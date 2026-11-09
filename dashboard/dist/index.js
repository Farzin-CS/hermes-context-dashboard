/* Context Lens — Hermes web dashboard tab.
 * Plain IIFE, no build step. React + UI primitives come from the dashboard SDK.
 */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  var React = SDK.React;
  var h = React.createElement;
  var hooks = SDK.hooks;
  var useState = hooks.useState;
  var useEffect = hooks.useEffect;
  var useMemo = hooks.useMemo;
  var Card = SDK.components.Card;
  var CardHeader = SDK.components.CardHeader;
  var CardTitle = SDK.components.CardTitle;
  var CardContent = SDK.components.CardContent;
  var Badge = SDK.components.Badge;
  var Button = SDK.components.Button;
  var Separator = SDK.components.Separator;

  var API = "/api/plugins/context-lens";

  var I18N = {
    en: {
      title: "Context Lens",
      kicker: "CONTEXT INSIGHT",
      subtitle: "What your agent is carrying, where it came from, and how it changes.",
      overview: "Overview",
      session: "Session",
      refresh: "Refresh",
      loading: "Loading…",
      error: "Could not load context data",
      empty: "No session data in this window.",
      sessions: "Sessions",
      billed: "Billed tokens",
      cost: "Estimated cost",
      cacheHit: "Cache hit",
      turns: "Turns",
      toolCalls: "Tool calls",
      active: "Active time",
      activeTime: "active",
      in: "in",
      out: "out",
      priced: "priced",
      cached: "cached",
      thinking: "thinking",
      usage: "Daily usage",
      composition: "Current composition",
      compositionHint: "Estimated share of the retained prompt",
      skills: "Skills loaded",
      tools: "Tools",
      commands: "Commands",
      files: "File activity",
      recentSessions: "Recent sessions",
      context: "Context",
      contextWindow: "Context window",
      headroom: "Headroom",
      tokens: "tokens",
      estimated: "estimated",
      trend: "Context trend",
      trendHint: "Estimated prompt size at each assistant step",
      events: "Context events",
      fleet: "Fleet",
      parent: "Parent",
      children: "Children",
      noChildren: "No child sessions",
      back: "Back to overview",
      model: "Model",
      source: "Source",
      started: "Started",
      updated: "Updated",
      ended: "ended",
      running: "active",
      apiCalls: "API calls",
      messages: "Messages",
      exit: "exit",
      noFiles: "No file activity",
      noCommands: "No commands",
      noEvents: "No context events",
      all: "All",
      days7: "7 days",
      days30: "30 days",
      activity: "Activity",
      activityHint: "8 weeks · daily tokens",
      clickHint: "Open a session for the full breakdown.",
      lang: "فا",
      dir: "ltr"
    },
    fa: {
      title: "لنز زمینه",
      kicker: "بینش زمینه",
      subtitle: "اینکه ایجنت چه چیزی را حمل می\u200cکند، از کجا آمده و چگونه تغییر می\u200cکند.",
      overview: "نمای کلی",
      session: "نشست",
      refresh: "تازه\u200cسازی",
      loading: "در حال بارگذاری…",
      error: "بارگذاری داده\u200cهای زمینه ممکن نشد",
      empty: "در این بازه داده\u200cای نیست.",
      sessions: "نشست\u200cها",
      billed: "توکن\u200cهای محاسبه\u200cشده",
      cost: "هزینه تخمینی",
      cacheHit: "نرخ کش",
      turns: "نوبت\u200cها",
      toolCalls: "فراخوانی ابزار",
      active: "زمان فعال",
      activeTime: "فعال",
      in: "ورودی",
      out: "خروجی",
      priced: "قیمت\u200cگذاری\u200cشده",
      cached: "کش\u200cشده",
      thinking: "تفکر",
      usage: "مصرف روزانه",
      composition: "ترکیب فعلی",
      compositionHint: "سهم تخمینی از پرامپت نگه\u200cداشته\u200cشده",
      skills: "مهارت\u200cهای بارگذاری\u200cشده",
      tools: "ابزارها",
      commands: "دستورها",
      files: "فعالیت فایل",
      recentSessions: "نشست\u200cهای اخیر",
      context: "زمینه",
      contextWindow: "پنجره زمینه",
      headroom: "فضای باقی\u200cمانده",
      tokens: "توکن",
      estimated: "تخمینی",
      trend: "روند زمینه",
      trendHint: "اندازه تخمینی پرامپت در هر گام دستیار",
      events: "رویدادهای زمینه",
      fleet: "گروه",
      parent: "والد",
      children: "فرزندان",
      noChildren: "نشست فرزندی نیست",
      back: "بازگشت به نمای کلی",
      model: "مدل",
      source: "منبع",
      started: "شروع",
      updated: "آخرین فعالیت",
      ended: "پایان\u200cیافته",
      running: "فعال",
      apiCalls: "فراخوانی API",
      messages: "پیام\u200cها",
      exit: "کد خروج",
      noFiles: "فعالیت فایلی نیست",
      noCommands: "دستوری نیست",
      noEvents: "رویداد زمینه\u200cای نیست",
      all: "همه",
      days7: "۷ روز",
      days30: "۳۰ روز",
      activity: "فعالیت",
      activityHint: "۸ هفته · توکن روزانه",
      clickHint: "برای جزئیات کامل یک نشست را باز کنید.",
      lang: "EN",
      dir: "rtl"
    }
  };

  function t(lang, key) {
    var table = I18N[lang] || I18N.en;
    return table[key] !== undefined ? table[key] : (I18N.en[key] !== undefined ? I18N.en[key] : key);
  }

  var CAT_LABELS = {
    en: {
      system: "System prompt", tools: "Tool definitions", skills: "Skills index",
      user: "User messages", injected: "Injected context", assistant: "Assistant replies",
      thinking: "Reasoning", tool_calls: "Tool calls", tool_results: "Tool results"
    },
    fa: {
      system: "پرامپت سیستم", tools: "تعریف ابزارها", skills: "فهرست مهارت\u200cها",
      user: "پیام\u200cهای کاربر", injected: "زمینه تزریقی", assistant: "پاسخ\u200cهای دستیار",
      thinking: "استدلال", tool_calls: "فراخوانی ابزار", tool_results: "نتایج ابزار"
    }
  };

  function catLabel(lang, id, fallback) {
    var table = CAT_LABELS[lang] || CAT_LABELS.en;
    return table[id] || fallback || id;
  }

  function fmtInt(n) {
    try { return Math.round(Number(n) || 0).toLocaleString(); } catch (e) { return String(n || 0); }
  }
  function fmtTokens(n) {
    n = Number(n) || 0;
    if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (n >= 1e4) return (n / 1e3).toFixed(1) + "k";
    return fmtInt(n);
  }
  function fmtCost(n) {
    n = Number(n) || 0;
    if (n && n < 0.01) return "$" + n.toFixed(4);
    if (n < 1) return "$" + n.toFixed(3);
    return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  function fmtPct(n) { return (Number(n) || 0).toFixed(1) + "%"; }
  function fmtDuration(s, lang) {
    s = Math.max(0, Math.round(Number(s) || 0));
    var fa = lang === "fa";
    if (s >= 86400) return Math.floor(s / 86400) + (fa ? " روز " : "d ") + Math.floor((s % 86400) / 3600) + (fa ? " ساعت" : "h");
    if (s >= 3600) return Math.floor(s / 3600) + (fa ? " ساعت " : "h ") + Math.floor((s % 3600) / 60) + (fa ? " دقیقه" : "m");
    if (s >= 60) return Math.floor(s / 60) + (fa ? " دقیقه" : "m");
    return s + (fa ? " ثانیه" : "s");
  }
  function timeAgo(ts) {
    if (!ts) return "";
    var delta = Math.max(0, Math.floor(Date.now() / 1000 - Number(ts)));
    if (delta < 60) return "just now";
    if (delta < 3600) return Math.floor(delta / 60) + "m ago";
    if (delta < 86400) return Math.floor(delta / 3600) + "h ago";
    return Math.floor(delta / 86400) + "d ago";
  }
  function dayLabel(key, lang) {
    try {
      var d = new Date(key + "T00:00:00");
      return d.toLocaleDateString(lang === "fa" ? "fa-IR" : undefined, { month: "short", day: "numeric" });
    } catch (e) { return key; }
  }
  function truncate(text, n) {
    text = String(text || "").replace(/\s+/g, " ").trim();
    return text.length > n ? text.slice(0, n - 1) + "…" : text;
  }

  function useJson(url) {
    var s = useState({ data: null, error: null, loading: true });
    var state = s[0], setState = s[1];
    var reload = useState(0);
    var tick = reload[0], bump = reload[1];
    useEffect(function () {
      var alive = true;
      setState(function (prev) { return { data: prev.data, error: null, loading: true }; });
      SDK.fetchJSON(url).then(function (data) {
        if (alive) setState({ data: data, error: null, loading: false });
      }).catch(function (err) {
        if (alive) setState({ data: null, error: err, loading: false });
      });
      return function () { alive = false; };
    }, [url, tick]);
    return [state, function () { bump(function (n) { return n + 1; }); }];
  }

  function Kpi(props) {
    return h("div", { className: "lens-kpi" },
      h("div", { className: "lens-kpi-label" }, props.label),
      h("div", { className: "lens-kpi-value" }, props.value),
      props.hint ? h("div", { className: "lens-kpi-hint" }, props.hint) : null
    );
  }

  function Section(props) {
    return h("section", { className: "lens-section " + (props.className || "") },
      h("div", { className: "lens-section-head" },
        h("div", null,
          h("h2", { className: "lens-section-title" }, props.title),
          props.hint ? h("p", { className: "lens-section-hint" }, props.hint) : null
        ),
        props.right || null
      ),
      props.children
    );
  }

  function DailyChart(props) {
    var data = props.data || [];
    var max = 1;
    data.forEach(function (d) { max = Math.max(max, Number(d.tokens) || 0); });
    if (!data.length) return h("div", { className: "lens-empty" }, props.empty);
    var labelEvery = Math.max(1, Math.ceil(data.length / (props.lang === "fa" ? 6 : 8)));
    return h("div", { className: "lens-bars", role: "img", "aria-label": props.title },
      data.map(function (d, i) {
        var tokens = Number(d.tokens) || 0;
        var pct = Math.max(tokens > 0 ? 2 : 0, Math.round(tokens / max * 100));
        return h("div", { className: "lens-bar-slot", key: d.date,
          title: dayLabel(d.date, props.lang) + ": " + fmtTokens(tokens) + " " + props.tokensLabel + " · " + fmtCost(d.cost_usd) },
          h("div", { className: "lens-bar-track" },
            h("div", { className: "lens-bar-fill", style: { height: pct + "%" } })
          ),
          (i % labelEvery === 0)
            ? h("span", { className: "lens-bar-label" }, dayLabel(d.date, props.lang))
            : h("span", { className: "lens-bar-label" }, "")
        );
      })
    );
  }

  function Heatmap(props) {
    var data = props.data || [];
    var max = 1;
    data.forEach(function (d) { max = Math.max(max, Number(d.tokens) || 0); });
    var weeks = [];
    for (var i = 0; i < data.length; i += 7) weeks.push(data.slice(i, i + 7));
    return h("div", { className: "lens-heatmap", role: "img", "aria-label": props.title },
      weeks.map(function (week, wi) {
        return h("div", { className: "lens-heat-col", key: wi },
          week.map(function (d) {
            var tokens = Number(d.tokens) || 0;
            var intensity = tokens > 0 ? 0.18 + 0.82 * Math.min(1, tokens / max) : 0;
            return h("div", { key: d.date, className: "lens-heat-cell",
              style: { opacity: intensity || 0.06 },
              title: dayLabel(d.date, props.lang) + ": " + fmtTokens(tokens) + " " + props.tokensLabel + " · " + fmtInt(d.sessions) + " " + props.sessionsLabel });
          })
        );
      })
    );
  }

  function Donut(props) {
    var parts = props.parts || [];
    var total = 0;
    parts.forEach(function (p) { total += Number(p.tokens) || 0; });
    var size = 168, r = 62, cx = size / 2, cy = size / 2;
    var circ = 2 * Math.PI * r;
    var offset = 0;
    var circles = parts.map(function (p, i) {
      var value = Number(p.tokens) || 0;
      var len = total > 0 ? value / total * circ : 0;
      var el = h("circle", {
        key: p.id || i, cx: cx, cy: cy, r: r, fill: "none",
        stroke: p.color, strokeWidth: 18,
        strokeDasharray: len + " " + Math.max(0, circ - len),
        strokeDashoffset: -offset,
        transform: "rotate(-90 " + cx + " " + cy + ")"
      });
      offset += len;
      return el;
    });
    return h("div", { className: "lens-donut-wrap" },
      h("svg", { className: "lens-donut", width: size, height: size, viewBox: "0 0 " + size + " " + size },
        h("circle", { cx: cx, cy: cy, r: r, fill: "none", stroke: "var(--color-border)", strokeWidth: 18, opacity: 0.45 }),
        circles,
        h("text", { x: cx, y: cy - 2, textAnchor: "middle", className: "lens-donut-value" }, fmtTokens(total)),
        h("text", { x: cx, y: cy + 18, textAnchor: "middle", className: "lens-donut-caption" }, props.caption || "")
      ),
      h("div", { className: "lens-legend" },
        parts.map(function (p) {
          var value = Number(p.tokens) || 0;
          return h("div", { className: "lens-legend-row", key: p.id || p.label },
            h("span", { className: "lens-dot", style: { background: p.color } }),
            h("span", { className: "lens-legend-label" }, p.label),
            h("span", { className: "lens-legend-value" }, fmtPct(total ? value / total * 100 : 0))
          );
        })
      )
    );
  }

  function TrendChart(props) {
    var points = props.points || [];
    if (points.length < 2) return h("div", { className: "lens-empty" }, props.empty);
    var w = 720, hgt = 190, pad = 26;
    var values = points.map(function (p) { return Number(p.tokens) || 0; });
    var max = Math.max.apply(null, values) || 1;
    var step = (w - pad * 2) / Math.max(1, points.length - 1);
    var coords = values.map(function (v, i) {
      var x = pad + i * step;
      var y = pad + (1 - v / max) * (hgt - pad * 2);
      return [x, y];
    });
    var line = coords.map(function (c, i) { return (i === 0 ? "M" : "L") + c[0].toFixed(1) + " " + c[1].toFixed(1); }).join(" ");
    var area = line + " L" + coords[coords.length - 1][0].toFixed(1) + " " + (hgt - pad) + " L" + coords[0][0].toFixed(1) + " " + (hgt - pad) + " Z";
    return h("div", { className: "lens-trend" },
      h("svg", { viewBox: "0 0 " + w + " " + hgt, className: "lens-trend-svg", preserveAspectRatio: "none" },
        [0.25, 0.5, 0.75].map(function (f) {
          return h("line", { key: f, x1: pad, x2: w - pad,
            y1: pad + f * (hgt - pad * 2), y2: pad + f * (hgt - pad * 2),
            stroke: "var(--color-border)", strokeWidth: 1, opacity: 0.5 });
        }),
        h("path", { d: area, fill: "var(--color-primary)", opacity: 0.12 }),
        h("path", { d: line, fill: "none", stroke: "var(--color-primary)", strokeWidth: 2.4, strokeLinejoin: "round" }),
        h("text", { x: pad, y: 16, className: "lens-axis-label" }, fmtTokens(max)),
        h("text", { x: pad, y: hgt - 6, className: "lens-axis-label" }, "1"),
        h("text", { x: w - pad, y: hgt - 6, textAnchor: "end", className: "lens-axis-label" }, String(points.length))
      )
    );
  }

  function BarList(props) {
    var items = props.items || [];
    var max = 1;
    items.forEach(function (i) { max = Math.max(max, Number(i.value) || 0); });
    if (!items.length) return h("div", { className: "lens-empty" }, props.empty);
    return h("div", { className: "lens-list" },
      items.slice(0, props.limit || 10).map(function (item) {
        var value = Number(item.value) || 0;
        return h("div", { className: "lens-list-row", key: item.key },
          h("span", { className: "lens-list-name", title: item.title || item.key }, item.label),
          h("span", { className: "lens-list-track" },
            h("span", { className: "lens-list-fill", style: { width: Math.max(2, value / max * 100) + "%" } })
          ),
          h("span", { className: "lens-list-value" }, item.display || fmtInt(value))
        );
      })
    );
  }

  function SessionRow(props) {
    var s = props.session;
    var ctx = s.context || {};
    return h("button", { className: "lens-session-row", onClick: function () { props.onOpen(s.id); } },
      h("span", { className: "lens-session-main" },
        h("span", { className: "lens-session-title" }, s.title || s.id),
        h("span", { className: "lens-session-meta" },
          s.source + " · " + s.model + " · " + timeAgo(s.last_activity_at)
        )
      ),
      h("span", { className: "lens-session-ctx" },
        h("span", { className: "lens-session-ctx-bar" },
          h("span", { style: { width: Math.min(100, Number(ctx.pct) || 0) + "%" } })
        ),
        h("span", { className: "lens-session-ctx-label" }, fmtTokens(ctx.used))
      ),
      h("span", { className: "lens-session-num" }, fmtTokens(s.tokens)),
      h("span", { className: "lens-session-num" }, fmtCost(s.cost_usd))
    );
  }

  function Overview(props) {
    var lang = props.lang;
    var data = props.data;
    var totals = data.totals || {};
    var rangeLabel = props.days === 7 ? t(lang, "days7") : props.days === 30 ? t(lang, "days30") : t(lang, "all");
    var composition = data.composition || [];
    var categories = { system: "var(--lens-c1)", tools: "var(--lens-c2)", skills: "var(--lens-c3)",
      user: "var(--lens-c4)", injected: "var(--lens-c5)", assistant: "var(--lens-c6)",
      thinking: "var(--lens-c7)", tool_calls: "var(--lens-c8)", tool_results: "var(--lens-c9)" };
    var parts = composition.map(function (c) {
      return { id: c.id, label: catLabel(lang, c.id, c.label), tokens: c.tokens, color: categories[c.id] || "var(--lens-c1)" };
    });
    return h("div", { className: "lens-stack" },
      h("div", { className: "lens-kpis" },
        h(Kpi, { label: t(lang, "sessions"), value: fmtInt(totals.sessions) }),
        h(Kpi, { label: t(lang, "billed"), value: fmtTokens(totals.billed_tokens),
          hint: t(lang, "in") + " " + fmtTokens(totals.input_tokens) + " · " + t(lang, "out") + " " + fmtTokens(totals.output_tokens) }),
        h(Kpi, { label: t(lang, "cost"), value: fmtCost(totals.cost_usd),
          hint: totals.cost_sessions + "/" + totals.sessions + " " + t(lang, "priced") }),
        h(Kpi, { label: t(lang, "cacheHit"), value: fmtPct(totals.cache_hit_pct),
          hint: fmtTokens(totals.cache_read_tokens) + " " + t(lang, "cached") }),
        h(Kpi, { label: t(lang, "turns"), value: fmtInt(totals.turns) }),
        h(Kpi, { label: t(lang, "toolCalls"), value: fmtInt(totals.tool_calls),
          hint: fmtDuration(totals.active_seconds, lang) + " " + t(lang, "activeTime") })
      ),
      h(Section, { title: t(lang, "usage"), hint: rangeLabel },
        h(DailyChart, { data: data.daily, title: t(lang, "usage"), lang: lang,
          empty: t(lang, "empty"), tokensLabel: t(lang, "tokens") })
      ),
      h("div", { className: "lens-grid-2" },
        h(Section, { title: t(lang, "composition"), hint: t(lang, "compositionHint") + " · " + t(lang, "estimated") },
          h(Donut, { parts: parts, caption: t(lang, "tokens") })
        ),
        h(Section, { title: t(lang, "activity"), hint: t(lang, "activityHint") },
          h(Heatmap, { data: data.heatmap, title: t(lang, "usage"), lang: lang,
            tokensLabel: t(lang, "tokens"), sessionsLabel: t(lang, "sessions") })
        )
      ),
      h("div", { className: "lens-grid-3" },
        h(Section, { title: t(lang, "skills") },
          h(BarList, { items: (data.skills || []).map(function (s) {
            return { key: s.name, label: s.name, value: s.count };
          }), empty: t(lang, "empty"), limit: 8 })
        ),
        h(Section, { title: t(lang, "tools") },
          h(BarList, { items: (data.tools || []).map(function (s) {
            return { key: s.name, label: s.name, value: s.count,
              display: fmtInt(s.count) + (s.errors ? " · " + s.errors + "✕" : "") };
          }), empty: t(lang, "empty"), limit: 8 })
        ),
        h(Section, { title: t(lang, "commands") },
          h(BarList, { items: (data.commands || []).map(function (s) {
            return { key: s.program, label: s.program, value: s.count };
          }), empty: t(lang, "empty"), limit: 8 })
        )
      ),
      h(Section, { title: t(lang, "recentSessions"), hint: t(lang, "clickHint") },
        h("div", { className: "lens-session-table" },
          (data.sessions || []).slice(0, 40).map(function (s) {
            return h(SessionRow, { key: s.id, session: s, onOpen: props.onOpen });
          })
        )
      )
    );
  }

  function StatCard(props) {
    return h("div", { className: "lens-stat" },
      h("div", { className: "lens-stat-label" }, props.label),
      h("div", { className: "lens-stat-value" }, props.value),
      props.sub ? h("div", { className: "lens-stat-sub" }, props.sub) : null
    );
  }

  function SessionView(props) {
    var lang = props.lang;
    var d = props.data;
    var s = d.session || {};
    var stats = d.stats || {};
    var context = d.context || {};
    var composition = d.composition || [];
    var total = 0;
    composition.forEach(function (c) { total += Number(c.tokens) || 0; });
    var pct = Math.min(100, Number(context.pct) || 0);
    var fleet = d.fleet || {};
    return h("div", { className: "lens-stack" },
      h("div", { className: "lens-session-head" },
        h("button", { className: "lens-back", onClick: props.onBack },
          (t(lang, "dir") === "rtl" ? "→ " : "← ") + t(lang, "back")),
        h("div", { className: "lens-session-head-main" },
          h("h2", { className: "lens-session-head-title" }, s.title || s.id),
          h("div", { className: "lens-session-head-meta" },
            h(Badge, { variant: "secondary" }, s.source),
            h("span", null, s.model),
            h("span", null, s.ended ? t(lang, "ended") : t(lang, "running")),
            h("span", null, s.id)
          )
        )
      ),
      h("div", { className: "lens-stats" },
        h(StatCard, { label: t(lang, "context"), value: fmtTokens(context.used),
          sub: context.max ? fmtPct(pct) + " · " + fmtTokens(context.max) : t(lang, "estimated") }),
        h(StatCard, { label: t(lang, "billed"), value: fmtTokens((stats.input_tokens || 0) + (stats.output_tokens || 0) + (stats.cache_read_tokens || 0)),
          sub: t(lang, "in") + " " + fmtTokens(stats.input_tokens) + " · " + t(lang, "out") + " " + fmtTokens(stats.output_tokens) }),
        h(StatCard, { label: t(lang, "cost"), value: fmtCost(stats.cost_usd),
          sub: fmtTokens(stats.reasoning_tokens) + " " + t(lang, "thinking") }),
        h(StatCard, { label: t(lang, "cacheHit"), value: fmtPct(stats.cache_hit_pct),
          sub: fmtTokens(stats.cache_read_tokens) + " " + t(lang, "cached") }),
        h(StatCard, { label: t(lang, "turns"), value: fmtInt(stats.turns),
          sub: fmtInt(stats.messages) + " " + t(lang, "messages").toLowerCase() }),
        h(StatCard, { label: t(lang, "toolCalls"), value: fmtInt(stats.tool_calls),
          sub: fmtInt(stats.api_calls) + " " + t(lang, "apiCalls").toLowerCase() })
      ),
      h(Section, { title: t(lang, "contextWindow"),
          hint: fmtTokens(context.used) + " / " + (context.max ? fmtTokens(context.max) : "?") + " · " + context.source },
        h("div", { className: "lens-gauge" },
          h("div", { className: "lens-gauge-fill", style: { width: pct + "%" } })
        ),
        h("div", { className: "lens-gauge-legend" },
          h("span", null, fmtPct(pct)),
          h("span", null, t(lang, "headroom") + " " + fmtTokens(context.headroom))
        )
      ),
      h("div", { className: "lens-grid-2" },
        h(Section, { title: t(lang, "composition"), hint: t(lang, "compositionHint") },
          h("div", { className: "lens-stack-bar" },
            composition.map(function (c) {
              var width = total ? (Number(c.tokens) || 0) / total * 100 : 0;
              return h("span", { key: c.id, className: "lens-stack-seg",
                style: { width: Math.max(0.5, width) + "%", background: "var(--lens-" + c.id + ", var(--lens-c1))" },
                title: catLabel(lang, c.id, c.label) + ": " + fmtTokens(c.tokens) });
            })
          ),
          h("div", { className: "lens-comp-list" },
            composition.slice().sort(function (a, b) { return b.tokens - a.tokens; }).map(function (c) {
              var width = total ? (Number(c.tokens) || 0) / total * 100 : 0;
              return h("div", { className: "lens-comp-row", key: c.id },
                h("span", { className: "lens-dot", style: { background: "var(--lens-" + c.id + ", var(--lens-c1))" } }),
                h("span", { className: "lens-comp-label" }, catLabel(lang, c.id, c.label)),
                h("span", { className: "lens-comp-pct" }, fmtPct(width)),
                h("span", { className: "lens-comp-tokens" }, fmtTokens(c.tokens))
              );
            })
          )
        ),
        h(Section, { title: t(lang, "trend"), hint: t(lang, "trendHint") + " · " + t(lang, "estimated") },
          h(TrendChart, { points: d.trend, empty: t(lang, "empty") })
        )
      ),
      h("div", { className: "lens-grid-3" },
        h(Section, { title: t(lang, "files") },
          (d.files || []).length ? h("div", { className: "lens-rows" },
            d.files.slice(0, 10).map(function (f) {
              return h("div", { className: "lens-row", key: f.path, title: f.path },
                h("span", { className: "lens-row-name" }, f.path),
                h("span", { className: "lens-row-meta" },
                  (f.read ? "r" + f.read : "") + (f.write ? " w" + f.write : "") + (f.edit ? " e" + f.edit : ""))
              );
            })
          ) : h("div", { className: "lens-empty" }, t(lang, "noFiles"))
        ),
        h(Section, { title: t(lang, "commands") },
          (d.commands || []).length ? h("div", { className: "lens-rows" },
            d.commands.slice(-10).reverse().map(function (c, i) {
              var failed = c.exit_code !== null && c.exit_code !== undefined && c.exit_code !== 0;
              return h("div", { className: "lens-row", key: i, title: c.command },
                h("span", { className: "lens-row-name lens-mono" }, truncate(c.command || c.program, 54)),
                failed ? h("span", { className: "lens-err" }, t(lang, "exit") + " " + c.exit_code) : null
              );
            })
          ) : h("div", { className: "lens-empty" }, t(lang, "noCommands"))
        ),
        h(Section, { title: t(lang, "fleet") },
          h("div", { className: "lens-fleet" },
            fleet.parent ? h("div", { className: "lens-fleet-item" },
              h("span", { className: "lens-fleet-kind" }, t(lang, "parent")),
              h("span", { className: "lens-fleet-title" }, fleet.parent.title || fleet.parent.id)
            ) : null,
            (fleet.children || []).length ? (fleet.children || []).map(function (c) {
              return h("button", { key: c.id, className: "lens-fleet-item lens-fleet-button",
                onClick: function () { props.onOpen(c.id); } },
                h("span", { className: "lens-fleet-kind" }, t(lang, "children")),
                h("span", { className: "lens-fleet-title" }, c.title || c.id),
                h("span", { className: "lens-fleet-meta" }, fmtTokens(c.tokens) + " · " + fmtPct(c.context_pct))
              );
            }) : (fleet.parent ? null : h("div", { className: "lens-empty" }, t(lang, "noChildren")))
          )
        )
      ),
      h(Section, { title: t(lang, "events") },
        (d.events || []).length ? h("div", { className: "lens-timeline" },
          d.events.slice(-14).map(function (e, i) {
            return h("div", { className: "lens-timeline-row", key: i },
              h("span", { className: "lens-timeline-dot" }),
              h("span", { className: "lens-timeline-label" }, e.label),
              h("span", { className: "lens-timeline-detail" }, e.detail || ""),
              h("span", { className: "lens-timeline-time" }, e.timestamp ? new Date(e.timestamp * 1000).toLocaleString() : "")
            );
          })
        ) : h("div", { className: "lens-empty" }, t(lang, "noEvents"))
      )
    );
  }

  function App() {
    var langState = useState(function () {
      try { return localStorage.getItem("context-lens.lang") || "en"; } catch (e) { return "en"; }
    });
    var lang = langState[0], setLang = langState[1];
    var rangeState = useState(30);
    var days = rangeState[0], setDays = rangeState[1];
    var viewState = useState({ view: "overview", id: null });
    var view = viewState[0], setView = viewState[1];

    var overviewUrl = API + "/overview?days=" + days;
    var overviewReq = useJson(overviewUrl);
    var overview = overviewReq[0], refreshOverview = overviewReq[1];

    var sessionUrl = view.view === "session" && view.id ? API + "/session/" + encodeURIComponent(view.id) : null;
    var sessionReq = useJson(sessionUrl || API + "/health");
    var sessionState = sessionReq[0], refreshSession = sessionReq[1];

    useEffect(function () {
      try { localStorage.setItem("context-lens.lang", lang); } catch (e) { /* ignore */ }
    }, [lang]);

    var dir = t(lang, "dir");
    var loading = overview.loading && !overview.data;
    var error = overview.error;

    function openSession(id) {
      setView({ view: "session", id: id });
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    function back() { setView({ view: "overview", id: null }); }

    return h("div", { className: "lens-root", dir: dir, lang: lang },
      h("div", { className: "lens-head" },
        h("div", null,
          h("div", { className: "lens-kicker" }, t(lang, "kicker")),
          h("h1", { className: "lens-title" }, t(lang, "title")),
          h("p", { className: "lens-subtitle" }, t(lang, "subtitle"))
        ),
        h("div", { className: "lens-actions" },
          h("div", { className: "lens-seg" },
            [7, 30, 0].map(function (value) {
              return h("button", { key: value,
                className: "lens-seg-btn" + (days === value ? " is-on" : ""),
                onClick: function () { setDays(value); if (view.view === "session") back(); } },
                value === 7 ? t(lang, "days7") : value === 30 ? t(lang, "days30") : t(lang, "all"));
            })
          ),
          h(Button, { variant: "outline", size: "sm",
            onClick: view.view === "session" ? refreshSession : refreshOverview },
            t(lang, "refresh")),
          h("button", { className: "lens-lang",
            onClick: function () { setLang(lang === "fa" ? "en" : "fa"); } },
            t(lang, "lang"))
        )
      ),
      error ? h("div", { className: "lens-error" }, t(lang, "error") + ": " + String(error.message || error)) : null,
      loading ? h("div", { className: "lens-loading" }, t(lang, "loading")) : null,
      !loading && overview.data ? (
        view.view === "session" && sessionState.data && sessionState.data.session
          ? h(SessionView, { data: sessionState.data, lang: lang, onBack: back, onOpen: openSession })
          : h(Overview, { data: overview.data, lang: lang, days: days, onOpen: openSession })
      ) : null,
      h("div", { className: "lens-foot" },
        h(Separator, null),
        h("span", null, "Context Lens · reads local state.db only · estimates are marked")
      )
    );
  }

  if (window.__HERMES_PLUGINS__ && window.__HERMES_PLUGINS__.register) {
    window.__HERMES_PLUGINS__.register("context-lens", App);
  }
})();
