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
          cards: [],
          name: "",
          content: "",
          editing: false,
        },
      };
    },
    computed: {
      viewTitle() {
        if (this.view === "traces") return "模型调用分析";
        if (this.view === "knowledge") return "知识库维护";
        return "提问测试";
      },
      viewSubtitle() {
        if (this.view === "traces") return "复盘每轮模型输入、工具调用和最终回答，快速发现上下文不足的问题。";
        if (this.view === "knowledge") return "维护模块框架、关键配置和排查细节，问答时自动注入相关上下文。";
        return "按 crash 堆栈、宕机日志、功能实现、配置实现选择对应答疑路径。";
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
          this.repos = data.repos || [];
          const current = this.repos.find((repo) => repo.current) || this.repos[0];
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
        });
      },
      async loadCard(name) {
        await this.withLoading("读取卡片", async () => {
          const url = "/knowledge/api/" + encodeURIComponent(this.selectedRepo) + "/" + encodeURIComponent(name);
          const data = await this.apiJson(url);
          this.knowledge.name = data.name || name;
          this.knowledge.content = data.content || "";
          this.knowledge.editing = false;
        });
      },
      newCard() {
        this.knowledge.name = "new-module.md";
        this.knowledge.content = "---\ntitle: 新模块\ntags: \n---\n\n# 新模块\n\n## 框架\n\n## 关键流程\n\n## 常见问题\n";
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
    },
  });

  app.mount("#app");
})();
