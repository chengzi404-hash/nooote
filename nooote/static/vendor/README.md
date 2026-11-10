# Vendored browser libraries

These files are served locally so the app works offline and the Content Security
Policy can stay at `script-src 'self'` (plus `'wasm-unsafe-eval'` for the Ruby parser).

| File | Library | Version | License |
| --- | --- | --- | --- |
| `marked.min.js` | [marked](https://github.com/markedjs/marked) | 18.2.0 | MIT |
| `highlight.min.js` | [highlight.js](https://github.com/highlightjs/highlight.js) (common languages build) | 11.12.0 | BSD-3-Clause |
| `purify.min.js` | [DOMPurify](https://github.com/cure53/DOMPurify) | 3.4.17 | Apache-2.0 OR MPL-2.0 |
| `lezer-checks.js` | [Lezer](https://lezer.codemirror.net/) grammars bundled with esbuild | see below | MIT |
| `ruby-checks.js` | [Ruby Prism](https://github.com/ruby/prism) + [browser_wasi_shim](https://github.com/bjorn3/browser_wasi_shim) | 2.1.0 / 0.4.2 | MIT / MIT OR Apache-2.0 |
| `prism.wasm` | Ruby Prism WASM parser | 2.1.0 | MIT |
| `katex/katex.min.js`, `katex/katex.min.css`, `katex/fonts/*` | [KaTeX](https://katex.org/) | 0.18.10 | MIT |
| `mermaid/mermaid.min.js` | [Mermaid](https://mermaid.js.org/) (on-demand diagram renderer) | 11.12.2 | MIT |
| `github.min.css`, `github-dark.min.css` | highlight.js themes | 11.12.0 | BSD-3-Clause |

`lezer-checks.js` bundles these MIT-licensed grammars:

| Package | Version |
| --- | --- |
| `@lezer/javascript` | 1.5.6 |
| `@lezer/python` | 1.1.19 |
| `@lezer/cpp` | 1.1.6 |
| `@lezer/rust` | 1.0.3 |
| `@lezer/html` | 1.3.13 |
| `@lezer/css` | 1.3.9 |
| `@lezer/json` | 1.0.3 |
| `@lezer/java` | 1.1.5 |
| `@lezer/php` | 1.0.6 |
| `@lezer/go` | 1.0.1 |
| `@lezer/yaml` | 1.0.4 |

Sources and rebuild instructions live in `tools/checks/`. License texts are
included in this directory as `LICENSE.*`.
