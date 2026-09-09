# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2026-09-09

First public open-source release.

### What's New

- ✨ Feature: 10 built-in sources searched in parallel with graceful degradation — Project Gutenberg, Open Library, Wikisource (zh/en), Standard Ebooks, CBETA, ctext.org, LibriVox, Google Books, wenshuoge, daizhigev20
- ✨ Feature: Full-GitHub book-list search — the `github_lists` source queries the GitHub code-search API for community book-list markdown files pointing to netdisk downloads, with curated seed repositories as an anonymous fallback
- ✨ Feature: Confidence ranking (0–100) by title/author match, availability and format
- ✨ Feature: Three front-ends sharing one core — CLI (`bookscout`), MCP server (`pip install mu-ebook-scout[mcp]`), and an Agent Skill shell
- ✨ Feature: Custom user-configured sources (Prowlarr-style), strictly pass-through link-only
- ✨ Feature: CBETA traditional/simplified auto-retry for Chinese Buddhist canon queries
- ✨ Feature: Optional Google Books API key support (`BOOKSCOUT_GOOGLE_BOOKS_KEY`)

### Safety

- 🛡️ Downloads only at explicit user request, behind a host allowlist, a 100 MB cap, and magic-number verification
- 🛡️ Tokens/keys read from environment variables only — never stored or logged

### Full Changelog

Initial release — https://github.com/muippt/mu-ebook-scout/releases/tag/v1.4.0
