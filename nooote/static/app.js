(() => {
  "use strict";

  const relativeFormatter = typeof Intl !== "undefined" && Intl.RelativeTimeFormat
    ? new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" })
    : null;

  const RELATIVE_UNITS = [
    ["year", 31536000000],
    ["month", 2592000000],
    ["week", 604800000],
    ["day", 86400000],
    ["hour", 3600000],
    ["minute", 60000],
  ];

  function formatRelative(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;

    const diff = date.getTime() - Date.now();
    if (Math.abs(diff) < 45000) return "刚刚";

    for (const [unit, ms] of RELATIVE_UNITS) {
      if (Math.abs(diff) >= ms) {
        const value = Math.round(diff / ms);
        return relativeFormatter ? relativeFormatter.format(value, unit) : date.toLocaleString("zh-CN");
      }
    }
    return date.toLocaleString("zh-CN");
  }

  function formatAbsolute(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString("zh-CN", { dateStyle: "medium", timeStyle: "short" });
  }

  function refreshTimes(root = document) {
    root.querySelectorAll("time[data-relative]").forEach((el) => {
      const iso = el.getAttribute("datetime");
      el.textContent = formatRelative(iso);
      el.title = formatAbsolute(iso);
    });
  }

  refreshTimes();
  setInterval(() => refreshTimes(), 60000);

  const workspace = document.querySelector("[data-note-id]");
  if (!workspace) return;

  const noteId = workspace.dataset.noteId;
  const textarea = document.querySelector("#editor");
  const preview = document.querySelector("[data-preview]");
  const statusEl = document.querySelector("[data-status]");
  const savedAt = document.querySelector("[data-saved-at]");
  if (!textarea || !preview) return;

  let dirty = false;
  let saving = false;
  let queued = false;
  let saveTimer = null;
  let previewTimer = null;

  const canRender = typeof marked !== "undefined"
    && typeof DOMPurify !== "undefined"
    && typeof hljs !== "undefined";

  const INLINE_MATH = /^(\${1,2})(?!\$)(?=\S)((?:\\.|[^\\\n$])*?(?:\\.|\S))\1(?![0-9])/;
  const BLOCK_MATH = /^(\${1,2})\n((?:\\[^]|[^\\])+?)\n\1(?:\n|$)/;

  function mathExtension(options) {
    const render = (token, newline) => katex.renderToString(token.text, {
      ...options,
      displayMode: token.displayMode,
    }) + (newline ? "\n" : "");

    return {
      extensions: [
        {
          name: "inlineMath",
          level: "inline",
          start(src) {
            for (let index = src.indexOf("$"); index !== -1; index = src.indexOf("$", index + 1)) {
              if (src.slice(index).match(INLINE_MATH)) return index;
            }
          },
          tokenizer(src) {
            const match = src.match(INLINE_MATH);
            if (!match) return undefined;

            return {
              type: "inlineMath",
              raw: match[0],
              text: match[2].trim(),
              displayMode: match[1].length === 2,
            };
          },
          renderer: (token) => render(token, false),
        },
        {
          name: "blockMath",
          level: "block",
          tokenizer(src) {
            const match = src.match(BLOCK_MATH);
            if (!match) return undefined;

            return {
              type: "blockMath",
              raw: match[0],
              text: match[2].trim(),
              displayMode: match[1].length === 2,
            };
          },
          renderer: (token) => render(token, true),
        },
      ],
    };
  }

  if (typeof marked !== "undefined" && typeof katex !== "undefined") {
    marked.use(mathExtension({
      throwOnError: false,
      errorColor: "#d33",
      strict: "ignore",
      trust: false,
      maxSize: 20,
    }));
  }

  if (canRender) {
    DOMPurify.addHook("uponSanitizeAttribute", (node, data) => {
      const insideMath = node.nodeType === 1 && node.closest(".katex, .katex-display");

      if (data.attrName === "style" && !insideMath) {
        data.keepAttr = false;
      }
    });
  }

  const MAX_CHECK_ERRORS = 20;

  const CHECKERS = {
    javascript: { label: "JavaScript", parser: "javascript", source: "Lezer" },
    python: { label: "Python", parser: "python", source: "Lezer" },
    c: { label: "C", parser: "cpp", source: "Lezer" },
    cpp: { label: "C++", parser: "cpp", source: "Lezer" },
    rust: { label: "Rust", parser: "rust", source: "Lezer" },
    html: { label: "HTML", parser: "html", source: "Lezer" },
    css: { label: "CSS", parser: "css", source: "Lezer" },
    json: { label: "JSON", parser: "json", source: "Lezer" },
    java: { label: "Java", parser: "java", source: "Lezer" },
    php: { label: "PHP", parser: "php", source: "Lezer" },
    go: { label: "Go", parser: "go", source: "Lezer" },
    yaml: { label: "YAML", parser: "yaml", source: "Lezer" },
    ruby: { label: "Ruby", checker: "ruby", source: "Prism" },
  };

  const LANGUAGE_ALIASES = {
    js: "javascript",
    javascript: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    node: "javascript",
    py: "python",
    python: "python",
    c: "c",
    h: "c",
    cpp: "cpp",
    "c++": "cpp",
    cc: "cpp",
    cxx: "cpp",
    hpp: "cpp",
    hxx: "cpp",
    rs: "rust",
    rust: "rust",
    rb: "ruby",
    ruby: "ruby",
    html: "html",
    htm: "html",
    css: "css",
    json: "json",
    java: "java",
    php: "php",
    go: "go",
    golang: "go",
    yml: "yaml",
    yaml: "yaml",
  };

  const checkModulePromises = new Map();

  function setStatus(text, state) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.dataset.state = state;
  }

  function showSavedAt(iso) {
    if (!savedAt) return;
    savedAt.setAttribute("datetime", iso);
    savedAt.textContent = formatRelative(iso);
    savedAt.title = formatAbsolute(iso);
  }

  function languageOf(block) {
    const languageClass = Array.from(block.classList).find((name) => name.startsWith("language-"));
    return languageClass ? languageClass.slice("language-".length).toLowerCase() : "";
  }

  function highlightCodeBlocks() {
    preview.querySelectorAll("pre code").forEach((block) => {
      block.classList.add("hljs");

      const language = languageOf(block);
      if (!language || !hljs.getLanguage(language)) return;

      block.innerHTML = hljs.highlight(block.textContent, {
        language,
        ignoreIllegals: true,
      }).value;
    });
  }

  function lineStarts(code) {
    const starts = [0];

    for (let index = 0; index < code.length; index += 1) {
      if (code.charCodeAt(index) === 10) starts.push(index + 1);
    }

    return starts;
  }

  function positionAt(starts, offset) {
    let low = 0;
    let high = starts.length - 1;

    while (low < high) {
      const middle = Math.ceil((low + high) / 2);
      if (starts[middle] <= offset) low = middle;
      else high = middle - 1;
    }

    return { line: low + 1, column: offset - starts[low] + 1 };
  }

  function loadCheckModule(kind) {
    if (!checkModulePromises.has(kind)) {
      const url = kind === "ruby"
        ? workspace.dataset.rubySrc
        : workspace.dataset.lezerSrc;

      const promise = import(url).catch((error) => {
        checkModulePromises.delete(kind);
        throw error;
      });

      checkModulePromises.set(kind, promise);
    }

    return checkModulePromises.get(kind);
  }

  function checkWithLezer(parser, code) {
    const tree = parser.parse(code);
    const starts = lineStarts(code);
    const seen = new Set();
    const errors = [];

    tree.iterate({
      enter(node) {
        if (!node.type.isError) return true;

        const position = positionAt(starts, node.from);
        const rawSnippet = code.slice(node.from, node.to).replace(/\s+/g, " ").trim();
        const snippet = rawSnippet.length > 60
          ? `${rawSnippet.slice(0, 60)}…`
          : rawSnippet;
        const key = `${position.line}:${position.column}:${snippet}`;

        if (!seen.has(key) && errors.length < MAX_CHECK_ERRORS) {
          seen.add(key);
          errors.push({
            line: position.line,
            column: position.column,
            reason: snippet ? `语法错误：${snippet}` : "语法错误：缺少必要的语法元素",
            code: "syntax",
          });
        }

        return false;
      },
    });

    return errors;
  }

  async function checkCode(language, code) {
    const config = CHECKERS[language];

    if (config.checker === "ruby") {
      const module = await loadCheckModule("ruby");
      return module.checkRuby(code);
    }

    const module = await loadCheckModule("lezer");
    const parser = module.parsers[config.parser];
    if (!parser) throw new Error(`缺少 ${config.label} 解析器`);

    return checkWithLezer(parser, code);
  }

  function createLintUi(block, metaLabel) {
    const pre = block.closest("pre");
    if (!pre || !pre.parentNode) return null;

    const wrapper = document.createElement("div");
    wrapper.className = "code-block";
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const details = document.createElement("details");
    details.className = "lint-check";
    details.dataset.state = "checking";

    const summary = document.createElement("summary");
    summary.textContent = "⏳";
    summary.title = "正在检查代码…";
    summary.setAttribute("aria-label", summary.title);

    const panel = document.createElement("div");
    panel.className = "lint-details";

    const heading = document.createElement("p");
    heading.className = "lint-heading";
    heading.textContent = "正在检查…";

    const meta = document.createElement("p");
    meta.className = "lint-meta";
    meta.textContent = metaLabel;

    panel.append(heading, meta);
    details.append(summary, panel);
    wrapper.appendChild(details);

    return { details, summary, panel };
  }

  function updateLintUi(ui, errors, metaLabel) {
    const passed = errors.length === 0;
    const { details, summary, panel } = ui;

    details.dataset.state = passed ? "pass" : "fail";
    summary.textContent = passed ? "✅" : "❌";
    summary.title = passed
      ? "静态检查通过，点击查看详情"
      : `发现 ${errors.length} 个问题，点击查看详情`;
    summary.setAttribute("aria-label", summary.title);

    const heading = document.createElement("p");
    heading.className = "lint-heading";
    heading.textContent = passed
      ? "静态检查通过：未发现问题。"
      : `静态检查发现 ${errors.length} 个问题：`;

    panel.replaceChildren(heading);

    if (!passed) {
      const list = document.createElement("ol");
      list.className = "lint-errors";

      errors.forEach((error) => {
        const item = document.createElement("li");

        const location = document.createElement("span");
        location.className = "lint-location";
        location.textContent = `${error.line ?? "?"}:${error.column ?? "?"}`;

        const reason = document.createElement("span");
        reason.className = "lint-reason";
        reason.textContent = error.reason || "无法解析的语法";

        item.append(location, reason);

        if (error.code) {
          const code = document.createElement("code");
          code.textContent = error.code;
          item.appendChild(code);
        }

        list.appendChild(item);
      });

      panel.appendChild(list);
    }

    const meta = document.createElement("p");
    meta.className = "lint-meta";
    meta.textContent = metaLabel;
    panel.appendChild(meta);
  }

  async function runStaticChecks() {
    const blocks = Array.from(preview.querySelectorAll("pre code"));

    await Promise.all(blocks.map(async (block) => {
      if (block.dataset.lintChecked === "true") return;

      const language = LANGUAGE_ALIASES[languageOf(block)];
      if (!language) return;

      block.dataset.lintChecked = "true";

      const config = CHECKERS[language];
      const metaLabel = `${config.source} · ${config.label}`;
      const ui = createLintUi(block, metaLabel);
      if (!ui) return;

      try {
        const errors = await checkCode(language, block.textContent);
        if (!block.isConnected) return;
        updateLintUi(ui, errors, metaLabel);
      } catch (error) {
        if (!block.isConnected) return;
        updateLintUi(ui, [{
          line: 0,
          column: 0,
          reason: `检查失败：${error.message}`,
          code: "E000",
        }], metaLabel);
      }
    }));
  }

  const ALERT_LABELS = {
    note: { icon: "ℹ️", label: "注意" },
    tip: { icon: "💡", label: "提示" },
    important: { icon: "❗", label: "重要" },
    warning: { icon: "⚠️", label: "警告" },
    caution: { icon: "🛑", label: "谨慎" },
  };

  const ALERT_MARKER = /^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*/i;

  function takeAlertType(paragraph) {
    const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();

    while (node) {
      const match = node.data.match(ALERT_MARKER);
      if (match) {
        node.data = node.data.slice(match[0].length);
        return match[1].toLowerCase();
      }

      if (node.data.trim()) return null;
      node = walker.nextNode();
    }

    return null;
  }

  function enhanceAlerts() {
    preview.querySelectorAll("blockquote").forEach((blockquote) => {
      const first = blockquote.querySelector("p");
      if (!first) return;

      const type = takeAlertType(first);
      const alertConfig = type ? ALERT_LABELS[type] : null;
      if (!alertConfig) return;

      const alert = document.createElement("div");
      alert.className = `markdown-alert markdown-alert-${type}`;
      alert.dataset.alert = type;

      const title = document.createElement("p");
      title.className = "markdown-alert-title";
      title.textContent = `${alertConfig.icon} ${alertConfig.label}`;
      alert.appendChild(title);

      if (!first.textContent.trim() && first.children.length === 0) {
        first.remove();
      }

      while (blockquote.firstChild) alert.appendChild(blockquote.firstChild);
      blockquote.replaceWith(alert);
    });
  }

  function enhanceTaskLists() {
    preview.querySelectorAll('li > input[type="checkbox"]').forEach((checkbox) => {
      const item = checkbox.parentElement;
      if (!item || item.tagName !== "LI") return;

      item.classList.add("task-list-item");
      if (checkbox.checked) item.classList.add("task-list-item-completed");

      const list = item.parentElement;
      if (list && (list.tagName === "UL" || list.tagName === "OL")) {
        list.classList.add("contains-task-list");
      }
    });
  }

  const MERMAID_LANGUAGES = new Set(["mermaid", "mmd"]);
  const MERMAID_DARK_THEME = {
    background: "transparent",
    primaryColor: "#1f2a44",
    primaryTextColor: "#e9e9e6",
    primaryBorderColor: "#6ea8fe",
    lineColor: "#9c9c96",
    secondaryColor: "#1e1533",
    tertiaryColor: "#12261e",
    edgeLabelBackground: "#1f1f24",
    pie1: "#3b82f6",
    pie2: "#22c55e",
    pie3: "#f59e0b",
    pie4: "#a855f7",
    pie5: "#ec4899",
    pie6: "#14b8a6",
    pie7: "#f97316",
    pie8: "#8b5cf6",
    pie9: "#06b6d4",
    pie10: "#eab308",
    pie11: "#ef4444",
    pie12: "#84cc16",
  };
  let mermaidPromise = null;
  let mermaidSequence = 0;
  let mermaidQueue = Promise.resolve();
  const mermaidCache = new Map();
  const MERMAID_CACHE_LIMIT = 50;

  function cacheMermaidSvg(key, svg) {
    if (mermaidCache.has(key)) mermaidCache.delete(key);
    if (mermaidCache.size >= MERMAID_CACHE_LIMIT) {
      mermaidCache.delete(mermaidCache.keys().next().value);
    }
    mermaidCache.set(key, svg);
  }

  function loadMermaid() {
    if (typeof mermaid !== "undefined") return Promise.resolve(mermaid);
    if (mermaidPromise) return mermaidPromise;

    const source = workspace.dataset.mermaidSrc;
    if (!source) return Promise.reject(new Error("缺少 Mermaid 资源地址"));

    mermaidPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = source;
      script.async = true;

      script.onload = () => {
        if (typeof mermaid === "undefined") {
          reject(new Error("Mermaid 加载后不可用"));
          return;
        }
        resolve(mermaid);
      };

      script.onerror = () => {
        script.remove();
        reject(new Error("无法加载 Mermaid"));
      };

      document.head.appendChild(script);
    }).catch((error) => {
      mermaidPromise = null;
      throw error;
    });

    return mermaidPromise;
  }

  function isDarkTheme() {
    return typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  async function renderMermaidDiagram(container, code, key) {
    if (!container.isConnected) return;

    try {
      const mermaid = await loadMermaid();
      if (!container.isConnected) return;

      const dark = isDarkTheme();
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "default",
        themeVariables: dark ? MERMAID_DARK_THEME : {},
        fontFamily: getComputedStyle(document.body).fontFamily,
      });

      await mermaid.parse(code);
      if (!container.isConnected) return;

      const id = `mermaid-diagram-${++mermaidSequence}`;
      const { svg, bindFunctions } = await mermaid.render(id, code);
      if (!container.isConnected) return;

      container.innerHTML = svg;
      container.dataset.state = "ready";
      cacheMermaidSvg(key, svg);
      if (typeof bindFunctions === "function") bindFunctions(container);
    } catch (error) {
      if (!container.isConnected) return;

      container.dataset.state = "error";

      const title = document.createElement("p");
      title.className = "mermaid-error-title";
      title.textContent = "图表渲染失败";

      const message = document.createElement("p");
      message.className = "mermaid-error-message";
      message.textContent = error?.message || String(error);

      container.replaceChildren(title, message);
    }
  }

  function queueMermaidRender(container, code, key) {
    mermaidQueue = mermaidQueue
      .then(() => renderMermaidDiagram(container, code, key))
      .catch(() => {
        /* renderMermaidDiagram reports its own errors. */
      });
  }

  function enhanceMermaidDiagrams() {
    let index = 0;

    preview.querySelectorAll("pre code").forEach((block) => {
      if (!MERMAID_LANGUAGES.has(languageOf(block))) return;

      const pre = block.closest("pre");
      if (!pre) return;

      const code = block.textContent;
      const key = `${isDarkTheme() ? "dark" : "light"}:${index}:${code}`;
      index += 1;

      const container = document.createElement("div");
      container.className = "mermaid-diagram";
      container.dataset.state = "loading";

      const placeholder = document.createElement("p");
      placeholder.className = "mermaid-placeholder";
      placeholder.textContent = "正在渲染图表…";
      container.appendChild(placeholder);

      pre.replaceWith(container);

      const cached = mermaidCache.get(key);
      if (cached) {
        container.innerHTML = cached;
        container.dataset.state = "ready";
        return;
      }

      queueMermaidRender(container, code, key);
    });
  }

  function renderPreview() {
    if (!canRender) return;

    const rawHtml = marked.parse(textarea.value, {
      gfm: true,
      breaks: false,
      async: false,
    });
    preview.innerHTML = DOMPurify.sanitize(rawHtml, {
      USE_PROFILES: { html: true, svg: true, mathMl: true },
      FORBID_TAGS: ["style", "link"],
    });
    enhanceAlerts();
    enhanceTaskLists();
    enhanceMermaidDiagrams();
    highlightCodeBlocks();
    runStaticChecks();
  }

  function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(renderPreview, 150);
  }

  function scheduleSave(delay = 900) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, delay);
  }

  async function save() {
    if (saving) {
      queued = true;
      return;
    }
    if (!dirty) return;

    saving = true;
    dirty = false;
    setStatus("保存中…", "saving");

    try {
      const response = await fetch(`/api/world/${encodeURIComponent(noteId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: textarea.value }),
      });
      if (response.status === 413) {
        dirty = true;
        setStatus("内容过大，无法保存", "error");
        return;
      }
      if (!response.ok) throw new Error("save failed");

      const data = await response.json();
      showSavedAt(data.updated_at);

      if (dirty) {
        setStatus("正在输入…", "dirty");
        scheduleSave(400);
      } else {
        setStatus("已保存", "saved");
      }
    } catch (error) {
      dirty = true;
      setStatus("保存失败，正在重试…", "error");
      scheduleSave(4000);
    } finally {
      saving = false;
      if (queued) {
        queued = false;
        if (dirty) scheduleSave(200);
      }
    }
  }

  textarea.addEventListener("input", () => {
    dirty = true;
    setStatus("正在输入…", "dirty");
    schedulePreview();
    scheduleSave();
  });

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Tab" && !event.shiftKey) {
      event.preventDefault();
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      textarea.setRangeText("  ", start, end, "end");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
      return;
    }

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      clearTimeout(saveTimer);
      save();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (!dirty && !saving) return;
    event.preventDefault();
    event.returnValue = "";
  });

  if (typeof window.matchMedia === "function") {
    const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSchemeChange = () => renderPreview();

    if (typeof colorScheme.addEventListener === "function") {
      colorScheme.addEventListener("change", handleSchemeChange);
    } else if (typeof colorScheme.addListener === "function") {
      colorScheme.addListener(handleSchemeChange);
    }
  }

  renderPreview();
})();
