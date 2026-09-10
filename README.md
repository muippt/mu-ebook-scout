<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/default-banner.png">
    <img alt="mu-ebook-scout" src="assets/default-banner.png" width="100%">
  </picture>
</p>

# 🔍 mu-ebook-scout · 电子书下载器

> **One search, ten legal book sources.** A multi-source search tool for public-domain and open-license ebooks in Chinese and English — a search guide that surfaces ranked links, and downloads a file only when you explicitly ask for it. Delivered as a CLI, an MCP server, and an Agent Skill shell: one core engine, three front-ends.

**English** | [中文](README_CN.md) | [🌐 Landing Page](https://muippt.github.io/mu-ebook-scout/)

[![WeChat](https://img.shields.io/badge/muippt-07C160?logo=wechat&logoColor=white)](https://mp.weixin.qq.com/s/YLtXENt_7WzO2DgJCFUtPA)
[![Xiaohongshu](https://img.shields.io/badge/muippt-FF2442?logo=xiaohongshu&logoColor=white)](https://xhslink.com/m/ESxtgUNMdl)
[![Book](https://img.shields.io/badge/Book-Visual%20Team%20Management-BBDDE5?logo=bookstack&logoColor=white)](https://item.m.jd.com/product/14547345.html)
[![mu-skillhub](https://img.shields.io/badge/mu--skillhub-9E95B7?logo=refinedgithub&logoColor=white)](https://muippt.github.io/mu-skill-hub/)
[![License](https://img.shields.io/github/license/muippt/mu-ebook-scout)](LICENSE)
[![Version](https://img.shields.io/github/v/release/muippt/mu-ebook-scout)](https://github.com/muippt/mu-ebook-scout/releases)
[![Stars](https://img.shields.io/github/stars/muippt/mu-ebook-scout)](https://github.com/muippt/mu-ebook-scout/stargazers)

---

### 💡 Usage Examples

- 📚 **Public-domain classics** — search 西游记 / Journey to the West and get direct EPUB/TXT downloads from Wenshuoge, Daizhige and Project Gutenberg in one go
- 🀄 **Ancient Chinese texts** — Pre-Qin philosophy from ctext.org, the Buddhist canon from CBETA (traditional/simplified auto-converted), Wikisource full texts
- 🔍 **Modern bestsellers** — the GitHub book-list source scans the whole of GitHub for community-maintained netdisk directories and hands you ctfile/lanzou links with extraction codes
- 🤖 **Agent-native** — MCP server for agent clients, plus an Agent Skill shell with a search-then-confirm workflow
- 🛡️ **Verified downloads** — nothing is fetched until you say so; downloaded files are magic-number-checked before being reported as success
- 🎧 **Free audiobooks** — 20,000+ LibriVox public-domain recordings (MP3/M4B) in the same ranked results
- 🧭 **Never empty-handed** — zero hits still returns manual entry points and legitimate borrow/purchase channels, not a bare "not found"

---

### ✨ Core Highlights

#### 🌐 Ten Built-in Sources, Parallel Search

Looking for a public-domain classic but dreading the tour across ten different websites? One query asks every source below in parallel and hands the results back ranked; a rate-limited or unreachable source is skipped and reported honestly, never fatal to the search. Try it with "Find me Journey to the West".

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

#### 🐙 Full-GitHub Book-List Search

For modern titles beyond the public domain, the clues often live in community-maintained book-list notes. It sweeps the book lists across all of GitHub for you and, on a netdisk hit, hands you the link together with the extraction code — strictly link-only: you open the download page yourself, the tool never touches the netdisk.

#### 🥇 Confidence Ranking

Ten sources each speak their own language; comparing them by hand takes forever. Every result is scored 0–100 on title/author match, availability, and format, so the best candidates sit at the top — just start from rank one.

#### 🔧 Three Front-Ends, One Core

Live in the terminal? Type a command. Prefer an AI agent? Let it search for you. Running an MCP client? Call it as a tool. Same engine, whichever posture you like — after installing, just tell your agent "find me a legal free copy of Journey to the West".

#### 🧩 Custom Sources (Prowlarr-style)

Want to follow sources beyond the built-in ten? Add one entry to the config. Custom sources are strictly pass-through: results are links you open yourself in your own browser, never proxied downloads.

#### 🛡️ Explicit, Verified Downloads

The scariest tool is one that pulls files onto your disk uninvited. Here nothing downloads until you say so, and every file passes a host allowlist, a size cap, and a file-signature check before being reported as success. A zero-hit search still isn't a dead end — manual entry points and legitimate borrow/purchase channels come back with the results.

---

### 📌 Comparison

| | 🧭 mu-ebook-scout | Manual site-by-site search | Paid subscriptions (Kindle Unlimited / Everand / WeRead etc.) |
| --- | --- | --- | --- |
| Cost | Free, open source | Free, but costs your time | Monthly subscription |
| Coverage | 10 public-domain/open-license sources in parallel + custom pass-through | However many sites you can remember | Licensed catalogs; limited public-domain classics |
| Chinese classics & public domain | Native (Wikisource zh, CBETA, ctext, wenshuoge, daizhigev20) | Search and compare site by site | Scarce |
| How you use it | One prompt, ranked results, direct file links | Search, filter, open download pages yourself | Mostly in-app reading |
| Agent / automation | MCP server + Agent Skill shell, conversational | Cannot be automated | No open interface |
| File access | On-demand EPUB/TXT/MP3 downloads to your own device, explicit confirm + verification | Manual downloads, inconsistent quality | Often DRM-restricted; export not guaranteed |
| License boundary | Indexes public-domain/open-license sources only; extended entries pass through links | Your own judgment | Fully licensed, stable experience |

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

**1) Install** — clone the Agent Skill shell into your skill directory:

```bash
git clone https://github.com/muippt/mu-ebook-scout.git ~/.claude/skills/mu-ebook-scout
```

> Other agents may use their own skill directories, or a project-level `.claude/skills/mu-ebook-scout`. To use the standalone CLI instead: `pipx install git+https://github.com/muippt/mu-ebook-scout` (Python 3.10+; add the `[mcp]` extra for the MCP server).

**2) Verify** — restart or reload your agent, then send:

```
List my available skills
```

**3) Run** — one core prompt to exercise the primary value:

```
Find me a legal free copy of 西游记 (Journey to the West), preferably EPUB.
```

Or invoke a specific workflow:

```
Search the public-domain sources for 《金刚经》 (the Diamond Sutra) and rank them.
```

```
Download result #2.
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

---

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
