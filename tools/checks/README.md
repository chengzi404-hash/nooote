# Browser static-check bundles

`nooote/static/vendor/lezer-checks.js` and `ruby-checks.js` are generated from
the entry files in this directory. They are loaded on demand by
`nooote/static/app.js`.

## Rebuild

```bash
npm install --no-save \
  @lezer/javascript @lezer/python @lezer/cpp @lezer/rust @lezer/html \
  @lezer/css @lezer/json @lezer/java @lezer/php @lezer/go @lezer/yaml \
  @ruby/prism @bjorn3/browser_wasi_shim esbuild

npx esbuild tools/checks/lezer.js \
  --bundle --format=esm --minify --platform=browser --target=es2020 \
  --outfile=nooote/static/vendor/lezer-checks.js

npx esbuild tools/checks/ruby.js \
  --bundle --format=esm --minify --platform=browser --target=es2020 \
  --outfile=nooote/static/vendor/ruby-checks.js

cp node_modules/@ruby/prism/src/prism.wasm nooote/static/vendor/prism.wasm
```

`lezer-checks.js` exports a `parsers` map keyed by language; `ruby-checks.js`
exports `checkRuby(code)`, which resolves to an array of `{ line, column,
reason, code }` errors. Both are ES modules loaded with dynamic `import()`.
