(function () {
  if (!window.Vue) {
    document.body.classList.add("vue-missing");
    return;
  }

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

  function pathToView(pathname) {
    if (pathname.indexOf("/admin/llm-traces") === 0) return "traces";
    if (pathname.indexOf("/knowledge/graph") === 0) return "graph";
    if (pathname.indexOf("/knowledge") === 0) return "knowledge";
    return "ask";
  }

  function eventText(row) {
    return row.answer || row.content || row.text || row.output || row.error || "";
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderInline(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
      .replace(/\[([^\]]+)\]\(([^):\s][^)\s]*)\)/g, '<span class="internal-link">$1</span>');
  }

  function stripFrontMatter(markdown) {
    const text = String(markdown || "");
    if (!text.startsWith("---\n")) return text;
    const end = text.indexOf("\n---", 4);
    if (end < 0) return text;
    return text.slice(end + 4).replace(/^\s+/, "");
  }

  function renderMarkdown(markdown) {
    const lines = stripFrontMatter(markdown).split(/\r?\n/);
    const html = [];
    let inCode = false;
    let code = [];
    let list = [];
    let paragraph = [];

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
      html.push("<pre><code>" + escapeHtml(code.join("\n")) + "</code></pre>");
      code = [];
    }

    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        if (inCode) {
          flushCode();
          inCode = false;
        } else {
          flushParagraph();
          flushList();
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        code.push(line);
        continue;
      }
      if (!line.trim()) {
        flushParagraph();
        flushList();
        continue;
      }
      const heading = /^(#{1,4})\s+(.+)$/.exec(line);
      if (heading) {
        flushParagraph();
        flushList();
        const level = heading[1].length;
        html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        continue;
      }
      const bullet = /^\s*[-*]\s+(.+)$/.exec(line);
      if (bullet) {
        flushParagraph();
        list.push(bullet[1]);
        continue;
      }
      paragraph.push(line);
    }
    if (inCode) flushCode();
    flushParagraph();
    flushList();
    return html.join("\n") || '<p class="empty">选择或新建一个知识卡片。</p>';
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

  applyDocumentTheme(readTheme());

  const app = Vue.createApp({
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
        ask: {
          mode: "technical",
          question_type: "outage_log",
          use_cache: true,
          plain: false,
          question: "",
          answer: "",
          raw: "",
        },
        traceDir: "",
        traceFiles: [],
        selectedTrace: "",
        traceRows: [],
        knowledge: {
          mode: "cards",
          cards: [],
          name: "",
          content: "",
          meta: {},
          editing: false,
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
      traceSummary() {
        const rows = this.traceRows || [];
        const llmRequests = rows.filter((row) => row.event === "llm_request");
        const llmResponses = rows.filter((row) => row.event === "llm_response");
        const toolRows = rows.filter((row) => row.event === "tool_call" || row.tool || row.name);
        const rounds = Math.max(llmRequests.length, llmResponses.length);
        const roundDetails = [];

        for (let i = 0; i < Math.max(1, rounds); i += 1) {
          const start = llmRequests[i] ? rows.indexOf(llmRequests[i]) : 0;
          const end = llmRequests[i + 1] ? rows.indexOf(llmRequests[i + 1]) : rows.length;
          const slice = rows.slice(start, end);
          const tools = slice
            .map((row) => row.tool || row.name || row.function || "")
            .filter(Boolean);
          const response = llmResponses[i] || slice.find((row) => row.event === "final_answer") || {};
          roundDetails.push({
            id: i + 1,
            tools: Array.from(new Set(tools)),
            answer: eventText(response),
          });
        }

        const findings = [];
        if (!rows.length) {
          findings.push("请选择一个 trace 文件。");
        } else {
          if (!llmRequests.length) findings.push("没有记录 llm_request，无法复盘提示词输入。");
          if (!toolRows.length) findings.push("没有工具调用记录，复杂代码问题可能缺少代码检索证据。");
          if (!rows.some((row) => row.event === "request_end" || row.event === "final_answer")) {
            findings.push("没有看到 request_end/final_answer，确认请求是否中途失败。");
          }
          if (llmResponses.length > 4) findings.push("LLM 轮次偏多，建议检查工具结果是否足够聚焦。");
        }

        return {
          rounds,
          tools: toolRows.length,
          findings,
          roundDetails,
        };
      },
      renderedKnowledge() {
        return renderMarkdown(this.knowledge.content);
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
        try {
          const result = await fn();
          this.statusText = "完成";
          return result;
        } catch (err) {
          this.statusText = "失败";
          throw err;
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
        this.$nextTick(() => this.refreshGraphTheme());
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
          const current = this.repos.find((repo) => repo.name === this.defaultRepo) || this.repos[0];
          if (current && !this.selectedRepo) this.selectedRepo = current.name;
        });
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
        });
      },
      async loadKnowledge() {
        if (!this.selectedRepo) return;
        await this.withLoading("加载知识库", async () => {
          const data = await this.apiJson("/knowledge/api?repo=" + encodeURIComponent(this.selectedRepo));
          this.knowledge.cards = data.cards || [];
          if (this.knowledge.cards.length && !this.knowledge.name) {
            await this.loadCard(this.knowledge.cards[0].name);
          }
          if (this.knowledge.mode === "qa") await this.loadKnowledgeQa();
        });
      },
      async loadCard(name) {
        await this.withLoading("读取卡片", async () => {
          const url = "/knowledge/api/" + encodeURIComponent(this.selectedRepo) + "/" + encodeURIComponent(name);
          const data = await this.apiJson(url);
          this.knowledge.name = data.name || name;
          this.knowledge.content = data.content || "";
          this.knowledge.meta = data.meta || {};
          this.knowledge.editing = false;
          this.knowledge.mode = "cards";
        });
      },
      newCard() {
        this.knowledge.name = "new-module.md";
        this.knowledge.meta = {};
        this.knowledge.content = "---\ntype: Code Module\ntitle: 新模块\ntags: \n---\n\n# 新模块\n\n## 框架\n\n## 关键流程\n\n## 常见问题\n";
        this.knowledge.mode = "cards";
        this.knowledge.editing = true;
      },
      async saveCard() {
        await this.withLoading("保存卡片", async () => {
          await this.apiJson("/knowledge/api", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              repo: this.selectedRepo,
              name: this.knowledge.name,
              content: this.knowledge.content,
            }),
          });
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
              mode: "technical",
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
})();
