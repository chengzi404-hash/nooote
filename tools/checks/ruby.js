import { WASI } from "@bjorn3/browser_wasi_shim";
import { parsePrism } from "@ruby/prism/src/parsePrism.js";

let prismPromise = null;

function loadPrism() {
  if (!prismPromise) {
    prismPromise = (async () => {
      const response = await fetch(new URL("./prism.wasm", import.meta.url));
      if (!response.ok) throw new Error(`Failed to load prism.wasm: ${response.status}`);

      const wasm = await WebAssembly.compile(await response.arrayBuffer());
      const wasi = new WASI([], [], []);
      const instance = await WebAssembly.instantiate(wasm, {
        wasi_snapshot_preview1: wasi.wasiImport,
      });
      wasi.initialize(instance);

      const encoder = new TextEncoder();
      return (code) => parsePrism(instance.exports, encoder.encode(code), {});
    })();
  }
  return prismPromise;
}

export async function checkRuby(code) {
  const parse = await loadPrism();
  const result = parse(code);

  return result.errors.map((error) => ({
    line: error.location.startLine(),
    column: error.location.startCodeUnitsColumn("utf-16") + 1,
    reason: error.message,
    code: error.type,
  }));
}
