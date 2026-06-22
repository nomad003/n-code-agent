(function () {
  const EXAMPLE_LOG = `15:04:47:429[61285][0000006133] [Error] GetEnemySkillConfigX(skillconfig.cpp:489) enemy conf skill:[0 921948522 monster_livinglaser_lightstream] not find
15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:80) [COMBAT] unit: [type=enemy uid=1153743939307804815 tid=302250101 role=0 user= name= sid=0 scene=0-0 map=0], caster:302250101 skill:[921948522 monster_livinglaser_lightstream] not find in conf
15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:81) Check cond: <false> failed
15:04:47:429[61285][0000006133] [Error] Log_FlushOnExit(LogInit.cpp:347) *************** Error Exit ***************`;

  const GRAPH_GROUPS = {
    module: { label: "模块", color: "#a78bfa", glow: "rgba(167,139,250,0.55)" },
    playbook: { label: "手册", color: "#38bdf8", glow: "rgba(56,189,248,0.55)" },
    qa: { label: "问答", color: "#34d399", glow: "rgba(52,211,153,0.55)" },
    config: { label: "配置", color: "#fbbf24", glow: "rgba(251,191,36,0.55)" },
    code: { label: "代码", color: "#60a5fa", glow: "rgba(96,165,250,0.55)" },
    tag: { label: "标签", color: "#94a3b8", glow: "rgba(148,163,184,0.35)" },
    symbol: { label: "符号", color: "#22d3ee", glow: "rgba(34,211,238,0.45)" },
    log: { label: "日志", color: "#fb7185", glow: "rgba(251,113,133,0.45)" },
    assert: { label: "断言", color: "#f97316", glow: "rgba(249,115,22,0.42)" },
    question_type: { label: "类型", color: "#c084fc", glow: "rgba(192,132,252,0.42)" },
    resource: { label: "路径", color: "#4ade80", glow: "rgba(74,222,128,0.38)" },
    other: { label: "其他", color: "#fb7185", glow: "rgba(251,113,133,0.45)" },
  };

  const GRAPH_RELATIONS = [
    {
      id: "links_to",
      label: "内部链接",
      short_label: "link",
      description: "正文 Markdown 链接指向另一个知识卡片。",
    },
    {
      id: "tagged_with",
      label: "标签归类",
      short_label: "tag",
      description: "frontmatter tags 声明了该标签。",
    },
    {
      id: "owns_symbol",
      label: "关键符号",
      short_label: "symbol",
      description: "frontmatter symbols 声明了关键类、函数或类型。",
    },
    {
      id: "emits_log",
      label: "日志线索",
      short_label: "log",
      description: "frontmatter logs 声明了常见日志关键字或错误文本。",
    },
    {
      id: "checks_assert",
      label: "断言线索",
      short_label: "assert",
      description: "frontmatter asserts 声明了常见断言、CHECK 或错误条件。",
    },
    {
      id: "answers_question_type",
      label: "问题类型",
      short_label: "intent",
      description: "frontmatter question_types 声明了适用问题类型。",
    },
    {
      id: "documents_resource",
      label: "代码资源",
      short_label: "path",
      description: "frontmatter resource 声明了卡片描述的模块路径或代码资源。",
    },
    {
      id: "part_of",
      label: "组成/从属",
      short_label: "part",
      description: "A part_of B：A 是 B 的一个组成部分。",
    },
    {
      id: "supplements",
      label: "补充",
      short_label: "plus",
      description: "A supplements B：A 为 B 提供额外细节、示例或背景信息。",
    },
    {
      id: "contradicts",
      label: "冲突",
      short_label: "conflict",
      description: "A contradicts B：A 与 B 的描述存在不一致，需要人工复核。",
    },
    {
      id: "supersedes",
      label: "取代",
      short_label: "newer",
      description: "A supersedes B：A 是 B 的更新版本，B 不再是最新有效信息。",
    },
    {
      id: "depends_on",
      label: "依赖",
      short_label: "dep",
      description: "A depends_on B：理解 A 需要先了解 B 的内容。",
    },
  ];

  const MERMAID_FENCE_LANGS = new Set([
    "mermaid",
    "flowchart",
    "graph",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "statediagram-v2",
    "erdiagram",
    "journey",
    "gantt",
    "pie",
    "gitgraph",
    "mindmap",
    "timeline",
    "quadrantchart",
    "requirementdiagram",
    "c4context",
    "c4container",
    "c4component",
    "c4dynamic",
    "xychart",
    "block",
    "packet",
  ]);

  const MERMAID_LABELS = {
    flowchart: "流程图",
    graph: "流程图",
    sequenceDiagram: "时序图",
    classDiagram: "类图",
    stateDiagram: "状态图",
    "stateDiagram-v2": "状态图",
    erDiagram: "ER 图",
    journey: "用户旅程",
    gantt: "甘特图",
    pie: "饼图",
    gitGraph: "Git 图",
    mindmap: "思维导图",
    timeline: "时间线",
    quadrantChart: "四象限图",
    requirementDiagram: "需求图",
    C4Context: "C4 图",
    C4Container: "C4 图",
    C4Component: "C4 图",
    C4Dynamic: "C4 图",
    xychart: "XY 图",
    block: "Block 图",
    packet: "Packet 图",
  };

  let diagramSeq = 0;
  let mermaidLoadPromise = null;

  function pathToView(pathname) {
    if (pathname.indexOf("/admin/llm-traces") === 0) return "traces";
    if (pathname.indexOf("/knowledge/graph") === 0) return "graph";
    if (pathname.indexOf("/knowledge") === 0) return "knowledge";
    return "ask";
  }

  function eventText(row) {
    return row.answer || row.content || row.text || row.output || row.error || "";
  }

  function compactText(value, limit = 260) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (!text) return "";
    return text.length > limit ? text.slice(0, limit - 1) + "..." : text;
  }

  function clipText(value, limit = 3600) {
    const text = String(value || "").trim();
    if (!text) return "";
    return text.length > limit ? text.slice(0, limit - 1) + "..." : text;
  }

  function asPrettyJson(value, limit = 3600) {
    if (value === undefined || value === null || value === "") return "";
    let text = "";
    if (typeof value === "string") {
      try {
        text = JSON.stringify(JSON.parse(value), null, 2);
      } catch (_err) {
        text = value;
      }
    } else {
      text = JSON.stringify(value, null, 2);
    }
    return text.length > limit ? text.slice(0, limit - 1) + "..." : text;
  }

  function messageContent(message) {
    const content = message && message.content;
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      return content
        .map((part) => (typeof part === "string" ? part : part.text || ""))
        .filter(Boolean)
        .join("\n");
    }
    return "";
  }

  function rowText(row) {
    if (!row) return "";
    if (row.message) return messageContent(row.message);
    if (row.result && typeof row.result === "string") return row.result;
    return eventText(row);
  }

  function rowToolName(row) {
    if (!row) return "";
    if (row.name || row.tool || row.function) return row.name || row.tool || row.function;
    const calls = row.message && row.message.tool_calls;
    if (Array.isArray(calls) && calls.length) {
      return calls
        .map((call) => (call.function && call.function.name) || call.name || "")
        .filter(Boolean)
        .join(", ");
    }
    return "";
  }

  function rowToolCalls(row) {
    const calls = row && row.message && row.message.tool_calls;
    if (!Array.isArray(calls)) return [];
    return calls.map((call, index) => ({
      key: `${row.round || "r"}-call-${index}`,
      event: "tool_call",
      name: (call.function && call.function.name) || call.name || "tool",
      arguments: asPrettyJson((call.function && call.function.arguments) || call.input || call.arguments),
      result: "",
      is_error: false,
    }));
  }

  function traceDuration(rows) {
    if (!rows.length) return "";
    const first = Date.parse(rows[0].ts || "");
    const last = Date.parse(rows[rows.length - 1].ts || "");
    if (!Number.isFinite(first) || !Number.isFinite(last) || last < first) return "";
    const ms = last - first;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)}s`;
  }

  function formatBytesValue(size) {
    const value = Number(size || 0);
    if (!value) return "0 B";
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }

  function buildTraceSummary(rows, header = {}) {
    const traceRows = rows || [];
    const isRoundStart = (row) => row.event === "llm_request" || row.event === "sdk_request";
    const isToolEvent = (row) => (
      row.event === "tool_result"
      || row.event === "sdk_tool_use"
      || row.event === "tool_call"
      || Boolean(row.tool || row.name)
    );
    const llmRequests = traceRows.filter((row) => row.event === "llm_request");
    const llmResponses = traceRows.filter((row) => row.event === "llm_response");
    const toolRows = traceRows.filter(isToolEvent);
    const anchors = traceRows
      .map((row, index) => ({ row, index }))
      .filter((item) => isRoundStart(item.row));
    const hasModelRequest = Boolean(anchors.length);
    if (!anchors.length && traceRows.length) anchors.push({ row: traceRows[0], index: 0 });

    const roundDetails = anchors.map((anchor, i) => {
      const end = anchors[i + 1] ? anchors[i + 1].index : traceRows.length;
      const slice = traceRows.slice(anchor.index, end);
      const request = slice.find(isRoundStart) || {};
      const messages = Array.isArray(request.messages) ? request.messages : [];
      const userMessage = [...messages].reverse().find((message) => message.role === "user");
      const toolRequests = slice.flatMap(rowToolCalls);
      const toolResults = slice
        .filter((row) => row.event === "tool_result" || row.event === "sdk_tool_use" || row.event === "tool_call")
        .map((row, index) => ({
          key: `${anchor.index}-${index}-${row.name || row.event}`,
          event: row.event || "tool_result",
          name: rowToolName(row) || "tool",
          arguments: asPrettyJson(row.arguments || row.input || row.raw_arguments, 1400),
          result: clipText(row.result || row.content || row.output || row.error || "", 2600),
          is_error: Boolean(row.is_error || row.error),
        }));
      const responseRows = slice.filter((row) => (
        row.event === "llm_response"
        || row.event === "llm_error"
        || row.event === "sdk_text"
        || row.event === "sdk_result"
        || row.event === "final_answer"
        || row.event === "request_end"
        || row.event === "shortcut"
        || row.event === "cache_hit"
      ));
      const answerParts = [];
      responseRows.forEach((row) => {
        const text = clipText(rowText(row), 3600);
        if (text && !answerParts.includes(text)) answerParts.push(text);
      });
      const tools = Array.from(new Set(
        [...toolRequests, ...toolResults]
          .map((item) => item.name)
          .filter(Boolean)
      ));
      return {
        id: request.round || anchor.row.round || i + 1,
        events: slice.length,
        duration: traceDuration(slice),
        model: request.model || anchor.row.model || header.model || "",
        messageCount: messages.length || (request.prompt ? 1 : 0),
        withTools: request.with_tools === true ? "开启" : request.with_tools === false ? "关闭" : "-",
        userPrompt: clipText(messageContent(userMessage) || request.prompt || header.question || "", 1800),
        tools,
        toolResults: [...toolRequests, ...toolResults],
        answer: answerParts.join("\n\n"),
        raw: slice.map((row) => JSON.stringify(row, null, 2)).join("\n"),
      };
    });

    const findings = [];
    if (!traceRows.length) {
      findings.push("请选择一个 trace 文件。");
    } else {
      if (!hasModelRequest) findings.push("没有记录模型请求事件，无法复盘提示词输入。");
      if (!toolRows.length) findings.push("没有工具调用记录，复杂代码问题可能缺少代码检索证据。");
      if (!traceRows.some((row) => row.event === "request_end" || row.event === "final_answer")) {
        findings.push("没有看到 request_end/final_answer，确认请求是否中途失败。");
      }
      if (llmResponses.length > 4) findings.push("LLM 轮次偏多，建议检查工具结果是否足够聚焦。");
    }

    return {
      rounds: roundDetails.length,
      tools: toolRows.length,
      findings,
      roundDetails,
    };
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttr(text) {
    return escapeHtml(text).replace(/`/g, "&#96;");
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/!\[([^\]]*)\]\((https?:\/\/[^)\s]+|\/[^)\s]+|\.{1,2}\/[^)\s]+|[^):\s][^)\s]*)\)/g, '<img src="$2" alt="$1" loading="lazy">')
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
      .replace(/\[([^\]]+)\]\(([^):\s][^)\s]*)\)/g, '<span class="internal-link">$1</span>');
  }

  function parseTableRow(line) {
    return line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell) => cell.trim());
  }

  function isTableLine(line) {
    return /^\s*\|.+\|\s*$/.test(line || "");
  }

  function isTableSeparator(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || "");
  }

  function normalizedFenceLang(info) {
    return String(info || "").trim().split(/\s+/)[0].replace(/[{}]/g, "");
  }

  function mermaidDirective(source) {
    const first = String(source || "").trim().split(/\r?\n/, 1)[0] || "";
    return first.trim().split(/\s+/, 1)[0] || "mermaid";
  }

  function diagramLabel(source, lang) {
    const directive = mermaidDirective(source);
    if (MERMAID_LABELS[directive]) return MERMAID_LABELS[directive];
    const normalized = String(lang || "").toLowerCase();
    const key = Object.keys(MERMAID_LABELS).find((item) => item.toLowerCase() === normalized);
    return key ? MERMAID_LABELS[key] : "图";
  }

  function isMermaidFence(lang) {
    return MERMAID_FENCE_LANGS.has(String(lang || "").toLowerCase());
  }

  function normalizedMermaidSource(lang, source) {
    const raw = String(source || "").trim();
    const normalized = String(lang || "").trim();
    const lower = normalized.toLowerCase();
    if (!raw || lower === "mermaid") return raw;
    if (!isMermaidFence(normalized)) return raw;
    const first = mermaidDirective(raw).toLowerCase();
    if (MERMAID_FENCE_LANGS.has(first)) return raw;
    if ((lower === "flowchart" || lower === "graph") && /^(td|lr|bt|rl)\b/i.test(raw)) {
      return `${normalized} ${raw}`;
    }
    return `${normalized}\n${raw}`;
  }

  function renderDiagramFence(lang, source) {
    const diagramSource = normalizedMermaidSource(lang, source);
    const label = diagramLabel(diagramSource, lang);
    return [
      `<figure class="diagram-card" data-diagram-engine="mermaid" data-diagram-lang="${escapeAttr(lang || "mermaid")}">`,
      '<figcaption><span>Mermaid</span><strong>' + escapeHtml(label) + '</strong><em class="diagram-status">待渲染</em></figcaption>',
      '<div class="diagram-stage"><div class="diagram-canvas" aria-label="' + escapeAttr(label) + '"></div></div>',
      '<pre class="diagram-source"><code>' + escapeHtml(diagramSource) + '</code></pre>',
      "</figure>",
    ].join("");
  }

  function stripFrontMatter(markdown) {
    const text = String(markdown || "");
    if (!text.startsWith("---\n")) return text;
    const end = text.indexOf("\n---", 4);
    if (end < 0) return text;
    return text.slice(end + 4).replace(/^\s+/, "");
  }

  function renderMarkdown(markdown, emptyText = "选择或新建一个知识卡片。") {
    const lines = stripFrontMatter(markdown).split(/\r?\n/);
    const html = [];
    let inCode = false;
    let codeLang = "";
    let code = [];
    let list = [];
    let paragraph = [];
    let table = [];

    function flushParagraph() {
      if (!paragraph.length) return;
      html.push("<p>" + paragraph.map(renderInline).join("<br>") + "</p>");
      paragraph = [];
    }

    function flushList() {
      if (!list.length) return;
      html.push("<ul>" + list.map((item) => "<li>" + renderInline(item) + "</li>").join("") + "</ul>");
      list = [];
    }

    function flushCode() {
      const source = code.join("\n");
      if (isMermaidFence(codeLang)) {
        html.push(renderDiagramFence(codeLang || "mermaid", source));
      } else {
        const langClass = codeLang ? ` class="language-${escapeAttr(codeLang)}"` : "";
        html.push("<pre><code" + langClass + ">" + escapeHtml(source) + "</code></pre>");
      }
      code = [];
      codeLang = "";
    }

    function flushTable() {
      if (!table.length) return;
      if (table.length < 2 || !isTableSeparator(table[1])) {
        table.forEach((line) => paragraph.push(line));
        table = [];
        return;
      }
      const header = parseTableRow(table[0]);
      const body = table.slice(2).map(parseTableRow);
      html.push(
        '<div class="markdown-table-wrap"><table><thead><tr>'
        + header.map((cell) => "<th>" + renderInline(cell) + "</th>").join("")
        + "</tr></thead><tbody>"
        + body.map((row) => "<tr>" + row.map((cell) => "<td>" + renderInline(cell) + "</td>").join("") + "</tr>").join("")
        + "</tbody></table></div>"
      );
      table = [];
    }

    for (const line of lines) {
      const fence = /^```\s*([^`]*)$/.exec(line.trim());
      if (fence) {
        if (inCode) {
          flushCode();
          inCode = false;
        } else {
          flushParagraph();
          flushList();
          flushTable();
          inCode = true;
          codeLang = normalizedFenceLang(fence[1]);
        }
        continue;
      }
      if (inCode) {
        code.push(line);
        continue;
      }
      if (isTableLine(line)) {
        flushParagraph();
        flushList();
        table.push(line);
        continue;
      }
      if (!line.trim()) {
        flushParagraph();
        flushList();
        flushTable();
        continue;
      }
      const heading = /^(#{1,4})\s+(.+)$/.exec(line);
      if (heading) {
        flushParagraph();
        flushList();
        flushTable();
        const level = heading[1].length;
        html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        continue;
      }
      const bullet = /^\s*[-*]\s+(.+)$/.exec(line);
      if (bullet) {
        flushParagraph();
        flushTable();
        list.push(bullet[1]);
        continue;
      }
      flushTable();
      paragraph.push(line);
    }
    if (inCode) flushCode();
    flushParagraph();
    flushList();
    flushTable();
    return html.join("\n") || '<p class="empty">' + escapeHtml(emptyText) + '</p>';
  }

  function readSidebarCollapsed() {
    try {
      return window.localStorage.getItem("code-agent.sidebarCollapsed") === "1";
    } catch (_err) {
      return false;
    }
  }

  function saveSidebarCollapsed(value) {
    try {
      window.localStorage.setItem("code-agent.sidebarCollapsed", value ? "1" : "0");
    } catch (_err) {
      // Local storage can be disabled in embedded browsers; the current session still works.
    }
  }

  function readTheme() {
    try {
      return window.localStorage.getItem("code-agent.theme") === "light" ? "light" : "dark";
    } catch (_err) {
      return "dark";
    }
  }

  function saveTheme(value) {
    try {
      window.localStorage.setItem("code-agent.theme", value);
    } catch (_err) {
      // Local storage can be disabled in embedded browsers; the current session still works.
    }
  }

  function applyDocumentTheme(value) {
    document.documentElement.classList.toggle("theme-light", value === "light");
  }

  function cssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function encodePath(path) {
    return String(path || "")
      .split("/")
      .map((segment) => encodeURIComponent(segment))
      .join("/");
  }

  applyDocumentTheme(readTheme());

  async function fallbackApiJson(url) {
    const res = await fetch(url);
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (_err) {
      data = { raw: text };
    }
    if (!res.ok) throw new Error(data.detail || data.error || text || res.statusText);
    return data;
  }

  function traceHeaderFrom(file, rows) {
    const first = (rows || [])[0] || {};
    return {
      file: file.file || first.request_id || "",
      question: file.question || first.question || "",
      mode: file.mode || first.mode || "",
      backend: file.backend || first.backend || "",
      model: file.model || first.model || "",
      size: file.size || 0,
    };
  }

  function renderTraceFallback() {
    const root = document.getElementById("app");
    if (!root) return;
    document.body.classList.add("vue-missing");
    root.removeAttribute("v-cloak");
    root.className = "";

    if (pathToView(window.location.pathname) !== "traces") {
      root.innerHTML = `
        <main class="main">
          <section class="notice danger">
            Vue 没有加载成功，请检查浏览器是否能访问 Vue CDN。当前页面已停止渲染，请使用 /admin/llm-traces 查看 trace 兜底页面。
          </section>
        </main>`;
      return;
    }

    root.innerHTML = `
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-copy">
            <div class="brand-title">Code Agent Workbench</div>
            <div class="brand-subtitle">代码调查 / 调用复盘 / 知识沉淀</div>
          </div>
        </div>
        <nav class="nav">
          <button type="button" onclick="location.href='/ui'" title="代码调查"><span class="nav-icon">Q</span><span class="nav-text">调查</span></button>
          <button type="button" class="active" title="调用复盘"><span class="nav-icon">T</span><span class="nav-text">复盘</span></button>
          <button type="button" onclick="location.href='/knowledge'" title="知识工作台"><span class="nav-icon">K</span><span class="nav-text">知识</span></button>
          <button type="button" onclick="location.href='/knowledge/graph'" title="知识图谱"><span class="nav-icon">G</span><span class="nav-text">图谱</span></button>
        </nav>
        <div class="side-note">
          <div class="label">前端状态</div>
          <strong>Vue CDN 未加载</strong>
        </div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div>
            <h1>调用复盘</h1>
            <p>Vue 未加载时的 trace 兜底视图，可查看会话、问题、Round 和原始事件。</p>
          </div>
          <div class="topbar-actions">
            <button class="ghost" type="button" id="fallback-refresh">刷新</button>
          </div>
        </header>
        <section class="workspace trace-layout">
          <div class="panel list-panel trace-list-panel">
            <div class="panel-head"><h2>会话</h2><span class="pill" id="fallback-count">0</span></div>
            <div class="trace-dir"><span>目录</span><strong id="fallback-dir">logs/llm</strong></div>
            <div id="fallback-list" class="fallback-list"></div>
          </div>
          <div class="panel trace-detail-panel" id="fallback-detail">
            <div class="trace-question-card">
              <div class="trace-question-label">问题</div>
              <h2>正在加载 trace...</h2>
            </div>
          </div>
        </section>
      </main>`;

    const listEl = root.querySelector("#fallback-list");
    const detailEl = root.querySelector("#fallback-detail");
    const countEl = root.querySelector("#fallback-count");
    const dirEl = root.querySelector("#fallback-dir");
    const state = { files: [], selected: "", traceDir: "" };

    function renderList() {
      countEl.textContent = String(state.files.length);
      dirEl.textContent = state.traceDir || "logs/llm";
      if (!state.files.length) {
        listEl.innerHTML = '<div class="trace-empty">暂无 trace 文件。</div>';
        return;
      }
      listEl.innerHTML = state.files.map((file) => `
        <button type="button" class="list-item trace-session ${state.selected === file.file ? "active" : ""}" data-file="${escapeHtml(file.file)}">
          <span class="trace-session-question">${escapeHtml(compactText(file.question || "无问题文本", 96))}</span>
          <small class="trace-session-meta">${escapeHtml([file.mode || "mode -", file.backend || "backend -", file.last_event || "event -", file.last_ts || file.mtime || ""].filter(Boolean).join(" · "))}</small>
          <small class="trace-session-file">${escapeHtml(file.file)}</small>
        </button>`).join("");
      listEl.querySelectorAll("[data-file]").forEach((button) => {
        button.addEventListener("click", () => loadTrace(button.dataset.file));
      });
    }

    function renderDetail(file, rows) {
      const header = traceHeaderFrom(file, rows);
      const summary = buildTraceSummary(rows, header);
      const findings = summary.findings.length ? `
        <div class="notice">
          <strong>质量检查</strong>
          <ul>${summary.findings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>` : "";
      const rounds = summary.roundDetails.map((round, index) => `
        <details class="round-card" ${index === 0 ? "open" : ""}>
          <summary>
            <span class="round-title">Round ${escapeHtml(round.id)}</span>
            <span class="round-summary">${round.events} events · ${round.tools.length} tools · ${escapeHtml(round.duration || "-")}</span>
          </summary>
          <div class="round-body">
            <div class="round-grid">
              <div class="round-panel">
                <h4>模型输入</h4>
                <dl class="trace-kv">
                  <div><dt>模型</dt><dd>${escapeHtml(round.model || "-")}</dd></div>
                  <div><dt>消息</dt><dd>${round.messageCount} 条</dd></div>
                  <div><dt>工具开关</dt><dd>${escapeHtml(round.withTools)}</dd></div>
                </dl>
                ${round.userPrompt ? `<pre>${escapeHtml(round.userPrompt)}</pre>` : ""}
              </div>
              <div class="round-panel">
                <h4>模型输出</h4>
                ${round.answer ? `<pre>${escapeHtml(round.answer)}</pre>` : '<div class="trace-muted">本轮没有文本输出。</div>'}
              </div>
            </div>
            <div class="round-panel">
              <h4>工具链</h4>
              <div class="tool-chain">
                ${round.tools.length ? round.tools.map((tool) => `<span>${escapeHtml(tool)}</span>`).join("") : "<em>未调用工具</em>"}
              </div>
              <div class="tool-results">
                ${round.toolResults.map((tool) => `
                  <div class="tool-result ${tool.is_error ? "danger" : ""}">
                    <div class="tool-result-head"><strong>${escapeHtml(tool.name)}</strong><span>${escapeHtml(tool.event)}</span></div>
                    ${tool.arguments ? `<pre>${escapeHtml(tool.arguments)}</pre>` : ""}
                    ${tool.result ? `<pre>${escapeHtml(tool.result)}</pre>` : ""}
                  </div>`).join("")}
              </div>
            </div>
            <details class="raw-round">
              <summary>本轮原始事件</summary>
              <pre>${escapeHtml(round.raw)}</pre>
            </details>
          </div>
        </details>`).join("");

      detailEl.innerHTML = `
        <div class="trace-question-card">
          <div class="trace-question-label">问题</div>
          <h2>${escapeHtml(header.question || "请选择一个会话")}</h2>
          <div class="trace-meta">
            <span>${escapeHtml(header.file || "-")}</span>
            <span>${escapeHtml(header.mode || "mode -")}</span>
            <span>${escapeHtml(header.backend || "backend -")}</span>
            <span>${escapeHtml(header.model || "model -")}</span>
            <span>${escapeHtml(formatBytesValue(header.size))}</span>
          </div>
        </div>
        <div class="metrics">
          <div><strong>${summary.rounds}</strong><span>Round</span></div>
          <div><strong>${summary.tools}</strong><span>工具事件</span></div>
          <div><strong>${summary.findings.length}</strong><span>检查项</span></div>
        </div>
        ${findings}
        <div class="trace-section-head"><h3>Round 明细</h3><span>${rows.length} events</span></div>
        ${rounds}
        <details class="raw-all">
          <summary>原始事件</summary>
          <pre>${escapeHtml(rows.map((row) => JSON.stringify(row, null, 2)).join("\n"))}</pre>
        </details>`;
    }

    async function loadTrace(name) {
      state.selected = name;
      renderList();
      detailEl.innerHTML = '<div class="trace-question-card"><div class="trace-question-label">问题</div><h2>读取 trace...</h2></div>';
      try {
        const data = await fallbackApiJson("/admin/llm-traces/api/" + encodeURIComponent(name));
        const file = state.files.find((item) => item.file === name) || { file: name };
        renderDetail(file, data.rows || []);
      } catch (err) {
        detailEl.innerHTML = `<div class="notice danger">读取 trace 失败：${escapeHtml(err.message || err)}</div>`;
      }
    }

    async function loadTraces() {
      try {
        const data = await fallbackApiJson("/admin/llm-traces/api");
        state.traceDir = data.trace_dir || "";
        state.files = data.files || [];
        state.selected = state.files[0] ? state.files[0].file : "";
        renderList();
        if (state.selected) {
          await loadTrace(state.selected);
        } else {
          detailEl.innerHTML = '<div class="notice">暂无 trace 文件。</div>';
        }
      } catch (err) {
        listEl.innerHTML = `<div class="notice danger">加载 trace 失败：${escapeHtml(err.message || err)}</div>`;
      }
    }

    root.querySelector("#fallback-refresh").addEventListener("click", loadTraces);
    loadTraces();
  }

  function loadScript(src, timeoutMs = 2500) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      let done = false;
      const timer = window.setTimeout(() => {
        if (done) return;
        done = true;
        script.remove();
        reject(new Error("script load timeout: " + src));
      }, timeoutMs);
      script.onload = () => {
        if (done) return;
        done = true;
        window.clearTimeout(timer);
        resolve();
      };
      script.onerror = () => {
        if (done) return;
        done = true;
        window.clearTimeout(timer);
        script.remove();
        reject(new Error("script load failed: " + src));
      };
      script.src = src;
      document.head.appendChild(script);
    });
  }

  async function loadAnyScript(sources, isReady, timeoutMs) {
    if (isReady()) return true;
    for (const src of sources) {
      try {
        await loadScript(src, timeoutMs);
        if (isReady()) return true;
      } catch (_err) {
        // Try the next source.
      }
    }
    return false;
  }

  async function ensureVue() {
    const loaded = await loadAnyScript(
      ["/static/vendor/vue.global.prod.js", "https://unpkg.com/vue@3/dist/vue.global.prod.js"],
      () => Boolean(window.Vue && window.Vue.createApp),
      2500
    );
    if (!loaded) throw new Error("Vue unavailable");
    window.__CODE_AGENT_VUE_READY__ = true;
  }

  function loadVisNetwork() {
    loadAnyScript(
      ["/static/vendor/vis-network.min.js", "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"],
      () => Boolean(window.vis && window.vis.Network),
      2500
    ).catch(() => {});
  }

  function loadMermaid() {
    if (!mermaidLoadPromise) {
      mermaidLoadPromise = loadAnyScript(
        ["/static/vendor/mermaid.min.js", "https://unpkg.com/mermaid@10/dist/mermaid.min.js"],
        () => Boolean(window.mermaid && window.mermaid.render),
        4000
      );
    }
    return mermaidLoadPromise;
  }

  function initMermaidTheme() {
    if (!window.mermaid || !window.mermaid.initialize) return;
    const isLight = document.documentElement.classList.contains("theme-light");
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: isLight ? "base" : "dark",
      themeVariables: {
        background: cssVar("--surface-2", isLight ? "#ffffff" : "#111929"),
        primaryColor: cssVar("--surface-3", isLight ? "#e7edf7" : "#18223a"),
        primaryTextColor: cssVar("--text", isLight ? "#162033" : "#f1f5ff"),
        primaryBorderColor: cssVar("--border-2", isLight ? "#b9c8dc" : "#253452"),
        lineColor: cssVar("--blue-hi", isLight ? "#1e55c4" : "#7badfa"),
        secondaryColor: cssVar("--blue-dim", isLight ? "#e7efff" : "#0b1830"),
        tertiaryColor: cssVar("--code-bg-soft", isLight ? "#e8eef7" : "#080d1c"),
        noteBkgColor: cssVar("--surface-4", isLight ? "#dce6f3" : "#1e2c45"),
        noteTextColor: cssVar("--text", isLight ? "#162033" : "#f1f5ff"),
        actorBkg: cssVar("--surface-3", isLight ? "#e7edf7" : "#18223a"),
        actorTextColor: cssVar("--text", isLight ? "#162033" : "#f1f5ff"),
        actorBorder: cssVar("--border-2", isLight ? "#b9c8dc" : "#253452"),
        signalColor: cssVar("--text-2", isLight ? "#526278" : "#a0b4cc"),
        signalTextColor: cssVar("--text", isLight ? "#162033" : "#f1f5ff"),
        fontFamily: cssVar("--font", "\"Plus Jakarta Sans\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"),
      },
    });
  }

  function setDiagramStatus(figure, text, failed) {
    const status = figure.querySelector(".diagram-status");
    if (status) status.textContent = text;
    figure.classList.toggle("has-error", Boolean(failed));
  }

  async function renderKnowledgeDiagrams(force = false) {
    const figures = Array.from(document.querySelectorAll('.markdown-preview .diagram-card[data-diagram-engine="mermaid"]'));
    if (!figures.length) return;
    if (force) {
      figures.forEach((figure) => {
        figure.dataset.diagramRendered = "";
        figure.dataset.diagramRendering = "";
        figure.classList.remove("is-rendered", "has-error");
        const canvas = figure.querySelector(".diagram-canvas");
        if (canvas) canvas.innerHTML = "";
        setDiagramStatus(figure, "待渲染", false);
      });
    }
    const pending = figures.filter((figure) => figure.dataset.diagramRendered !== "1" && figure.dataset.diagramRendering !== "1");
    if (!pending.length) return;
    pending.forEach((figure) => {
      figure.dataset.diagramRendering = "1";
      setDiagramStatus(figure, "渲染中", false);
    });
    const loaded = await loadMermaid();
    if (!loaded || !window.mermaid) {
      pending.forEach((figure) => {
        figure.dataset.diagramRendering = "";
        setDiagramStatus(figure, "Mermaid 未加载，显示源码", true);
      });
      return;
    }
    initMermaidTheme();
    for (const figure of pending) {
      const source = figure.querySelector(".diagram-source code");
      const canvas = figure.querySelector(".diagram-canvas");
      if (!source || !canvas) continue;
      const id = `code-agent-diagram-${Date.now()}-${diagramSeq++}`;
      try {
        const result = await window.mermaid.render(id, source.textContent || "");
        canvas.innerHTML = typeof result === "string" ? result : (result.svg || "");
        figure.dataset.diagramRendered = "1";
        figure.dataset.diagramRendering = "";
        figure.classList.add("is-rendered");
        setDiagramStatus(figure, "已渲染", false);
      } catch (err) {
        canvas.innerHTML = "";
        figure.dataset.diagramRendered = "1";
        figure.dataset.diagramRendering = "";
        setDiagramStatus(figure, "渲染失败，显示源码", true);
        if (window.console && window.console.warn) {
          window.console.warn("Mermaid render failed", err);
        }
      }
    }
  }

  function mountVueApp() {
  const app = window.Vue.createApp({
    data() {
      return {
        vueReady: window.__CODE_AGENT_VUE_READY__ === true,
        view: pathToView(window.location.pathname),
        loading: false,
        statusText: "就绪",
        shell: {
          sidebarCollapsed: readSidebarCollapsed(),
          theme: readTheme(),
        },
        defaultRepo: "",
        repos: [],
        selectedRepo: "",
        modes: {
          default: "plain",
          allowed: ["plain"],
          labels: {},
        },
        ask: {
          mode: "technical",
          question_type: "outage_log",
          use_cache: true,
          plain: false,
          question: "",
          answer: "",
          raw: "",
        },
        errorText: "",
        traceDir: "",
        traceFiles: [],
        selectedTrace: "",
        traceRows: [],
        traceOpenRounds: {},
        knowledge: {
          mode: "cards",
          cards: [],
          name: "",
          content: "",
          meta: {},
          editing: false,
          treeOpen: {},
          graph: { nodes: [], edges: [] },
          graphRelations: GRAPH_RELATIONS.slice(),
          graphSourceRepo: "",
          graphSearch: "",
          graphGroups: [],
          graphActiveGroups: [],
          graphStatus: "0 节点 · 0 关系",
          graphVisAvailable: true,
          graphShowEdgeLabels: false,
          graphVis: null,
          qaItems: [],
          qa: null,
          curateQuestion: "",
          curateQuestionType: "general",
          qaDraft: {
            title: "",
            name: "",
            tags: "qa, curated",
            answer: "",
          },
        },
      };
    },
    computed: {
      viewTitle() {
        if (this.view === "traces") return "调用复盘";
        if (this.view === "graph") return "知识图谱";
        if (this.view === "knowledge") return "知识工作台";
        return "代码调查";
      },
      viewSubtitle() {
        if (this.view === "traces") return "沿着每轮模型输入、工具调用和最终回答复盘证据链。";
        if (this.view === "graph") return "按模块、标签和沉淀知识关系查看代码知识网络。";
        if (this.view === "knowledge") return "维护模块地图、排查手册和可被问答自动召回的沉淀知识。";
        return "把 crash 堆栈、宕机日志、功能实现和配置实现放进同一个调查台。";
      },
      tracePretty() {
        return this.traceRows.map((row) => JSON.stringify(row, null, 2)).join("\n");
      },
      selectedTraceFile() {
        return this.traceFiles.find((file) => file.file === this.selectedTrace) || {};
      },
      traceHeader() {
        const rows = this.traceRows || [];
        const first = rows[0] || {};
        const file = this.selectedTraceFile;
        return {
          file: file.file || this.selectedTrace || first.request_id || "",
          question: file.question || first.question || "",
          mode: file.mode || first.mode || "",
          backend: file.backend || first.backend || "",
          model: file.model || first.model || "",
          size: file.size || 0,
          eventCount: rows.length,
        };
      },
      traceSummary() {
        return buildTraceSummary(this.traceRows || [], this.traceHeader);
      },
      renderedKnowledge() {
        return renderMarkdown(this.knowledge.content);
      },
      renderedAskAnswer() {
        return renderMarkdown(this.ask.answer, "等待提交问题。");
      },
      knowledgeCardRows() {
        const order = ["index.md", "gameserver", "unit", "enemy", "ecs", "common"];
        const root = { children: [], childMap: new Map() };
        const ensureFolder = (parent, segment, path, depth) => {
          if (!parent.childMap) parent.childMap = new Map();
          if (!parent.childMap.has(segment)) {
            const folder = {
              kind: "folder",
              id: path,
              label: segment,
              depth,
              count: 0,
              children: [],
              childMap: new Map(),
            };
            parent.childMap.set(segment, folder);
            parent.children.push(folder);
          }
          return parent.childMap.get(segment);
        };
        (this.knowledge.cards || []).forEach((card) => {
          const segments = Array.isArray(card.segments) && card.segments.length
            ? card.segments
            : String(card.name || "").split("/").filter(Boolean);
          if (!segments.length) return;
          let parent = root;
          let prefix = "";
          segments.slice(0, -1).forEach((segment, index) => {
            prefix = prefix ? `${prefix}/${segment}` : segment;
            parent = ensureFolder(parent, segment, prefix, index);
          });
          const leaf = segments[segments.length - 1];
          parent.children.push({
            kind: "card",
            id: card.name,
            label: card.title || leaf,
            leaf,
            depth: Math.max(0, segments.length - 1),
            card,
          });
        });
        const rank = (node) => {
          const key = node.kind === "folder" ? node.label : node.leaf;
          const index = order.indexOf(key);
          return index === -1 ? 99 : index;
        };
        const sortTree = (node) => {
          node.children.sort((a, b) => {
            const ar = rank(a);
            const br = rank(b);
            if (ar !== br) return ar - br;
            if (a.kind !== b.kind) return a.kind === "folder" ? -1 : 1;
            return String(a.label || "").localeCompare(String(b.label || ""));
          });
          node.children.forEach((child) => {
            if (child.kind === "folder") {
              sortTree(child);
              child.count = child.children.reduce(
                (total, item) => total + (item.kind === "folder" ? item.count : 1),
                0
              );
            }
          });
        };
        const rows = [];
        const flatten = (children) => {
          children.forEach((node) => {
            if (node.kind === "folder") {
              rows.push(node);
              if (this.isKnowledgeTreeOpen(node.id)) flatten(node.children);
            } else {
              rows.push(node);
            }
          });
        };
        sortTree(root);
        flatten(root.children);
        return rows;
      },
      knowledgeMetaRows() {
        return Object.entries(this.knowledge.meta || {}).map(([key, value]) => ({
          key,
          value,
        }));
      },
      graphStats() {
        const nodes = this.knowledge.graph.nodes || [];
        return {
          concepts: nodes.filter((node) => node.kind === "concept").length,
          tags: nodes.filter((node) => node.kind === "tag").length,
          edges: (this.knowledge.graph.edges || []).length,
        };
      },
      modeOptions() {
        const allowed = Array.isArray(this.modes.allowed) && this.modes.allowed.length
          ? this.modes.allowed
          : ["plain"];
        return allowed.map((mode) => ({
          value: mode,
          label: this.modes.labels && this.modes.labels[mode] ? `${mode} - ${this.modes.labels[mode]}` : mode,
        }));
      },
    },
    mounted() {
      this.syncSidebarClass();
      this.syncThemeClass();
      window.addEventListener("popstate", () => {
        this.view = pathToView(window.location.pathname);
        this.activateView();
      });
      this.loadRepos().then(() => this.activateView());
    },
    updated() {
      this.scheduleKnowledgeDiagramRender(false);
    },
    methods: {
      async apiJson(url, options) {
        const res = await fetch(url, options);
        const text = await res.text();
        let data = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch (_err) {
          data = { raw: text };
        }
        if (!res.ok) {
          throw new Error(data.detail || data.error || text || res.statusText);
        }
        return data;
      },
      async withLoading(label, fn) {
        this.loading = true;
        this.statusText = label;
        this.errorText = "";
        try {
          const result = await fn();
          this.statusText = "完成";
          return result;
        } catch (err) {
          this.statusText = "失败";
          this.errorText = err && err.message ? err.message : String(err || "请求失败");
          return null;
        } finally {
          this.loading = false;
        }
      },
      go(view, path) {
        if (this.view === view && window.location.pathname === path) return;
        history.pushState({}, "", path);
        this.view = view;
        this.activateView();
      },
      syncSidebarClass() {
        const root = document.getElementById("app");
        if (root) root.classList.toggle("sidebar-collapsed", this.shell.sidebarCollapsed);
      },
      syncThemeClass() {
        applyDocumentTheme(this.shell.theme);
      },
      toggleSidebar() {
        this.shell.sidebarCollapsed = !this.shell.sidebarCollapsed;
        saveSidebarCollapsed(this.shell.sidebarCollapsed);
        this.$nextTick(() => this.syncSidebarClass());
      },
      toggleTheme() {
        this.shell.theme = this.shell.theme === "dark" ? "light" : "dark";
        saveTheme(this.shell.theme);
        this.syncThemeClass();
        this.$nextTick(() => {
          this.refreshGraphTheme();
          this.scheduleKnowledgeDiagramRender(true);
        });
      },
      isKnowledgeTreeOpen(id) {
        return this.knowledge.treeOpen[id] !== false;
      },
      toggleKnowledgeTree(id) {
        this.knowledge.treeOpen = {
          ...this.knowledge.treeOpen,
          [id]: !this.isKnowledgeTreeOpen(id),
        };
      },
      shortQuestion(question) {
        return compactText(question || "无问题文本", 96);
      },
      traceFileMeta(file) {
        return [
          file.mode || "mode -",
          file.backend || "backend -",
          file.last_event || "event -",
          file.last_ts || file.mtime || "",
        ].filter(Boolean).join(" · ");
      },
      formatBytes(size) {
        return formatBytesValue(size);
      },
      isTraceRoundOpen(id) {
        return this.traceOpenRounds[id] === true;
      },
      setTraceRoundOpen(id, open) {
        this.traceOpenRounds = { ...this.traceOpenRounds, [id]: open };
      },
      activateView() {
        if (this.view !== "graph") this.destroyKnowledgeGraphVis();
        if (this.view === "traces" && !this.traceFiles.length) this.loadTraces();
        if (this.view === "knowledge" && this.selectedRepo) {
          if (this.knowledge.mode === "graph") this.knowledge.mode = "cards";
          this.loadKnowledge();
        }
        if (this.view === "graph" && this.selectedRepo) this.loadKnowledgeGraph();
      },
      async loadRepos() {
        await this.withLoading("加载仓库", async () => {
          const data = await this.apiJson("/repos");
          this.defaultRepo = data.default || "";
          this.repos = data.repos || [];
          this.modes = {
            default: data.modes && data.modes.default ? data.modes.default : "plain",
            allowed: data.modes && Array.isArray(data.modes.allowed) && data.modes.allowed.length ? data.modes.allowed : ["plain"],
            labels: data.modes && data.modes.labels ? data.modes.labels : {},
          };
          this.syncModeSelection();
          const current = this.repos.find((repo) => repo.name === this.defaultRepo) || this.repos[0];
          if (current && !this.selectedRepo) this.selectedRepo = current.name;
        });
      },
      syncModeSelection() {
        const allowed = Array.isArray(this.modes.allowed) && this.modes.allowed.length
          ? this.modes.allowed
          : ["plain"];
        const fallback = allowed.includes(this.modes.default) ? this.modes.default : allowed[0];
        if (!allowed.includes(this.ask.mode)) this.ask.mode = fallback;
      },
      preferredKnowledgeQaMode() {
        const allowed = Array.isArray(this.modes.allowed) && this.modes.allowed.length
          ? this.modes.allowed
          : ["plain"];
        if (allowed.includes("technical")) return "technical";
        if (allowed.includes(this.ask.mode)) return this.ask.mode;
        return allowed.includes(this.modes.default) ? this.modes.default : allowed[0];
      },
      fillExample() {
        this.ask.question = EXAMPLE_LOG;
        this.ask.question_type = "outage_log";
      },
      clearAskOutput() {
        this.ask.answer = "";
        this.ask.raw = "";
      },
      async submitAsk() {
        await this.withLoading("提交提问", async () => {
          const body = {
            question: this.ask.question,
            mode: this.ask.mode,
            repo: this.selectedRepo,
            question_type: this.ask.question_type,
            use_cache: this.ask.use_cache,
          };
          const data = await this.apiJson("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          this.ask.answer = data.answer || "";
          this.ask.raw = JSON.stringify(data, null, 2);
        });
      },
      async submitDiagnose() {
        await this.withLoading("提交诊断", async () => {
          const body = {
            repo: this.selectedRepo,
            backtrace: "",
            log: this.ask.question,
            plain: this.ask.plain,
          };
          const data = await this.apiJson("/diagnose", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          this.ask.answer = data.answer || data.plain || "";
          this.ask.raw = JSON.stringify(data, null, 2);
        });
      },
      async loadTraces() {
        await this.withLoading("加载 trace", async () => {
          const data = await this.apiJson("/admin/llm-traces/api");
          this.traceDir = data.trace_dir || "";
          this.traceFiles = data.files || [];
          if (!this.selectedTrace && this.traceFiles.length) {
            await this.loadTrace(this.traceFiles[0].file);
          }
        });
      },
      async loadTrace(file) {
        await this.withLoading("读取 trace", async () => {
          const data = await this.apiJson("/admin/llm-traces/api/" + encodeURIComponent(file));
          this.selectedTrace = file;
          this.traceRows = data.rows || [];
          const roundIds = this.traceRows
            .filter((row) => row.event === "llm_request" || row.event === "sdk_request")
            .map((row, index) => row.round || index + 1);
          if (!roundIds.length && this.traceRows.length) roundIds.push(1);
          this.traceOpenRounds = Object.fromEntries(
            roundIds.map((id, index) => [id, index === 0])
          );
        });
      },
      async loadKnowledge() {
        if (!this.selectedRepo) return;
        await this.withLoading("加载知识库", async () => {
          const data = await this.apiJson("/knowledge/api?repo=" + encodeURIComponent(this.selectedRepo));
          this.knowledge.cards = data.cards || [];
          const selectedExists = this.knowledge.cards.some((card) => card.name === this.knowledge.name);
          if (this.knowledge.cards.length && (!this.knowledge.name || !selectedExists)) {
            const first = this.knowledge.cards.find((card) => card.name === "index.md") || this.knowledge.cards[0];
            await this.loadCard(first.name);
          }
          if (this.knowledge.mode === "qa") await this.loadKnowledgeQa();
        });
      },
      async loadCard(name) {
        await this.withLoading("读取卡片", async () => {
          const url = "/knowledge/api/" + encodeURIComponent(this.selectedRepo) + "/" + encodePath(name);
          const data = await this.apiJson(url);
          this.knowledge.name = data.name || name;
          this.knowledge.content = data.content || "";
          this.knowledge.meta = data.meta || {};
          this.knowledge.editing = false;
          this.knowledge.mode = "cards";
          this.scheduleKnowledgeDiagramRender(true);
        });
      },
      newCard() {
        this.knowledge.name = "unit/new-module.md";
        this.knowledge.meta = {};
        this.knowledge.content = "---\ntype: Code Module\ntitle: 新模块\ntags: \n---\n\n# 新模块\n\n## 框架\n\n## 关键流程\n\n```mermaid\nflowchart TD\n    A[\"入口\"] --> B[\"处理\"]\n    B --> C[\"结果\"]\n```\n\n## 常见问题\n";
        this.knowledge.mode = "cards";
        this.knowledge.editing = true;
      },
      showCardPreview() {
        this.knowledge.editing = false;
        this.scheduleKnowledgeDiagramRender(true);
      },
      scheduleKnowledgeDiagramRender(force) {
        if (this.view !== "knowledge" || this.knowledge.mode !== "cards" || this.knowledge.editing) return;
        if (this._diagramFrame) window.cancelAnimationFrame(this._diagramFrame);
        this._diagramFrame = window.requestAnimationFrame(() => {
          this._diagramFrame = null;
          renderKnowledgeDiagrams(Boolean(force)).catch(() => {});
        });
      },
      async saveCard() {
        await this.withLoading("保存卡片", async () => {
          const data = await this.apiJson("/knowledge/api", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repo: this.selectedRepo,
              name: this.knowledge.name,
              content: this.knowledge.content,
            }),
          });
          this.knowledge.name = data.name || this.knowledge.name;
          await this.loadKnowledge();
          this.knowledge.editing = false;
        });
      },
      async setKnowledgeMode(mode) {
        this.knowledge.mode = mode;
        if (mode === "qa") await this.loadKnowledgeQa();
      },
      graphGroupForNode(node) {
        if (node.kind === "tag") return "tag";
        if (node.kind === "symbol") return "symbol";
        if (node.kind === "log") return "log";
        if (node.kind === "assert") return "assert";
        if (node.kind === "question_type") return "question_type";
        if (node.kind === "resource") return "resource";
        const text = [node.type, node.title, node.description, ...(node.tags || [])].join(" ").toLowerCase();
        if (text.includes("qa") || text.includes("curated") || text.includes("问答")) return "qa";
        if (text.includes("playbook") || text.includes("手册") || text.includes("排查")) return "playbook";
        if (text.includes("config") || text.includes("配置") || text.includes("table")) return "config";
        if (text.includes("code") || text.includes("代码")) return "code";
        if (text.includes("module") || text.includes("模块")) return "module";
        return "other";
      },
      graphGroupMeta(group) {
        return GRAPH_GROUPS[group] || GRAPH_GROUPS.other;
      },
      graphRelationMeta(relation) {
        const remote = this.knowledge.graphRelations.find((item) => item.id === relation);
        const local = GRAPH_RELATIONS.find((item) => item.id === relation);
        if (remote || local) return Object.assign({}, local || {}, remote || {});
        return {
          id: relation || "unknown",
          label: relation || "未知关系",
          short_label: relation || "unknown",
          description: "当前 relation 尚未登记含义。",
        };
      },
      getGraphBg() {
        return cssVar("--graph-bg", "#0d1424");
      },
      graphColor(name, fallback) {
        return cssVar(name, fallback);
      },
      buildKnowledgeGraphVisData() {
        const rawNodes = this.knowledge.graph.nodes || [];
        const rawEdges = this.knowledge.graph.edges || [];
        const degree = {};
        rawNodes.forEach((node) => {
          degree[node.id] = 0;
        });
        rawEdges.forEach((edge) => {
          if (degree[edge.source] !== undefined) degree[edge.source] += 1;
          if (degree[edge.target] !== undefined) degree[edge.target] += 1;
        });
        const groups = [];
        const seenGroups = new Set();
        const nodes = rawNodes.map((node) => {
          const group = this.graphGroupForNode(node);
          if (!seenGroups.has(group)) {
            seenGroups.add(group);
            groups.push(group);
          }
          const label = node.kind === "tag" ? String(node.title || node.id).replace(/^tag:/, "") : (node.title || node.id);
          return {
            id: node.id,
            label,
            title: node.description || node.type || node.id,
            group,
            kind: node.kind,
            degree: degree[node.id] || 0,
            value: Math.max(10, Math.min(36, 10 + (degree[node.id] || 0) * 3)),
          };
        });
        const edges = rawEdges.map((edge, index) => {
          const relation = this.graphRelationMeta(edge.relation);
          return {
            id: edge.id || `${edge.source}->${edge.target}-${index}`,
            from: edge.source,
            to: edge.target,
            relation: relation.id,
            label: relation.short_label || relation.id,
            title: relation.description,
          };
        });
        const order = Object.keys(GRAPH_GROUPS);
        groups.sort((a, b) => order.indexOf(a) - order.indexOf(b));
        return { nodes, edges, groups };
      },
      prepareKnowledgeGraphVis() {
        const data = this.buildKnowledgeGraphVisData();
        this.knowledge.graphGroups = data.groups.map((group) => ({
          id: group,
          label: this.graphGroupMeta(group).label,
          color: this.graphGroupMeta(group).color,
        }));
        this.knowledge.graphActiveGroups = data.groups.slice();
        this.knowledge.graphStatus = `${data.nodes.length} 节点 · ${data.edges.length} 关系`;
        this.knowledge.graphShowEdgeLabels = false;
      },
      destroyKnowledgeGraphVis() {
        const current = this.knowledge.graphVis;
        if (!current) return;
        if (current.hoverFrame) window.cancelAnimationFrame(current.hoverFrame);
        if (current.tooltipMove) document.removeEventListener("mousemove", current.tooltipMove);
        if (current.network) current.network.destroy();
        this.knowledge.graphVis = null;
      },
      nodeFullColor(node) {
        const meta = this.graphGroupMeta(node.group);
        return {
          color: {
            background: meta.color,
            border: meta.color,
            highlight: { background: meta.color, border: meta.color },
            hover: { background: meta.color, border: meta.color },
          },
          shadow: { enabled: false },
          opacity: 0.48,
          font: { color: this.graphColor("--graph-label-muted", "rgba(230,237,243,0.5)"), size: 11 },
        };
      },
      nodeDim(node) {
        const meta = this.graphGroupMeta(node.group);
        return {
          color: {
            background: meta.color,
            border: meta.color,
            highlight: { background: meta.color, border: meta.color },
            hover: { background: meta.color, border: meta.color },
          },
          shadow: { enabled: false },
          opacity: 0.06,
          font: { color: "rgba(0,0,0,0)" },
        };
      },
      nodeNeighbor(node) {
        const meta = this.graphGroupMeta(node.group);
        return {
          color: {
            background: meta.color,
            border: meta.color,
            highlight: { background: meta.color, border: meta.color },
            hover: { background: meta.color, border: meta.color },
          },
          shadow: { enabled: false },
          opacity: 0.85,
          font: { color: this.graphColor("--graph-label", "rgba(230,237,243,0.8)"), size: 11 },
        };
      },
      nodeHovered(node) {
        const meta = this.graphGroupMeta(node.group);
        return {
          color: {
            background: meta.color,
            border: "#ffffff",
            highlight: { background: meta.color, border: "#ffffff" },
            hover: { background: meta.color, border: "#ffffff" },
          },
          borderWidth: 2,
          shadow: { enabled: true, color: meta.glow.replace(/[\d.]+\)$/, "0.75)"), size: 18, x: 0, y: 0 },
          opacity: 1,
          font: { color: this.graphColor("--graph-label-strong", "#ffffff"), size: 13 },
        };
      },
      edgeStyle(active) {
        const bg = this.getGraphBg();
        if (active === null) {
          return {
            color: {
              color: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              highlight: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              hover: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              inherit: false,
            },
            width: 1,
            font: { size: this.knowledge.graphShowEdgeLabels ? 10 : 0, color: this.graphColor("--graph-edge-label", "#8b949e"), strokeWidth: 2, strokeColor: bg },
          };
        }
        if (active) {
          return {
            color: {
              color: this.graphColor("--graph-edge-active", "rgba(190,220,255,0.9)"),
              highlight: this.graphColor("--graph-edge-active", "rgba(190,220,255,0.9)"),
              hover: this.graphColor("--graph-edge-active", "rgba(190,220,255,0.9)"),
              inherit: false,
            },
            width: 2.5,
            font: { size: 11, color: this.graphColor("--graph-edge-label", "#a8c4e0"), strokeWidth: 2, strokeColor: bg },
          };
        }
        return {
          color: {
            color: this.graphColor("--graph-edge-dim", "rgba(148,163,184,0.04)"),
            highlight: this.graphColor("--graph-edge-dim", "rgba(148,163,184,0.04)"),
            hover: this.graphColor("--graph-edge-dim", "rgba(148,163,184,0.04)"),
            inherit: false,
          },
          width: 0.5,
          font: { size: 0 },
        };
      },
      refreshGraphTheme() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        const bg = this.getGraphBg();
        graph.network.setOptions({
          nodes: { font: { strokeColor: bg } },
          edges: { font: { strokeColor: bg } },
        });
        if (graph.pinnedSet) this.applyKnowledgePinnedHighlight(Array.from(graph.pinnedSet));
        else this.applyKnowledgeNodeStyles();
      },
      applyKnowledgeNodeStyles() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        graph.hoveredId = null;
        const nodeUpdates = [];
        const edgeUpdates = [];
        graph.nodeData.forEach((node) => {
          const current = graph.nodes.get(node.id);
          if (!current || current.hidden) return;
          nodeUpdates.push(Object.assign({ id: node.id }, this.nodeFullColor(node)));
        });
        graph.edgeData.forEach((edge) => {
          edgeUpdates.push(Object.assign({ id: edge.id }, this.edgeStyle(null)));
        });
        if (nodeUpdates.length) graph.nodes.update(nodeUpdates);
        if (edgeUpdates.length) graph.edges.update(edgeUpdates);
      },
      applyKnowledgeHoverHighlight(hoveredId) {
        const graph = this.knowledge.graphVis;
        if (!graph || graph.isDragging || graph.hoveredId === hoveredId) return;
        if (graph.hoverFrame) window.cancelAnimationFrame(graph.hoverFrame);
        graph.hoverFrame = window.requestAnimationFrame(() => {
          graph.hoverFrame = null;
          this.applyKnowledgeHoverHighlightNow(hoveredId);
        });
      },
      applyKnowledgeHoverHighlightNow(hoveredId) {
        const graph = this.knowledge.graphVis;
        if (!graph || graph.isDragging) return;
        graph.hoveredId = hoveredId;
        const neighbors = new Set([hoveredId]);
        graph.edgeData.forEach((edge) => {
          if (edge.from === hoveredId) neighbors.add(edge.to);
          if (edge.to === hoveredId) neighbors.add(edge.from);
        });
        const nodeUpdates = [];
        const edgeUpdates = [];
        graph.nodeData.forEach((node) => {
          const current = graph.nodes.get(node.id);
          if (!current || current.hidden) return;
          if (node.id === hoveredId) {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeHovered(node)));
          } else if (neighbors.has(node.id)) {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeNeighbor(node)));
          } else {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeDim(node)));
          }
        });
        graph.edgeData.forEach((edge) => {
          const connected = edge.from === hoveredId || edge.to === hoveredId;
          edgeUpdates.push(Object.assign({ id: edge.id }, this.edgeStyle(connected)));
        });
        if (nodeUpdates.length) graph.nodes.update(nodeUpdates);
        if (edgeUpdates.length) graph.edges.update(edgeUpdates);
      },
      applyKnowledgePinnedHighlight(idList) {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        graph.hoveredId = null;
        graph.pinnedSet = idList && idList.length ? new Set(idList) : null;
        if (!graph.pinnedSet) {
          this.applyKnowledgeNodeStyles();
          return;
        }
        const neighbors = new Set(graph.pinnedSet);
        graph.edgeData.forEach((edge) => {
          if (graph.pinnedSet.has(edge.from)) neighbors.add(edge.to);
          if (graph.pinnedSet.has(edge.to)) neighbors.add(edge.from);
        });
        const nodeUpdates = [];
        const edgeUpdates = [];
        graph.nodeData.forEach((node) => {
          const current = graph.nodes.get(node.id);
          if (!current || current.hidden) return;
          if (graph.pinnedSet.has(node.id)) {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeHovered(node)));
          } else if (neighbors.has(node.id)) {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeNeighbor(node)));
          } else {
            nodeUpdates.push(Object.assign({ id: node.id }, this.nodeDim(node)));
          }
        });
        graph.edgeData.forEach((edge) => {
          const connected = graph.pinnedSet.has(edge.from) || graph.pinnedSet.has(edge.to);
          edgeUpdates.push(Object.assign({ id: edge.id }, this.edgeStyle(connected)));
        });
        if (nodeUpdates.length) graph.nodes.update(nodeUpdates);
        if (edgeUpdates.length) graph.edges.update(edgeUpdates);
      },
      applyKnowledgeGraphFilter() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        const active = new Set(this.knowledge.graphActiveGroups);
        const hidden = new Set(graph.nodeData.filter((node) => !active.has(node.group)).map((node) => node.id));
        graph.hiddenNodeIds = hidden;
        graph.nodes.update(graph.nodeData.map((node) => ({ id: node.id, hidden: hidden.has(node.id) })));
        graph.edges.update(graph.edgeData.map((edge) => ({ id: edge.id, hidden: hidden.has(edge.from) || hidden.has(edge.to) })));
        this.updateKnowledgeGraphStatus();
      },
      updateKnowledgeGraphStatus() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        const active = new Set(this.knowledge.graphActiveGroups);
        const hidden = graph.hiddenNodeIds || new Set();
        const visibleNodes = graph.nodeData.filter((node) => active.has(node.group)).length;
        const visibleEdges = graph.edgeData.filter((edge) => !hidden.has(edge.from) && !hidden.has(edge.to)).length;
        this.knowledge.graphStatus = `${visibleNodes} 节点 · ${visibleEdges} 关系`;
      },
      initKnowledgeGraphVis() {
        this.destroyKnowledgeGraphVis();
        const container = this.$refs.graphCanvas;
        if (!container || !window.vis || !window.vis.Network) {
          this.knowledge.graphVisAvailable = false;
          return;
        }
        const data = this.buildKnowledgeGraphVisData();
        if (!data.nodes.length) return;
        this.knowledge.graphVisAvailable = true;
        const nodes = new window.vis.DataSet(data.nodes);
        const edges = new window.vis.DataSet(data.edges);
        const options = {
          layout: { randomSeed: 7 },
          nodes: {
            shape: "dot",
            scaling: { min: 10, max: 36 },
            borderWidth: 0,
            borderWidthSelected: 3,
            font: {
              color: this.graphColor("--graph-label", "#e6edf3"),
              size: 11,
              face: cssVar("--font", "\"Plus Jakarta Sans\", \"PingFang SC\", \"Microsoft YaHei\", -apple-system, sans-serif"),
              vadjust: -2,
              strokeWidth: 3,
              strokeColor: this.getGraphBg(),
            },
            shadow: { enabled: false },
          },
          edges: {
            arrows: { to: { enabled: true, scaleFactor: 0.4 } },
            color: {
              color: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              highlight: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              hover: this.graphColor("--graph-edge", "rgba(148,163,184,0.22)"),
              inherit: false,
            },
            font: { size: 0 },
            smooth: { type: "continuous", roundness: 0.2 },
            width: 0.8,
            selectionWidth: 0,
            hoverWidth: 0,
          },
          interaction: {
            hover: true,
            hoverConnectedEdges: false,
            tooltipDelay: 100,
            navigationButtons: false,
            keyboard: { enabled: true, bindToWindow: false },
            multiselect: false,
            selectEdges: false,
            hideEdgesOnDrag: true,
            hideEdgesOnZoom: true,
            dragNodes: true,
            dragView: true,
            zoomView: true,
          },
          physics: {
            enabled: true,
            solver: "forceAtlas2Based",
            forceAtlas2Based: {
              gravitationalConstant: -40,
              centralGravity: 0.01,
              springLength: 200,
              springConstant: 0.03,
              damping: 0.55,
              avoidOverlap: 0.6,
            },
            stabilization: { iterations: 500, updateInterval: 20 },
          },
        };
        const network = new window.vis.Network(container, { nodes, edges }, options);
        const tooltipMove = (event) => {
          const tooltip = this.$refs.graphTooltip;
          if (!tooltip || tooltip.style.display !== "block") return;
          tooltip.style.left = `${event.clientX + 16}px`;
          tooltip.style.top = `${event.clientY - 10}px`;
        };
        document.addEventListener("mousemove", tooltipMove);
        this.knowledge.graphVis = {
          network,
          nodes,
          edges,
          nodeData: data.nodes,
          edgeData: data.edges,
          pinnedSet: null,
          hiddenNodeIds: new Set(),
          hoveredId: null,
          hoverFrame: null,
          isDragging: false,
          tooltipMove,
        };
        this.applyKnowledgeNodeStyles();
        this.applyKnowledgeGraphFilter();

        network.on("hoverNode", (params) => {
          const graph = this.knowledge.graphVis;
          if (graph && graph.isDragging) return;
          this.applyKnowledgeHoverHighlight(params.node);
          const node = nodes.get(params.node);
          const tooltip = this.$refs.graphTooltip;
          if (!node || !tooltip) return;
          const meta = this.graphGroupMeta(node.group);
          tooltip.innerHTML = `<div class="graph-tooltip-name" style="color:${meta.color}">${escapeHtml(node.label || node.id)}</div><div class="graph-tooltip-group">${escapeHtml(meta.label)}</div><div class="graph-tooltip-deg">连接数 ${node.degree || 0}</div>`;
          tooltip.style.display = "block";
        });
        network.on("blurNode", () => {
          const tooltip = this.$refs.graphTooltip;
          if (tooltip) tooltip.style.display = "none";
          const graph = this.knowledge.graphVis;
          if (graph && graph.hoverFrame) {
            window.cancelAnimationFrame(graph.hoverFrame);
            graph.hoverFrame = null;
          }
          if (graph && graph.pinnedSet) this.applyKnowledgePinnedHighlight(Array.from(graph.pinnedSet));
          else this.applyKnowledgeNodeStyles();
        });
        network.on("hoverEdge", (params) => {
          const edge = edges.get(params.edge);
          const tooltip = this.$refs.graphTooltip;
          if (!edge || !tooltip) return;
          const relation = this.graphRelationMeta(edge.relation);
          tooltip.innerHTML = `<div class="graph-tooltip-name">${escapeHtml(relation.label || relation.id)}</div><div class="graph-tooltip-edge">${escapeHtml(relation.description || edge.title || "")}</div><div class="graph-tooltip-deg">${escapeHtml(relation.id || edge.label || "")}</div>`;
          tooltip.style.display = "block";
        });
        network.on("blurEdge", () => {
          const tooltip = this.$refs.graphTooltip;
          if (tooltip) tooltip.style.display = "none";
        });
        network.on("dragStart", () => {
          const graph = this.knowledge.graphVis;
          if (!graph) return;
          graph.isDragging = true;
          const tooltip = this.$refs.graphTooltip;
          if (tooltip) tooltip.style.display = "none";
        });
        network.on("dragEnd", () => {
          const graph = this.knowledge.graphVis;
          if (!graph) return;
          graph.isDragging = false;
        });
        network.on("doubleClick", (params) => {
          const id = params.nodes && params.nodes[0];
          const node = id ? nodes.get(id) : null;
          if (node && node.kind === "concept") {
            this.go("knowledge", "/knowledge");
            this.loadCard(node.id);
          }
        });
        network.on("stabilizationIterationsDone", () => {
          network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
          network.setOptions({ physics: { enabled: false } });
          this.updateKnowledgeGraphStatus();
        });
      },
      toggleGraphGroup(group) {
        const active = new Set(this.knowledge.graphActiveGroups);
        if (active.has(group)) active.delete(group);
        else active.add(group);
        this.knowledge.graphActiveGroups = Array.from(active);
        this.applyKnowledgeGraphFilter();
      },
      toggleGraphEdgeLabels() {
        this.knowledge.graphShowEdgeLabels = !this.knowledge.graphShowEdgeLabels;
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        graph.network.setOptions({
          edges: {
            font: {
              size: this.knowledge.graphShowEdgeLabels ? 10 : 0,
              color: this.graphColor("--graph-edge-label", "#8b949e"),
              strokeWidth: 2,
              strokeColor: this.getGraphBg(),
            },
          },
        });
        if (!this.knowledge.graphShowEdgeLabels) this.applyKnowledgeNodeStyles();
      },
      rerunKnowledgeGraphPhysics() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        graph.network.setOptions({
          physics: {
            enabled: true,
            forceAtlas2Based: { gravitationalConstant: -40, springLength: 200, springConstant: 0.03, damping: 0.55, avoidOverlap: 0.6 },
            stabilization: { iterations: 300 },
          },
        });
      },
      fitKnowledgeGraph() {
        const graph = this.knowledge.graphVis;
        if (graph) graph.network.fit({ animation: { duration: 400 } });
      },
      searchKnowledgeGraph() {
        const graph = this.knowledge.graphVis;
        if (!graph) return;
        const query = this.knowledge.graphSearch.trim().toLowerCase();
        if (!query) {
          graph.network.fit();
          graph.network.unselectAll();
          this.applyKnowledgePinnedHighlight(null);
          return;
        }
        const matched = graph.nodeData
          .filter((node) => [node.id, node.label, node.title, node.group].join(" ").toLowerCase().includes(query))
          .map((node) => node.id);
        if (!matched.length) return;
        graph.network.selectNodes(matched);
        this.applyKnowledgePinnedHighlight(matched);
        graph.network.fit({ nodes: matched, animation: { duration: 500 } });
      },
      clearGraphSearch() {
        this.knowledge.graphSearch = "";
        this.searchKnowledgeGraph();
      },
      async loadKnowledgeGraph() {
        await this.withLoading("加载图谱", async () => {
          let repo = this.selectedRepo;
          let data = await this.apiJson("/knowledge/api/graph?repo=" + encodeURIComponent(repo));
          if (!(data.nodes || []).length && this.defaultRepo && this.defaultRepo !== repo) {
            const fallback = await this.apiJson("/knowledge/api/graph?repo=" + encodeURIComponent(this.defaultRepo));
            if ((fallback.nodes || []).length) {
              repo = this.defaultRepo;
              this.selectedRepo = this.defaultRepo;
              data = fallback;
              const cards = await this.apiJson("/knowledge/api?repo=" + encodeURIComponent(this.defaultRepo));
              this.knowledge.cards = cards.cards || [];
            }
          }
          this.knowledge.graph = {
            nodes: data.nodes || [],
            edges: data.edges || [],
          };
          this.knowledge.graphRelations = data.relations || GRAPH_RELATIONS.slice();
          this.knowledge.graphSourceRepo = repo;
          this.prepareKnowledgeGraphVis();
          this.$nextTick(() => this.initKnowledgeGraphVis());
        });
      },
      async loadKnowledgeQa() {
        await this.withLoading("加载问答", async () => {
          const data = await this.apiJson("/knowledge/api/qa?repo=" + encodeURIComponent(this.selectedRepo));
          this.knowledge.qaItems = data.items || [];
          if (!this.knowledge.qa && this.knowledge.qaItems.length) this.selectQa(this.knowledge.qaItems[0]);
        });
      },
      selectQa(item) {
        this.knowledge.qa = item;
        const title = item.question.length > 28 ? item.question.slice(0, 28) : item.question;
        const slug = "qa-" + String(item.id || Date.now()) + ".md";
        this.knowledge.qaDraft = {
          title,
          name: slug,
          tags: "qa, curated",
          answer: item.answer || "",
        };
      },
      async askKnowledgeQa() {
        await this.withLoading("后台追问", async () => {
          const data = await this.apiJson("/knowledge/api/qa/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repo: this.selectedRepo,
              question: this.knowledge.curateQuestion,
              question_type: this.knowledge.curateQuestionType,
              mode: this.preferredKnowledgeQaMode(),
            }),
          });
          this.selectQa({
            id: "draft-" + Date.now(),
            question: data.question,
            answer: data.answer,
            refs: [],
            created_at: "draft",
          });
        });
      },
      async precipitateQa() {
        if (!this.knowledge.qa) return;
        await this.withLoading("沉淀知识", async () => {
          const data = await this.apiJson("/knowledge/api/precipitate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repo: this.selectedRepo,
              name: this.knowledge.qaDraft.name,
              title: this.knowledge.qaDraft.title,
              question: this.knowledge.qa.question,
              answer: this.knowledge.qaDraft.answer,
              tags: this.knowledge.qaDraft.tags,
              refs: this.knowledge.qa.refs || [],
            }),
          });
          await this.loadKnowledge();
          await this.loadCard(data.name);
        });
      },
    },
  });

  app.mount("#app");
  }

  ensureVue()
    .then(() => {
      loadVisNetwork();
      mountVueApp();
    })
    .catch(() => {
      renderTraceFallback();
    });
})();
