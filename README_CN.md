<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/default-banner.png">
    <img alt="mu-ebook-scout" src="assets/default-banner.png" width="100%">
  </picture>
</p>

# 🔍 mu-ebook-scout · 电子书下载器

> **一次搜索，十个合法书源。** 中英双语公版与开放授权电子书的多源搜索工具——搜索引路者：只帮你找到并排序合法链接，只有你明确要求时才下载文件。提供 CLI、MCP server 和 Agent Skill 壳三种形态，一个内核，三个入口。

[English](README.md) | **中文** | [🌐 在线主页](https://muippt.github.io/mu-ebook-scout/)

[![微信公众号](https://img.shields.io/badge/muippt-07C160?logo=wechat&logoColor=white)](https://mp.weixin.qq.com/s/YLtXENt_7WzO2DgJCFUtPA)
[![小红书](https://img.shields.io/badge/muippt-FF2442?logo=xiaohongshu&logoColor=white)](https://xhslink.com/m/ESxtgUNMdl)
[![书籍](https://img.shields.io/badge/书籍-图解团队管理-BBDDE5?logo=bookstack&logoColor=white)](https://item.m.jd.com/product/14547345.html)
[![mu-skill集合](https://img.shields.io/badge/mu--skill集合-9E95B7?logo=refinedgithub&logoColor=white)](https://muippt.github.io/mu-skill-hub/)
[![License](https://img.shields.io/github/license/muippt/mu-ebook-scout)](LICENSE)
[![Version](https://img.shields.io/github/v/release/muippt/mu-ebook-scout)](https://github.com/muippt/mu-ebook-scout/releases)
[![Stars](https://img.shields.io/github/stars/muippt/mu-ebook-scout)](https://github.com/muippt/mu-ebook-scout/stargazers)

### 💡 使用场景示例

- 📚 **公版经典一键找**——搜「西游记」，文硕阁、殆知阁、Project Gutenberg 的 EPUB/TXT 直链一次到手
- 🀄 **古籍全覆盖**——ctext.org 先秦两汉典籍、CBETA 佛藏（繁简自动转换）、维基文库全文
- 🔍 **现代畅销书**——GitHub 书单源全站扫描社区网盘书目录，连提取码一起给你城通/蓝奏链接
- 🤖 **Agent 原生**——MCP server 供 Agent 客户端调用，另有「先搜索、确认后下载」的 Agent Skill 壳
- 🛡️ **下载有校验**——你不点头不下载；文件先做魔数校验，通过才算成功
- 🎧 **免费有声书**——20,000+ 部 LibriVox 公版有声书（MP3/M4B）与电子书同榜呈现
- 🧭 **绝不空手而归**——零命中也返回手动入口和合法借阅/购买渠道，而不是一句"未找到"

---

### ✨ 核心亮点

#### 🌐 十个内置源，并行搜索

想找一本公版经典，却不想在十个网站之间挨个打开、挨个搜？一次查询就把下表的书源并行问一遍，结果排好序递到你面前；个别源临时限流或失联会被跳过并如实上报，绝不拖垮整次搜索。先发一句「帮我找《西游记》」试试水。

| 书源 | 覆盖范围 | 许可 |
| --- | --- | --- |
| Project Gutenberg（Gutendex API） | 75,000+ 部英文/西方经典 | 公有领域 |
| Open Library / archive.org | 海量书目记录、公版扫描、借阅 | CC BY-SA / ODbL |
| 维基文库（中 + 英） | 中英文全文经典 | CC BY-SA 4.0 |
| Standard Ebooks | 精排英文经典 | 公有领域 |
| CBETA | 汉文佛藏 | CC BY-NC-SA 4.0 |
| ctext.org | 先秦至汉代典籍 | 公版古籍 |
| LibriVox | 20,000+ 部免费公版有声书 | 公有领域 |
| Google Books（需免费 key） | 全球最大图书目录 | 元数据 CC BY |
| 文硕阁 / 殆知阁（GitHub 镜像） | 中文古籍语料 | 公版古籍 |
| GitHub 书单索引（全量代码搜索） | 社区网盘书目录 | 仅链接 |

#### 🐙 GitHub 全量书单搜索

公版之外的现代书，线索常散落在社区维护的书单笔记里。它替你把 GitHub 全站的书单翻一遍，命中网盘目录时连提取码一起给你——但严格只给链接，下载页由你亲手打开，工具不碰网盘。

#### 🥇 置信度排序

十个源各说各话，人工比对要翻很久。它按书名/作者匹配度、可获得性和格式给每条结果打 0–100 分，最合适的排最前——你只管从榜首看起。

#### 🔧 三形态共享一个内核

习惯终端就敲一条命令，用 AI Agent 就让它替你搜，搭了 MCP 客户端就当工具调用——同一个引擎，换着姿势用。安装后对 Agent 说一句「帮我找一本《西游记》的合法免费电子书」就能上手。

#### 🧩 custom 源机制（Prowlarr 模式）

内置源之外还想追自己的书源？在配置里加一项就能接入。custom 源严格只透传：结果只给链接，由你自己在浏览器打开，绝不代理下载。

#### 🛡️ 显式下载 + 校验把关

最怕工具自作主张往本地拉文件。这里一切下载都要你点头，文件到手前还要过 host 白名单、大小上限、文件头校验三道关，通过才算成功；零命中时也不让你白跑——手动入口和合法借阅/购买渠道一并奉上。

---

### 📌 与同类工具对比

| | 🧭 mu-ebook-scout | 手动逐站搜索 | 付费订阅服务（Kindle Unlimited / Everand / 微信读书 等） |
| --- | --- | --- | --- |
| 成本 | 免费开源 | 免费，但花时间 | 按月订阅 |
| 覆盖范围 | 10 个公版/开放授权书源并行 + custom 透传 | 取决于你记得住多少个网站 | 授权书目为主，公版经典覆盖有限 |
| 中文公版/古籍 | 原生支持（维基文库中文、CBETA、ctext、文硕阁、殆知阁） | 需逐站检索、逐站比对 | 较少 |
| 使用方式 | 一句搜索，置信度排序，直接拿到文件链接 | 自己搜、自己筛、自己开下载页 | App 内在线阅读为主 |
| Agent / 自动化 | MCP server + Agent Skill 壳，可对话式调用 | 无法自动化 | 无开放接口 |
| 文件获取 | 按需下载 EPUB/TXT/MP3 到你自己的设备，显式确认 + 校验 | 自己逐站下载，格式质量参差 | 多数受 DRM 限制，不一定能导出文件 |
| 许可边界 | 只索引公版/开放授权源；扩展入口仅透传链接 | 由你自行判断 | 全部正版授权，体验稳定 |

---

### 🚀 核心工作流

| 工作流 | 场景 | 触发方式 |
| --- | --- | --- |
| 搜索与排序 | 十源并行找一本书 | `bookscout search "书名"` |
| 校验下载 | 下载你选定的一条 | `bookscout get N` |
| MCP 集成 | Agent 免终端调用搜索 | MCP 客户端配置 |
| Agent Skill 模式 | 对话式搜索-确认-下载 | Skill 触发词 |

---

### ⚙️ 技术规格

| 项目 | 说明 |
| --- | --- |
| 语言 | Python 3.10+ |
| 运行时依赖 | 零依赖（纯标准库；`mcp` 为可选扩展） |
| 形态 | CLI / MCP server / Agent Skill 壳 |
| 输出 | 按可获得性分组的排序文本报告 |
| 校验 | 每次下载均做魔数校验 |
| 下载上限 | 100MB，host 白名单强制 |
| 测试 | 127 项单元测试，全部通过 |
| 许可 | MIT（聚合书源保留各自许可） |

---

### 🛠️ 快速开始

**① 安装**——将 Agent Skill 壳克隆到你的 skill 目录：

```bash
git clone https://github.com/muippt/mu-ebook-scout.git ~/.claude/skills/mu-ebook-scout
```

> 其他 Agent 可使用各自的 skill 目录，或项目级 `.claude/skills/mu-ebook-scout`。若只想用独立 CLI：`pipx install git+https://github.com/muippt/mu-ebook-scout`（Python 3.10+；需要 MCP server 则安装 `[mcp]` 扩展）。

**② 验证**——重启或重载你的 Agent，然后发送：

```
列出我当前可用的 Skills
```

**③ 使用**——一条核心触发语：

```
帮我找一本《西游记》的合法免费电子书，最好有 EPUB 格式。
```

或指定工作流：

```
帮我把《金刚经》的公版电子书源都搜出来排个序
```

```
下载第 2 条
```

---

### 🔒 安全与隐私

- **本地运行，零运行时依赖**——整个引擎为 Python 标准库实现；无分析、无遥测、无数据收集。
- **Token 永不落盘**——可选的 GitHub token 与 Google Books key 仅在运行时从环境变量读取，不存储、不进日志，且只附加到 `api.github.com` / `googleapis.com` 请求——绝不发送给任何书源。
- **host 白名单**——下载命令拒绝一切内置公版源之外的 host；custom 源链接只做原样透传，绝不代理。
- **用途边界**——本工具不托管、不分发任何内容；内置书源均为公版/开放授权；扩展资源入口（Anna's Archive、LibGen）仅为预构造的搜索入口 URL。

---

### ⭐ Star 趋势

如果这个工具帮到了你，点个 star 让更多人看到：

<!-- Star 趋势图将在仓库积累 star 后补充。 -->

> 一次搜索十个合法书源——绝不空手而归。

---

### 👤 作者简介

🎓 清华大学出版社签约作家 / 2026当当影响力作家 / 某互联网大厂 AI 大模型业务 HR 砖家 / 一级人力资源管理师 / 二级心理咨询师 / 野生设计师

📚 著有[《图解团队管理》](https://item.m.jd.com/product/14547345.html)，服务客户有字节跳动、腾讯、百度、中国移动、SMG、BOE…

💡 [微信公众号](https://mp.weixin.qq.com/s/YLtXENt_7WzO2DgJCFUtPA) / [小红书](https://xhslink.com/m/ESxtgUNMdl)：muippt

### 📄 许可证与致谢

[MIT](LICENSE) © 2026 muippt

感谢让这个工具成为可能的公版与开放授权生态：Project Gutenberg、Open Library、维基文库、Standard Ebooks、CBETA、ctext.org、LibriVox、Google Books，以及文硕阁/殆知阁 GitHub 镜像。各源许可说明见 [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt)。

> 声明：本项目大部分内容由 AI 辅助完成。如您认为您的作品被使用但未获得适当署名，请提交 issue。

## 网络 FAQ：代理与 API key（可选）

部分书源在某些网络环境下不可达（Anna's Archive / LibGen 镜像、archive.org
下载节点、HathiTrust 存在区域性屏蔽）。引擎使用 Python 标准库 HTTP 栈，
**自动识别标准代理环境变量**——无需改任何代码：

```bash
# 指向你的本地代理（端口按实际情况调整）
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890   # 代理为 SOCKS5 时
```

单次会话临时设置，或写入 `~/.zshrc` / `~/.bashrc` 永久生效。
不开代理一切照常可用：内置书源、GitHub 代码搜索与全部降级路径均不受影响。

### GitHub API token（可选，建议配置）

中文公版书库（文硕阁 + 殆知阁）托管在 GitHub 上，通过 GitHub API 搜索。
匿名请求限制为**每小时 60 次/每 IP**——日常够用，重度容易触顶。
配置免费个人访问 token 后额度提升为**每小时 5,000 次**。

1. 打开 https://github.com/settings/tokens?type=beta
2. **Generate new token** → 命名如 `bookscout`，权限全部留空
3. `export GITHUB_TOKEN=github_pat_xxxx`（或 `BOOKSCOUT_GITHUB_TOKEN`，优先级更高）

token 仅在运行时从环境变量读取——不写入任何配置文件、不进日志，
且只附加到 `api.github.com` 请求。

### Google Books API key（可选）

免 key 的 Google Books 配额按 IP 共享，经常被耗尽（HTTP 429）。
配置你自己的免费 key 后，`google_books` 源自动启用：

1. 打开 https://console.cloud.google.com/apis/library/books.googleapis.com
2. 创建（或选择）项目，点击 **Enable**，再进入 **Credentials**
3. 创建 **API key**（只读搜索无需任何限制）
4. `export BOOKSCOUT_GOOGLE_BOOKS_KEY=AIza...`

未配置 key 时该源保持静默——绝不会拖垮一次搜索。

## Roadmap

- **v1.5**——Gallica、Europeana、archive.org 中文筛选
- **v1.6**——chinese-poetry 语料、更多社区种子仓库

## 参与贡献

欢迎提 issue 和 pull request：<https://github.com/muippt/mu-ebook-scout>。新增书源 adapter 必须面向公版或开放授权材料；各源许可说明见 [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt)。

## 用途边界

- 本工具**不托管、不分发任何内容文件**——只产出链接。内置可搜索书源均为公版/开放授权；下载命令只对这些源生效。
- **扩展资源入口**（Anna's Archive、LibGen）仅是预构造的搜索入口 URL：工具从不请求、解析或下载这些站点。你在自己的浏览器里打开链接，之后发生的一切由你、该站点与你所在地的法律决定。
- 下载**只在你明确请求时**执行；遵守各书源许可条款及当地法律的责任由使用者承担。
- **custom 源完全由你自己配置。** 本项目不提供任何 custom 源配置，也不分发任何 custom 源内容——链接只做原样透传。
