# Vendored browser libraries

These files are served locally so the app works offline and the Content Security
Policy can stay at `script-src 'self'`.

`static/vendor/` is gitignored: every app start runs `nooote.vendor.sync`, which
downloads any missing or corrupted file and verifies it against the SHA-256
digests declared in `nooote/vendor.py`. Run `uv run python -m nooote.vendor` to
fetch everything up front, or set `NOOOTE_SKIP_VENDOR_SYNC=1` to skip the check.

| File | Library | Version | License |
| --- | --- | --- | --- |
| `marked.min.js` | [marked](https://github.com/markedjs/marked) | 18.2.0 | MIT |
| `highlight.min.js` | [highlight.js](https://github.com/highlightjs/highlight.js) (common languages build) | 11.12.0 | BSD-3-Clause |
| `purify.min.js` | [DOMPurify](https://github.com/cure53/DOMPurify) | 3.4.17 | Apache-2.0 OR MPL-2.0 |
| `katex/katex.min.js`, `katex/katex.min.css`, `katex/fonts/*` | [KaTeX](https://katex.org/) | 0.18.10 | MIT |
| `mermaid/mermaid.min.js` | [Mermaid](https://mermaid.js.org/) (on-demand diagram renderer) | 11.12.2 | MIT |
| `fontawesome/css/*`, `fontawesome/webfonts/*` | [Font Awesome Free](https://fontawesome.com/) (solid icons) | 7.3.1 | Icons CC BY 4.0, fonts SIL OFL 1.1, code MIT |
| `github.min.css`, `github-dark.min.css` | highlight.js themes | 11.12.0 | BSD-3-Clause |

License texts are downloaded next to their libraries as `LICENSE.*`.
