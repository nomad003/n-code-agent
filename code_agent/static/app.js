(function () {
  if (!window.Vue) {
    document.body.classList.add("vue-missing");
    return;
  }

  const EXAMPLE_LOG = `15:04:47:429[61285][0000006133] [Error] GetEnemySkillConfigX(skillconfig.cpp:489) enemy conf skill:[0 921948522 monster_livinglaser_lightstream] not find
15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:80) [COMBAT] unit: [type=enemy uid=1153743939307804815 tid=302250101 role=0 user= name= sid=0 scene=0-0 map=0], caster:302250101 skill:[921948522 monster_livinglaser_lightstream] not find in conf
15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:81) Check cond: <false> failed
15:04:47:429[61285][0000006133] [Error] Log_FlushOnExit(LogInit.cpp:347) *************** Error Exit ***************`;

  function pathToView(pathname) {
    if (pathname.indexOf("/admin/llm-traces") === 0) return "traces";
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

  const app = Vue.createApp({
    data() {
      return {
        vueReady: window.__CODE_AGENT_VUE_READY__ === true,
        view: pathToView(window.location.pathname),
        loading: false,
        statusText: "就绪",
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
          graphSourceRepo: "",
          graphPositions: {},
          graphSearch: "",
          graphRelation: "all",
          graphSelectedId: "",
          graphDrag: null,
          graphPan: null,
          graphView: { x: 0, y: 0, scale: 1 },
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
        if (this.view === "knowledge") return "知识工作台";
        return "代码调查";
      },
      viewSubtitle() {
        if (this.view === "traces") return "沿着每轮模型输入、工具调用和最终回答复盘证据链。";
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
      graphNodes() {
        const nodes = this.knowledge.graph.nodes || [];
        if (!nodes.length) return [];
        const query = this.knowledge.graphSearch.trim().toLowerCase();
        const linked = new Set();
        for (const edge of this.filteredGraphEdgesRaw) {
          linked.add(edge.source);
          linked.add(edge.target);
        }
        return nodes.map((node) => {
          const pos = this.knowledge.graphPositions[node.id] || { x: 480, y: 280 };
          const text = [node.id, node.title, node.type, node.description, ...(node.tags || [])].join(" ").toLowerCase();
          const matches = !query || text.includes(query);
          const active = node.id === this.knowledge.graphSelectedId || matches && query;
          return {
            ...node,
            x: Math.round(pos.x),
            y: Math.round(pos.y),
            radius: node.kind === "concept" ? 18 + Math.min((node.tags || []).length, 8) : 11,
            active,
            dim: Boolean(query && !matches && !linked.has(node.id)),
          };
        });
      },
      filteredGraphEdgesRaw() {
        const relation = this.knowledge.graphRelation;
        return (this.knowledge.graph.edges || []).filter((edge) => relation === "all" || edge.relation === relation);
      },
      graphEdges() {
        const byId = new Map(this.graphNodes.map((node) => [node.id, node]));
        const query = this.knowledge.graphSearch.trim().toLowerCase();
        return this.filteredGraphEdgesRaw
          .map((edge, index) => {
            const source = byId.get(edge.source);
            const target = byId.get(edge.target);
            if (!source || !target) return null;
            return {
              id: `${edge.source}->${edge.target}-${index}`,
              relation: edge.relation || "links_to",
              x1: source.x,
              y1: source.y,
              x2: target.x,
              y2: target.y,
              dim: Boolean(query && source.dim && target.dim),
            };
          })
          .filter(Boolean);
      },
      graphStats() {
        const nodes = this.knowledge.graph.nodes || [];
        return {
          concepts: nodes.filter((node) => node.kind === "concept").length,
          tags: nodes.filter((node) => node.kind === "tag").length,
          edges: (this.knowledge.graph.edges || []).length,
        };
      },
      graphConcepts() {
        const query = this.knowledge.graphSearch.trim().toLowerCase();
        return (this.knowledge.graph.nodes || [])
          .filter((node) => node.kind === "concept")
          .filter((node) => {
            if (!query) return true;
            return [node.id, node.title, node.type, node.description, ...(node.tags || [])].join(" ").toLowerCase().includes(query);
          });
      },
      selectedGraphNode() {
        return (this.knowledge.graph.nodes || []).find((node) => node.id === this.knowledge.graphSelectedId) || null;
      },
    },
    mounted() {
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
      activateView() {
        if (this.view === "traces" && !this.traceFiles.length) this.loadTraces();
        if (this.view === "knowledge" && this.selectedRepo) this.loadKnowledge();
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
          if (this.knowledge.mode === "graph") await this.loadKnowledgeGraph();
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
        if (mode === "graph") await this.loadKnowledgeGraph();
        if (mode === "qa") await this.loadKnowledgeQa();
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
          this.knowledge.graphSourceRepo = repo;
          this.layoutGraph();
        });
      },
      layoutGraph() {
        const nodes = this.knowledge.graph.nodes || [];
        const edges = this.knowledge.graph.edges || [];
        const positions = {};
        const width = 960;
        const height = 560;
        const centerX = width / 2;
        const centerY = height / 2;
        const concepts = nodes.filter((node) => node.kind === "concept");
        const tags = nodes.filter((node) => node.kind === "tag");
        concepts.forEach((node, index) => {
          const angle = (Math.PI * 2 * index) / Math.max(1, concepts.length);
          positions[node.id] = {
            x: centerX + Math.cos(angle) * 180,
            y: centerY + Math.sin(angle) * 150,
          };
        });
        tags.forEach((node, index) => {
          const angle = (Math.PI * 2 * index) / Math.max(1, tags.length);
          positions[node.id] = {
            x: centerX + Math.cos(angle) * 320,
            y: centerY + Math.sin(angle) * 230,
          };
        });
        for (let tick = 0; tick < 140; tick += 1) {
          const force = {};
          nodes.forEach((node) => {
            force[node.id] = { x: (centerX - positions[node.id].x) * 0.002, y: (centerY - positions[node.id].y) * 0.002 };
          });
          for (let i = 0; i < nodes.length; i += 1) {
            for (let j = i + 1; j < nodes.length; j += 1) {
              const a = nodes[i];
              const b = nodes[j];
              const pa = positions[a.id];
              const pb = positions[b.id];
              const dx = pa.x - pb.x;
              const dy = pa.y - pb.y;
              const dist2 = Math.max(dx * dx + dy * dy, 80);
              const strength = (a.kind === "tag" || b.kind === "tag") ? 900 : 1500;
              const push = strength / dist2;
              force[a.id].x += dx * push;
              force[a.id].y += dy * push;
              force[b.id].x -= dx * push;
              force[b.id].y -= dy * push;
            }
          }
          for (const edge of edges) {
            const source = positions[edge.source];
            const target = positions[edge.target];
            if (!source || !target) continue;
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const desired = edge.relation === "links_to" ? 145 : 105;
            const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const pull = (dist - desired) * 0.006;
            const fx = (dx / dist) * pull;
            const fy = (dy / dist) * pull;
            force[edge.source].x += fx;
            force[edge.source].y += fy;
            force[edge.target].x -= fx;
            force[edge.target].y -= fy;
          }
          nodes.forEach((node) => {
            const pos = positions[node.id];
            pos.x = Math.max(35, Math.min(width - 35, pos.x + force[node.id].x));
            pos.y = Math.max(35, Math.min(height - 35, pos.y + force[node.id].y));
          });
        }
        this.knowledge.graphPositions = positions;
        if (!this.knowledge.graphSelectedId && concepts.length) this.knowledge.graphSelectedId = concepts[0].id;
      },
      selectGraphNode(node) {
        this.knowledge.graphSelectedId = node.id;
      },
      startNodeDrag(node, event) {
        this.knowledge.graphSelectedId = node.id;
        this.knowledge.graphDrag = {
          id: node.id,
          startX: event.clientX,
          startY: event.clientY,
          origin: { ...(this.knowledge.graphPositions[node.id] || { x: node.x, y: node.y }) },
        };
      },
      panGraphStart(event) {
        this.knowledge.graphPan = {
          startX: event.clientX,
          startY: event.clientY,
          origin: { ...this.knowledge.graphView },
        };
      },
      moveGraphPointer(event) {
        if (this.knowledge.graphDrag) {
          const drag = this.knowledge.graphDrag;
          const scale = this.knowledge.graphView.scale || 1;
          this.knowledge.graphPositions[drag.id] = {
            x: drag.origin.x + (event.clientX - drag.startX) / scale,
            y: drag.origin.y + (event.clientY - drag.startY) / scale,
          };
        } else if (this.knowledge.graphPan) {
          const pan = this.knowledge.graphPan;
          this.knowledge.graphView.x = pan.origin.x + event.clientX - pan.startX;
          this.knowledge.graphView.y = pan.origin.y + event.clientY - pan.startY;
        }
      },
      endGraphPointer() {
        this.knowledge.graphDrag = null;
        this.knowledge.graphPan = null;
      },
      zoomGraph(event) {
        const next = this.knowledge.graphView.scale * (event.deltaY > 0 ? 0.9 : 1.1);
        this.knowledge.graphView.scale = Math.max(0.55, Math.min(2.4, next));
      },
      resetGraphView() {
        this.knowledge.graphView = { x: 0, y: 0, scale: 1 };
        this.layoutGraph();
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
