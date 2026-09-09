"""Command line interface for ``bookscout`` (``search`` / ``get`` / ``mcp``).

Hard rules wired into this module:
- ``search`` only collects and displays links — it never downloads;
- ``get`` is the single explicit download path, restricted to FREE hits
  from builtin public-domain sources (custom source URLs are always
  rejected) and requires interactive confirmation unless ``--yes`` is set
  (non-TTY without ``--yes`` refuses);
- downloads are streamed with a 100MB hard cap and verified by magic
  number before being reported as successful.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

from . import __version__
from .core import report
from .core.fallback import search_all
from .core.model import Availability, Hit, Source
from .core.validate import verify

__all__ = ["main"]

#: Hard cap for a single download (bytes).
_MAX_BYTES = 100 * 1024 * 1024

_DOWNLOAD_CHUNK = 64 * 1024

_HTTP_TIMEOUT = 60.0

_USER_AGENT = f"bookscout/{__version__}"


class _DownloadError(Exception):
    """A download could not be completed (network error or size cap)."""


# ---------------------------------------------------------------------------
# Source registry loading
# ---------------------------------------------------------------------------

def _load_sources() -> tuple[list[Source], list[Source]]:
    """Load builtin registry and user-configured custom sources.

    Returns ``(builtin_sources, custom_sources)``.
    """
    try:
        from .sources import SOURCE_REGISTRY, get_custom_sources
    except ImportError as exc:  # pragma: no cover - depends on packaging state
        raise SystemExit(
            "bookscout: source registry is unavailable "
            f"({exc}). Reinstall the package: pipx install mu-ebook-scout"
        ) from exc
    builtin = list(SOURCE_REGISTRY)
    try:
        custom = list(get_custom_sources())
    except Exception as exc:  # noqa: BLE001 - bad user config must not crash the CLI
        print(f"bookscout: 跳过自定义源（配置无法加载：{exc}）", file=sys.stderr)
        custom = []
    return builtin, custom


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> int:
    """Run a search across builtin + custom sources and render the results."""
    builtin, custom = _load_sources()
    pool: list[Source] = builtin + custom

    if args.source:
        wanted = {s.strip() for s in args.source.split(",") if s.strip()}
        pool = [src for src in pool if src.id in wanted]
        unknown = wanted - {src.id for src in pool}
        if unknown:
            known = ", ".join(src.id for src in builtin + custom) or "(none)"
            print(
                f"bookscout: 未知的源：{', '.join(sorted(unknown))}；可用源：{known}",
                file=sys.stderr,
            )
    if not pool:
        print("bookscout: 没有可用的搜索源。", file=sys.stderr)
        return 1

    print(f"正在搜索 {len(pool)} 个来源……", file=sys.stderr)
    hits, failed = search_all(args.title, args.author, args.lang, pool)

    ordered = report.order_for_display(hits)
    report.save_session(ordered, title=args.title, author=args.author)

    if args.json:
        print(report.render_json(ordered, failed, args.title, args.author))
    elif ordered:
        print(
            report.render_text(
                ordered,
                query_title=args.title,
                query_author=args.author,
                failed_sources=failed,
            ),
            end="",
        )
    else:
        print(report.fallback_output(args.title), end="")
    return 0


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

def _pick_hit(args: argparse.Namespace, hits: list[Hit]) -> Optional[Hit]:
    """Resolve the target hit from a positional index or a --url value."""
    if args.url:
        for hit in hits:
            if args.url in (hit.url, hit.download_url):
                return hit
        print(
            "bookscout: 拒绝下载 —— 该 URL 不属于内置公版源的已知结果"
            "（自定义源的链接只透传，不支持自动下载）。\n"
            "请先 bookscout search，再用 get <序号> 选择结果。",
            file=sys.stderr,
        )
        return None
    if args.n is None:
        print("bookscout: 请提供结果序号 N，或用 --url 指定链接。", file=sys.stderr)
        return None
    if not 1 <= args.n <= len(hits):
        print(f"bookscout: 序号超出范围（1-{len(hits)}）。", file=sys.stderr)
        return None
    return hits[args.n - 1]


def _guard_downloadable(hit: Hit, custom_ids: set[str]) -> bool:
    """Enforce the get rules: builtin source + FREE + has a direct URL."""
    if hit.source in custom_ids:
        print(
            "bookscout: 拒绝下载 —— 该结果来自自定义源（custom），按设计只透传链接。\n"
            f"请手动访问：{hit.url}",
            file=sys.stderr,
        )
        return False
    if hit.availability != Availability.FREE:
        print(
            "bookscout: 该条目不可直接下载（需注册借阅 / 仅链接 / 需购买）。\n"
            "请选择标记为 FREE 的条目。",
            file=sys.stderr,
        )
        return False
    if not hit.download_url:
        print(
            f"bookscout: 该条目没有直链下载地址，请打开页面手动获取：{hit.url}",
            file=sys.stderr,
        )
        return False
    return True


def _confirm(hit: Hit, args: argparse.Namespace) -> bool:
    """Interactive confirmation; refuses in non-TTY mode without --yes."""
    if args.yes:
        return True
    if not sys.stdin.isatty():
        print(
            "bookscout: 非交互环境下默认拒绝下载。确认无误请追加 --yes。",
            file=sys.stderr,
        )
        return False
    try:
        answer = input(
            f'确认下载 "{hit.title}"（来源：{hit.source_label}）？[y/N] '
        )
    except EOFError:
        return False
    if answer.strip().lower() not in ("y", "yes"):
        print("已取消。")
        return False
    return True


def _extension_for(hit: Hit) -> str:
    """Guess a file extension from the download URL, then from the format list."""
    if hit.download_url:
        suffix = PurePosixPath(urlparse(hit.download_url).path).suffix.lower()
        stem = suffix.lstrip(".")
        if stem and stem.isalnum() and len(stem) <= 5:
            return stem
    for fmt in hit.formats:
        candidate = fmt.strip().lower().lstrip(".")
        if candidate and candidate.isalnum():
            return candidate
    return "bin"


def _filename_for(hit: Hit) -> str:
    """Build a safe output filename from the hit title and format."""
    base = "".join("_" if ch in r'\/:*?"<>|' else ch for ch in hit.title).strip(" ._")
    base = base or "book"
    return f"{base}.{_extension_for(hit)}"


def _download(url: str, dest_dir: Path, filename: str) -> Path:
    """Stream ``url`` to ``dest_dir/filename`` with a hard 100MB cap."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT) as resp, open(
            dest, "wb"
        ) as out:
            total = 0
            while True:
                chunk = resp.read(_DOWNLOAD_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > _MAX_BYTES:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise _DownloadError(
                        f"文件超过 100MB 上限（已写入 {total / 1024 / 1024:.1f}MB，已中止）"
                    )
                out.write(chunk)
    except (urllib.error.URLError, OSError) as exc:
        dest.unlink(missing_ok=True)
        raise _DownloadError(f"下载失败：{exc}") from exc
    return dest


def cmd_get(args: argparse.Namespace) -> int:
    """Explicitly download one FREE hit from a builtin public-domain source."""
    session = report.load_session()
    if session is None:
        print(
            "bookscout: 没有可用的搜索会话，请先运行：bookscout search <书名>",
            file=sys.stderr,
        )
        return 1

    hits = report.hits_from_session(session)
    hit = _pick_hit(args, hits)
    if hit is None:
        return 1

    _, custom = _load_sources()
    custom_ids = {src.id for src in custom}
    if not _guard_downloadable(hit, custom_ids):
        return 1
    if not _confirm(hit, args):
        return 1

    out_dir = Path(args.out).expanduser()
    filename = _filename_for(hit)
    try:
        path = _download(hit.download_url or "", out_dir, filename)
    except _DownloadError as exc:
        print(f"bookscout: {exc}", file=sys.stderr)
        return 1

    ok, detail = verify(path, _extension_for(hit))
    if ok:
        print(f"✅ 下载完成并通过校验：{path}")
        print(f"   {detail}")
        return 0
    print(f"⚠️ 下载完成但校验未通过：{detail}")
    print(f"   文件保留在 {path}，请自行确认内容后再使用。")
    return 1


# ---------------------------------------------------------------------------
# mcp
# ---------------------------------------------------------------------------

def cmd_mcp(args: argparse.Namespace) -> int:  # noqa: ARG001 - uniform signature
    """Start the MCP server (requires the optional ``mcp`` extra)."""
    try:
        from . import mcp_server
    except ImportError:
        print(
            "bookscout: 未安装 MCP 服务组件（缺少可选依赖 mcp）。\n"
            "请安装：pipx install 'mu-ebook-scout[mcp]'\n"
            "或：pip install 'mu-ebook-scout[mcp]'",
            file=sys.stderr,
        )
        return 2
    return int(mcp_server.main() or 0)


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the ``bookscout`` argument parser."""
    parser = argparse.ArgumentParser(
        prog="bookscout",
        description=(
            "Public-domain ebook search aggregator. Searches links only; "
            "downloads require an explicit 'get'."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="搜索公版书链接（默认不下载）")
    p_search.add_argument("title", help="书名（必填）")
    p_search.add_argument("--author", default="", help="作者名（可选）")
    p_search.add_argument(
        "--lang", default="auto", choices=["zh", "en", "auto"], help="语言过滤（默认 auto）"
    )
    p_search.add_argument("--json", action="store_true", help="输出 JSON 而非文本")
    p_search.add_argument(
        "--source", default="", help="只搜索指定源（逗号分隔的源 id，如 gutenberg,wenshuoge）"
    )
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="下载搜索结果中的某一条（需显式选择）")
    p_get.add_argument("n", type=int, nargs="?", default=None, help="搜索结果序号")
    p_get.add_argument(
        "--url",
        default="",
        help="直接给 URL（仅接受内置公版源的已知结果；custom 源一律拒绝）",
    )
    p_get.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    p_get.add_argument("--yes", action="store_true", help="跳过交互确认（非 TTY 必需）")
    p_get.set_defaults(func=cmd_get)

    p_mcp = sub.add_parser("mcp", help="以 MCP server 模式运行（需要 [mcp] 可选依赖）")
    p_mcp.set_defaults(func=cmd_mcp)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point (also used by the console script)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
