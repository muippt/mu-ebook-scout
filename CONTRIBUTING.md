# Contributing to mu-ebook-scout

Thanks for your interest in improving this tool!

## Ways to contribute

- **Report a bug** — open an issue with the bug report template
- **Suggest a source** — new source adapters are welcome
- **Improve docs** — README wording, FAQ, examples
- **Fix a bug** — check the issue list for "good first issue" material

## Ground rules for source adapters

New source adapters **must target public-domain or openly licensed material**
(Creative Commons, public domain, or equivalent). Adapters for piracy-oriented
sites will not be accepted — see the Usage Boundaries section of the README.

Each adapter lives in `src/bookscout/sources/<name>.py`, implements the
`Source` interface (`search(title, author, language) -> list[Hit]`), and is
registered in `src/bookscout/sources/__init__.py`. Add unit tests in
`src/bookscout/tests/` that mock the HTTP layer (monkeypatch
`http_get_json` / `http_get_text`) — the test suite never touches the network.

## Development setup

```bash
git clone https://github.com/muippt/mu-ebook-scout
cd mu-ebook-scout
pip install -e .
pip install pytest
python -m pytest src/bookscout/tests/ -q
```

## Pull request checklist

- [ ] Tests pass locally (`python -m pytest src/bookscout/tests/ -q`)
- [ ] New sources are public-domain / open-license only
- [ ] No network calls in tests
- [ ] Docs updated if user-facing behavior changed
- [ ] Per-source license noted in `THIRD_PARTY_LICENSES.txt` for new sources
