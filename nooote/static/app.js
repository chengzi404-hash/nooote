(() => {
  "use strict";

  function faIcon(name, label, extraClass) {
    const icon = document.createElement("i");
    icon.className = `fa-solid fa-${name}${extraClass ? ` ${extraClass}` : ""}`;
    icon.setAttribute("aria-hidden", "true");
    if (label) icon.title = label;
    return icon;
  }

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

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-confirm]");
    if (!form) return;
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });

  document.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-copy]");
    if (!trigger) return;

    const url = new URL(trigger.dataset.copy, window.location.origin).href;
    try {
      await navigator.clipboard.writeText(url);
      const original = trigger.textContent;
      trigger.textContent = "已复制";
      setTimeout(() => { trigger.textContent = original; }, 1500);
    } catch (error) {
      window.prompt("复制链接", url);
    }
  });

  const workspace = document.querySelector("[data-note-id], [data-share-id]");
  if (!workspace) return;

  const readOnly = workspace.hasAttribute("data-share-id");
  const noteId = workspace.dataset.noteId || workspace.dataset.shareId || "";
  const textarea = document.querySelector("#editor");
  const shareSource = document.querySelector("#share-source");
  const preview = document.querySelector("[data-preview]");
  const statusEl = document.querySelector("[data-status]");
  const savedAt = document.querySelector("[data-saved-at]");
  if (!preview || (!readOnly && !textarea)) return;

  function sourceText() {
    if (textarea) return textarea.value;
    return shareSource ? shareSource.value : "";
  }

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

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const fallback = document.createElement("textarea");
    fallback.value = text;
    fallback.setAttribute("readonly", "");
    fallback.style.position = "fixed";
    fallback.style.opacity = "0";
    document.body.appendChild(fallback);
    fallback.select();
    document.execCommand("copy");
    fallback.remove();
  }

  const COPY_RESET_MS = 1500;

  function createCopyButton(block) {
    const pre = block.closest("pre");
    if (!pre || !pre.parentNode) return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-block";
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "code-copy";
    button.title = "复制代码";
    button.setAttribute("aria-label", button.title);
    button.appendChild(faIcon("copy"));

    let resetTimer = null;

    button.addEventListener("click", async () => {
      try {
        await copyText(block.textContent);
        button.replaceChildren(faIcon("check"));
        button.dataset.state = "copied";
        button.title = "已复制";
        button.setAttribute("aria-label", button.title);
      } catch (error) {
        button.dataset.state = "error";
        button.title = "复制失败";
        button.setAttribute("aria-label", button.title);
      }

      clearTimeout(resetTimer);
      resetTimer = setTimeout(() => {
        button.replaceChildren(faIcon("copy"));
        delete button.dataset.state;
        button.title = "复制代码";
        button.setAttribute("aria-label", button.title);
      }, COPY_RESET_MS);
    });

    wrapper.appendChild(button);
  }

  function addCopyButtons() {
    preview.querySelectorAll("pre code").forEach(createCopyButton);
  }

  const ALERT_LABELS = {
    note: { icon: "circle-info", label: "注意" },
    tip: { icon: "lightbulb", label: "提示" },
    important: { icon: "circle-exclamation", label: "重要" },
    warning: { icon: "triangle-exclamation", label: "警告" },
    caution: { icon: "ban", label: "谨慎" },
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
      title.append(faIcon(alertConfig.icon, alertConfig.label), alertConfig.label);
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
  const MERMAID_VIEW_ACTIONS = {
    diagram: { icon: "code", label: "查看代码" },
    code: { icon: "diagram-project", label: "查看图表" },
  };
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
    const explicit = document.documentElement.dataset.theme;
    if (explicit === "dark") return true;
    if (explicit === "light") return false;
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

  function toggleMermaidView(block) {
    const showCode = block.dataset.view !== "code";
    block.dataset.view = showCode ? "code" : "diagram";

    const action = MERMAID_VIEW_ACTIONS[block.dataset.view];
    const button = block.querySelector(".mermaid-toggle");
    if (!button) return;

    button.replaceChildren(faIcon(action.icon));
    button.title = action.label;
    button.setAttribute("aria-label", action.label);
    button.setAttribute("aria-pressed", showCode ? "true" : "false");
  }

  preview.addEventListener("click", (event) => {
    const trigger = event.target.closest(".mermaid-toggle");
    if (!trigger) return;

    const block = trigger.closest(".mermaid-block");
    if (block) toggleMermaidView(block);
  });

  function createMermaidBlock() {
    const block = document.createElement("div");
    block.className = "mermaid-block";
    block.dataset.view = "diagram";

    const container = document.createElement("div");
    container.className = "mermaid-diagram";
    container.dataset.state = "loading";

    const placeholder = document.createElement("p");
    placeholder.className = "mermaid-placeholder";
    placeholder.textContent = "正在渲染图表…";
    container.appendChild(placeholder);

    const source = document.createElement("div");
    source.className = "mermaid-source";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "mermaid-toggle";
    button.title = MERMAID_VIEW_ACTIONS.diagram.label;
    button.setAttribute("aria-label", button.title);
    button.setAttribute("aria-pressed", "false");
    button.appendChild(faIcon(MERMAID_VIEW_ACTIONS.diagram.icon));

    block.append(container, source, button);
    return { block, container, source };
  }

  function enhanceMermaidDiagrams() {
    let index = 0;

    preview.querySelectorAll("pre code").forEach((codeBlock) => {
      if (!MERMAID_LANGUAGES.has(languageOf(codeBlock))) return;

      const pre = codeBlock.closest("pre");
      if (!pre) return;

      const code = codeBlock.textContent;
      const key = `${isDarkTheme() ? "dark" : "light"}:${index}:${code}`;
      index += 1;

      const { block, container, source } = createMermaidBlock();
      pre.replaceWith(block);
      source.appendChild(pre);

      const cached = mermaidCache.get(key);
      if (cached) {
        container.innerHTML = cached;
        container.dataset.state = "ready";
        return;
      }

      queueMermaidRender(container, code, key);
    });
  }

  const SCROLL_SYNC_MIN_WIDTH = 821;
  let scrollSyncLock = null;

  function scrollRatio(element) {
    const range = element.scrollHeight - element.clientHeight;
    return range > 0 ? element.scrollTop / range : 0;
  }

  function applyScrollRatio(target, ratio) {
    const range = target.scrollHeight - target.clientHeight;
    if (range > 0) target.scrollTop = ratio * range;
  }

  function syncScroll(source, target) {
    if (window.innerWidth < SCROLL_SYNC_MIN_WIDTH) return;

    if (scrollSyncLock) {
      const fromTarget = scrollSyncLock.element === source;
      const echoed = Math.abs(source.scrollTop - scrollSyncLock.top) <= 1;
      scrollSyncLock = null;
      if (fromTarget && echoed) return;
    }

    if (target.scrollHeight - target.clientHeight <= 0) return;

    const ratio = scrollRatio(source);
    const expected = ratio * (target.scrollHeight - target.clientHeight);
    if (Math.abs(target.scrollTop - expected) <= 1) return;

    scrollSyncLock = { element: target, top: expected };
    applyScrollRatio(target, ratio);
  }

  if (textarea) {
    textarea.addEventListener("scroll", () => syncScroll(textarea, preview), { passive: true });
    preview.addEventListener("scroll", () => syncScroll(preview, textarea), { passive: true });
  }

  function renderPreview() {
    if (!canRender) return;

    const ratio = textarea ? scrollRatio(textarea) : 0;

    const rawHtml = marked.parse(sourceText(), {
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
    addCopyButtons();

    if (textarea) applyScrollRatio(preview, ratio);
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
      const response = await fetch(`/api/console/notes/${encodeURIComponent(noteId)}`, {
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

  if (textarea) {
    const uploadTrigger = document.querySelector("[data-upload-trigger]");
    const uploadInput = document.querySelector("[data-upload-input]");

    function insertMarkdown(snippet) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const prefix = start > 0 && textarea.value[start - 1] !== "\n" ? "\n" : "";
      textarea.setRangeText(`${prefix}${snippet}\n`, start, end, "end");
      textarea.focus();
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
    }

    async function uploadFiles(files) {
      const selected = Array.from(files || []);
      if (selected.length === 0) return;

      setStatus(`上传中… (0/${selected.length})`, "saving");

      try {
        for (let index = 0; index < selected.length; index += 1) {
          const body = new FormData();
          body.append("file", selected[index]);

          const response = await fetch("/api/console/attachments", {
            method: "POST",
            body,
          });
          if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.error || "上传失败");
          }

          const data = await response.json();
          insertMarkdown(data.markdown);
          setStatus(`上传中… (${index + 1}/${selected.length})`, "saving");
        }
        setStatus("正在输入…", "dirty");
      } catch (error) {
        setStatus(error.message || "上传失败", "error");
      }
    }

    if (uploadTrigger && uploadInput) {
      uploadTrigger.addEventListener("click", () => uploadInput.click());
      uploadInput.addEventListener("change", () => {
        uploadFiles(uploadInput.files);
        uploadInput.value = "";
      });
    }

    textarea.addEventListener("dragover", (event) => {
      if (event.dataTransfer && Array.from(event.dataTransfer.types).includes("Files")) {
        event.preventDefault();
      }
    });

    textarea.addEventListener("drop", (event) => {
      if (!event.dataTransfer || event.dataTransfer.files.length === 0) return;
      event.preventDefault();
      uploadFiles(event.dataTransfer.files);
    });

    textarea.addEventListener("paste", (event) => {
      const files = event.clipboardData ? Array.from(event.clipboardData.files) : [];
      if (files.length === 0) return;
      event.preventDefault();
      uploadFiles(files);
    });

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
  }

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
