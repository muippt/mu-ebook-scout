# 🔍 mu-ebook-scout · 电子书下载器

> **One search, ten legal book sources.** A multi-source search tool for public-domain and open-license ebooks in Chinese and English — a search guide that surfaces ranked links, and downloads a file only when you explicitly ask for it. Delivered as a CLI, an MCP server, and an Agent Skill shell: one core engine, three front-ends.

[English](README.md) | **中文** | [🌐 Landing Page](https://muippt.github.io/mu-ebook-scout/)

[![WeChat](https://img.shields.io/badge/muippt-07C160?logo=wechat&logoColor=white)](https://mp.weixin.qq.com/s/YLtXENt_7WzO2DgJCFUtPA)
[![Xiaohongshu](https://img.shields.io/badge/muippt-FF2442?logo=xiaohongshu&logoColor=white)](https://xhslink.com/m/ESxtgUNMdl)
[![Book](https://img.shields.io/badge/Book-Visual%20Team%20Management-BBDDE5?logo=bookstack&logoColor=white)](https://item.m.jd.com/product/14547345.html)
[![mu-skillhub](https://img.shields.io/badge/mu--skillhub-9E95B7?logo=refinedgithub&logoColor=white)](https://muippt.github.io/mu-skill-hub/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.4.0-blue)](pyproject.toml)
[![Stars](https://img.shields.io/github/stars/muippt/mu-ebook-scout)](https://github.com/muippt/mu-ebook-scout/stargazers)

### 💡 Usage Examples

- 📚 **Public-domain classics** — search 西游记 / Journey to the West and get direct EPUB/TXT downloads from Wenshuoge, Daizhige and Project Gutenberg in one go
- 🀄 **Ancient Chinese texts** — Pre-Qin philosophy from ctext.org, the Buddhist canon from CBETA (traditional/simplified auto-converted), Wikisource full texts
- 🔍 **Modern bestsellers** — the GitHub book-list source scans the whole of GitHub for community-maintained netdisk directories and hands you ctfile/lanzou links with extraction codes
- 🤖 **Agent-native** — MCP server for agent clients, plus a Claude-style Agent Skill shell with a search-then-confirm workflow
- 🛡️ **Verified downloads** — nothing is fetched until you say so; downloaded files are magic-number-checked before being reported as success
- 🎧 **Free audiobooks** — 20,000+ LibriVox public-domain recordings (MP3/M4B) in the same ranked results
- 🧭 **Never empty-handed** — zero hits still returns manual entry points and legitimate borrow/purchase channels, not a bare "not found"

---

### ✨ Core Highlights

#### 🌐 Ten Built-in Sources, Parallel Search

| Source | Coverage | License |
| --- | --- | --- |
| Project Gutenberg (Gutendex API) | 75,000+ English/Western classics | Public domain |
| Open Library / archive.org | Millions of catalog records, scans, lending | CC BY-SA / ODbL |
| Wikisource (zh + en) | Chinese and English full-text classics | CC BY-SA 4.0 |
| Standard Ebooks | Polished, carefully typeset English classics | Public domain |
| CBETA | Chinese Buddhist canon | CC BY-NC-SA 4.0 |
| ctext.org | Pre-Qin through Han-era classics | Public-domain texts |
| LibriVox | 20,000+ free public-domain audiobooks | Public domain |
| Google Books (free API key) | World's largest book catalog | Metadata CC BY |
| wenshuoge / daizhigev20 (GitHub mirrors) | Chinese ancient-text corpus | Public-domain classics |
| GitHub book-list indexes (full code search) | Community netdisk directories | Links only |

Graceful degradation: a failing or rate-limited source is skipped and reported, never fatal to the query.

#### 🐙 Full-GitHub Book-List Search

Beyond curated public-domain repositories, the `github_lists` source searches **all of GitHub** via the code-search API (token recommended) for community book-list markdown files pointing to netdisk downloads, with curated seed repositories as an anonymous fallback. Netdisk hits are strictly link-only: you open the download page yourself — the tool never touches the netdisk.

#### 🥇 Confidence Ranking

Results are scored 0–100 by title/author match, availability, and format, so the best candidates surface first — no manual filtering across ten sources.

#### 🔧 Three Front-Ends, One Core

- **CLI** — `bookscout search "title"` / `bookscout get N`
- **MCP server** — `pip install mu-ebook-scout[mcp]`, two tools (`search`, `get`), host allowlist + 100 MB cap + magic-number verification
- **Agent Skill shell** — [`skills/mu-ebook-scout/SKILL.md`](skills/mu-ebook-scout/SKILL.md) wraps the CLI with trigger conditions and a search-then-confirm workflow

#### 🧩 Custom Sources (Prowlarr-style)

Add your own sources in a config file. Custom sources are strictly pass-through: results are links you open yourself, never proxied downloads.

#### 🛡️ Explicit, Verified Downloads

Nothing is downloaded until you say so. Every download goes through a host allowlist, a 100 MB cap, and magic-number verification before being reported as success — and a zero-hit search still returns manual entry points and legitimate borrow/purchase channels, never a bare "not found".

---

### 📌 Comparison

| | 🧭 mu-ebook-scout | book-searcher | annas-mcp | librarr |
| --- | --- | --- | --- | --- |
| Multi-source aggregation | 10 sources + custom (pass-through) | Single self-hosted index | Single source | Single source |
| Chinese sources | Native (Wikisource zh, CBETA, ctext, wenshuoge, daizhigev20) | Index-dependent | Limited | Limited |
| Agent interface | MCP server + Agent Skill shell | None | MCP server | None |
| Activity | Active | Upstream inactive | Active | Active |
| Download behavior | Explicit request only, magic-number verification, host allowlist | Index only | Direct download | Direct download |

---

### 🚀 Workflows

| Workflow | Scenario | Trigger |
| --- | --- | --- |
| Search & rank | Find a book across all 10 sources | `bookscout search "title"` |
| Verified download | Fetch one file you picked | `bookscout get N` |
| MCP integration | Agent-driven search without a shell | MCP client config |
| Agent Skill mode | Conversational search-then-confirm | Skill trigger phrases |

---

### ⚙️ Technical Specs

| Item | Description |
| --- | --- |
| Language | Python 3.10+ |
| Runtime dependencies | None (stdlib only; `mcp` is an optional extra) |
| Front-ends | CLI / MCP server / Agent Skill shell |
| Output | Ranked text report (grouped by availability) |
| Verification | Magic-number check on every download |
| Download cap | 100 MB, host allowlist enforced |
| Tests | 127 unit tests, all passing |
| License | MIT (aggregated sources keep their own licenses) |

---

### 🛠️ Quick Start

**1) Install** — requires Python 3.10+:

```bash
# From source (PyPI release planned)
pipx install git+https://github.com/muippt/mu-ebook-scout

# With the MCP server extra
pipx install "mu-ebook-scout[mcp]"
```

Or use the Agent Skill shell: copy [`skills/mu-ebook-scout/`](skills/mu-ebook-scout/) into your agent's skill directory (e.g. `~/.claude/skills/mu-ebook-scout`).

**2) Verify**:

```bash
bookscout search "西游记"
```

**3) Run** — pick a hit and download:

```bash
bookscout get 2
```

---

### 🔒 Security & Privacy

- **Local execution, zero runtime dependencies** — the whole engine is Python stdlib; no analytics, no telemetry, no data collection.
- **Tokens never touch disk** — the optional GitHub token and Google Books key are read from environment variables at runtime only, never stored, never logged, and attached exclusively to `api.github.com` / `googleapis.com` requests — never to any book source.
- **Host allowlist** — the download command refuses any host outside the built-in public-domain sources; custom-source links are passed through as-is, never proxied.
- **Usage boundaries** — the tool hosts and distributes no content; built-in sources are public-domain/open-license; extended-resource entries (Anna's Archive, LibGen) are pre-built search-entry URLs only.

---

### ⭐ Star History

If this tool saves you time, a star helps others find it:

<!-- Star-history chart will be added once the repository accumulates stars. -->

> One search across ten legal book sources — never empty-handed.

---

### 👤 About the Author

🎓 Signatory Author of Tsinghua University Press / 2026 Dangdang Influential Author / AI & Large Model Business HR Specialist at a Leading Tech Company / National Level-1 HR Manager / Level-2 Psychological Counselor / Self-taught Designer

📚 Author of [*Visual Team Management*](https://item.m.jd.com/product/14547345.html). Clients include ByteDance, Tencent, Baidu, China Mobile, SMG, BOE…

💡 [WeChat Official Account](https://mp.weixin.qq.com/s/YLtXENt_7WzO2DgJCFUtPA) / [Xiaohongshu](https://xhslink.com/m/ESxtgUNMdl): muippt

### 📄 License & Acknowledgments

[MIT](LICENSE) © 2026 muippt

Thanks to the public-domain and open-license ecosystems that make this tool possible: Project Gutenberg, Open Library, Wikisource, Standard Ebooks, CBETA, ctext.org, LibriVox, Google Books, and the wenshuoge / daizhigev20 GitHub mirrors. Per-source license notes: [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt).

> Note: Much of this project was co-created with AI assistance. If you believe your work has been used without proper attribution, please open an issue.

## Network FAQ: proxy and API keys (optional)

Some source hosts are unreachable from certain networks (regional blocking
of Anna's Archive / LibGen mirrors, archive.org download nodes, HathiTrust).
The engine uses Python's stdlib HTTP stack, which **respects the standard
proxy environment variables automatically** — no code change needed:

```bash
# point at your local proxy (adjust the port to your setup)
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890   # if your proxy is SOCKS5
```

Set them for one session, or in `~/.zshrc` / `~/.bashrc` for permanence.
Without a proxy everything still works: the built-in sources, GitHub code
search, and all graceful-degradation paths remain reachable.

### GitHub API token (optional, recommended)

The Chinese public-domain book collections (Wenshuoge + Daizhige) are hosted
on GitHub and searched through the GitHub API. Anonymous requests are limited
to **60 per hour per IP** — usually fine for casual use, but easy to exhaust.
With a free personal access token the limit becomes **5,000 requests/hour**.

1. Open https://github.com/settings/tokens?type=beta
2. **Generate new token** → name it e.g. `bookscout`, leave all permissions unchecked
3. `export GITHUB_TOKEN=github_pat_xxxx` (or `BOOKSCOUT_GITHUB_TOKEN`, which takes precedence)

The token is read from the environment at runtime only — never stored, never
logged, attached exclusively to `api.github.com` requests.

### Google Books API key (optional)

The keyless Google Books quota is shared per IP and often exhausted
(HTTP 429). With your own free key the `google_books` source activates
automatically:

1. Open https://console.cloud.google.com/apis/library/books.googleapis.com
2. Create (or select) a project, click **Enable**, then **Credentials**
3. Create an **API key** (no restrictions needed for read-only search)
4. `export BOOKSCOUT_GOOGLE_BOOKS_KEY=AIza...`

Without the key the source simply stays silent — it never fails a search.

## Roadmap

- **v1.5** — Gallica, Europeana, and archive.org Chinese-language filtering
- **v1.6** — chinese-poetry corpus, more community seed repositories

## Contributing

Issues and pull requests are welcome at <https://github.com/muippt/mu-ebook-scout>. New source adapters must target public-domain or openly licensed material; see [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt) for the per-source license notes.
