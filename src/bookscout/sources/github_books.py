"""GitHub-hosted public-domain book collections adapter.

Two curated repositories of Chinese public-domain texts:
  - zhpelo/wenshuoge      ~13.8k public-domain EPUB/PDF books
  - garychowcmu/daizhigev20  classical Chinese corpus (TXT)

Strategy: fetch the full recursive git tree in ONE request
(https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1),
then match file names against the query locally. Unauthenticated GitHub
API is rate limited (60 req/h per IP); setting ``GITHUB_TOKEN`` or
``BOOKSCOUT_GITHUB_TOKEN`` raises the limit to 5,000 req/h (the token is
attached automatically by ``sources._http`` for api.github.com only).
A rate-limited response raises SourceError so the engine degrades this
source.

Matching normalizes file names: strip title marks (《》), spaces, case,
repository name prefixes (wenshuoge files are named "文硕阁_书名.epub")
and traditional/simplified variants (wenshuoge uses simplified titles;
daizhige mostly traditional; users may type either).
"""
from __future__ import annotations

import re
from urllib.parse import quote

from bookscout.core.model import Availability, Hit, HitType, Source, SourceError
from bookscout.sources._http import http_get_json

_REPOS: list[tuple[str, str, str]] = [
    # (owner, repo, collection label)
    ("zhpelo", "wenshuoge", "文硕阁"),
    ("garychowcmu", "daizhigev20", "殆知阁"),
]
_MAX_PER_REPO = 5
_EXT_FORMATS = {".epub": "EPUB", ".pdf": "PDF", ".txt": "TXT", ".mobi": "MOBI"}

#: Repository prefixes stripped from file stems before matching
#: ("文硕阁_孙子兵法.epub" → "孙子兵法").
_REPO_PREFIXES = ("文硕阁_", "殆知阁_")

#: Traditional → simplified mapping for common characters in book titles.
#: Compact by design: full T2S tables are too heavy for a zero-dependency
#: tool; unmapped characters pass through unchanged (matching stays exact
#: for them).
_T2S_TABLE = (
    "夢樓紅遊記國義滸傳論語詩經韓孫漢"
    "莊禮場現齋異廂資鑑戰說貞觀齊術憶"
    "筆談錄綱傷雜黃內農呂鹽鐵顏訓壇圓"
    "覺嚴華聖剛習陽飲叢魯吶鄉駱駝婁聽"
    "塵藝愛車長陳東動發風鳳蓋廣歸過後"
    "話畫匯極計濟間劍節盡舊開樂離蓮嶺"
    "龍陸馬門們廟腦鳥盤鵬貧鋪譜氣錢強"
    "橋輕慶窮權勸讓擾認絨軟銳潤賽傘喪"
    "設審腎師時濕實駛勢適視壽獸書樹雙"
    "順絲鬆蘇訴肅歲損縮鎖臺態嘆湯體條"
    "頭團遠願約閱雲運責張賬漲趙鎮證織"
    "職紙質製鐘種燭囑專轉賺裝壯狀綜總"
    "組劉關楊許葉蔣溫費備遲鄧鄭馮衛"
    "韋羅喬餘蕭"
)
_T2S_PLAIN = (
    "梦楼红游记国义浒传论语诗经韩孙汉"
    "庄礼场现斋异厢资鉴战说贞观齐术忆"
    "笔谈录纲伤杂黄内农吕盐铁颜训坛圆"
    "觉严华圣刚习阳饮丛鲁呐乡骆驼娄听"
    "尘艺爱车长陈东动发风凤盖广归过后"
    "话画汇极计济间剑节尽旧开乐离莲岭"
    "龙陆马门们庙脑鸟盘鹏贫铺谱气钱强"
    "桥轻庆穷权劝让扰认绒软锐润赛伞丧"
    "设审肾师时湿实驶势适视寿兽书树双"
    "顺丝松苏诉肃岁损缩锁台态叹汤体条"
    "头团远愿约阅云运责张账涨赵镇证织"
    "职纸质制钟种烛嘱专转赚装壮状综总"
    "组刘关杨许叶蒋温费备迟邓郑冯卫"
    "韦罗乔余萧"
)
_T2S = str.maketrans(_T2S_TABLE, _T2S_PLAIN)


class GithubBooksSource(Source):
    """Public-domain Chinese book collections mirrored on GitHub."""

    id = "github_books"
    label = "GitHub 公版书库 (文硕阁/殆知阁)"

    def search(self, title: str, author: str = "", language: str = "") -> list[Hit]:
        title = title.strip()
        if not title:
            return []
        # Chinese collections: only meaningful for zh / auto queries.
        if language and language != "auto" and language != "zh":
            return []

        needle = _normalize(title)
        if not needle:
            return []

        hits: list[Hit] = []
        for owner, repo, collection in _REPOS:
            tree = self._fetch_tree(owner, repo)
            hits.extend(self._match(tree, owner, repo, collection, needle))
        return hits

    # ------------------------------------------------------------------
    def _fetch_tree(self, owner: str, repo: str) -> list[dict]:
        try:
            return self._tree_at(owner, repo, "HEAD")
        except SourceError:
            # Some repositories do not expose HEAD as a tree ref; retry
            # with the repository's default branch instead.
            info = http_get_json(
                f"https://api.github.com/repos/{owner}/{repo}",
                self.timeout,
                self.max_retries,
            )
            branch = info.get("default_branch") or "master"
            return self._tree_at(owner, repo, branch)

    def _tree_at(self, owner: str, repo: str, ref: str) -> list[dict]:
        url = (
            f"https://api.github.com/repos/{owner}/{repo}"
            f"/git/trees/{quote(ref)}?recursive=1"
        )
        data = http_get_json(url, self.timeout, self.max_retries)
        # `truncated: true` just means we see a prefix of the tree; matching
        # against a partial listing is still correct, only less complete.
        return data.get("tree") or []

    def _match(
        self,
        tree: list[dict],
        owner: str,
        repo: str,
        collection: str,
        needle: str,
    ) -> list[Hit]:
        matched: list[Hit] = []
        for entry in tree:
            if entry.get("type") != "blob":
                continue
            path = entry.get("path", "")
            filename = path.rsplit("/", 1)[-1]
            stem, dot, ext = filename.rpartition(".")
            ext = (dot + ext).lower() if dot else ""
            if ext not in _EXT_FORMATS:
                continue
            if needle not in _normalize(stem):
                continue
            raw_path = quote(path, safe="/")
            matched.append(
                Hit(
                    title=_display(stem),
                    url=f"https://github.com/{owner}/{repo}/blob/HEAD/{raw_path}",
                    source=self.id,
                    source_label=self.label,
                    language="zh",
                    formats=[_EXT_FORMATS[ext]],
                    hit_type=HitType.EBOOK,
                    availability=Availability.FREE,
                    license="Public domain",
                    size_hint=_size_hint(entry.get("size")),
                    download_url=(
                        f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{raw_path}"
                    ),
                    extra={"collection": collection, "repo": f"{owner}/{repo}"},
                )
            )
            if len(matched) >= _MAX_PER_REPO:
                break
        return matched


def _normalize(name: str) -> str:
    """Normalize for matching: lowercase, strip marks/space/repo prefix, T2S."""
    cleaned = re.sub(r"[《》〈〉「」『』\s\u3000]+", "", (name or "").lower())
    for prefix in _REPO_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.translate(_T2S)


def _display(name: str) -> str:
    """Strip title marks and repo prefixes for a readable Hit title."""
    out = (name or "").strip()
    for prefix in _REPO_PREFIXES:
        if out.startswith(prefix):
            out = out[len(prefix):]
            break
    return re.sub(r"[《》〈〉「」『』]", "", out)


def _size_hint(size) -> str:
    """Format a byte count as a human-readable size hint."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        return ""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    if size >= 1024:
        return f"{size / 1024:.0f}KB"
    return f"{size}B"
