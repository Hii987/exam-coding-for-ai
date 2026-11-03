/* Analyste avec arbitre : logique de l'interface (JavaScript sans dépendance). */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fr = (x, d = 2) => Number(x).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
const frInt = (x) => Number(x).toLocaleString("fr-FR");
const pct = (x, d = 1) => `${fr(100 * x, d)}\u00a0%`;

const ICON = {
  qwen: '<svg viewBox="0 0 24 24"><path d="M12 3l1.8 4.6L18 9l-4.2 1.6L12 15l-1.8-4.4L6 9l4.2-1.4zM18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9z"/></svg>',
  code: '<svg viewBox="0 0 24 24"><path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/></svg>',
  out: '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h10M4 18h7"/></svg>',
  shield: '<svg viewBox="0 0 24 24"><path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z"/></svg>',
  scale: '<svg viewBox="0 0 24 24"><path d="M12 4v16M6 20h12M5 8h14M5 8l-3 6a3 3 0 0 0 6 0zM19 8l-3 6a3 3 0 0 0 6 0z"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7"/></svg>',
  cross: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  q: '<svg viewBox="0 0 24 24"><path d="M4 5h16v10H9l-5 4z"/></svg>',
  answer: '<svg viewBox="0 0 24 24"><path d="M4 12h12M12 6l6 6-6 6"/></svg>',
  warn: '<svg viewBox="0 0 24 24"><path d="M12 4l9 16H3zM12 10v4M12 17v.5"/></svg>',
};

/* ------------------------------------------------------------------ thème */
const root = document.documentElement;
function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { /* stockage indisponible */ }
  const prefersLight = window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches;
  root.dataset.theme = saved || (prefersLight ? "light" : "dark");
  $("#theme-btn").addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) { /* rien */ }
    if (state.bench) renderBench(state.bench);
    if (state.data) renderData(state.data);
  });
}

/* ------------------------------------------------------------------ navigation */
const state = { examples: [], bench: null, data: null, running: false };
function show(view) {
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  if (view === "bench") loadBench();
  if (view === "data") loadData();
  try { history.replaceState(null, "", `#${view}`); } catch (e) { /* rien */ }
  window.scrollTo({ top: 0 });
}

/* ------------------------------------------------------------------ état du modèle */
async function pollStatus() {
  const box = $("#status");
  try {
    const s = await (await fetch("/api/status")).json();
    box.classList.toggle("ok", !!s.llm_ok);
    box.classList.toggle("down", !s.llm_ok);
    $("#status-model").textContent = s.model;
    $("#status-detail").textContent = `${s.llm_detail} · ${frInt(s.rows)} trajets`;
  } catch (e) {
    box.classList.remove("ok"); box.classList.add("down");
    $("#status-model").textContent = "Serveur arrêté";
    $("#status-detail").textContent = "relancez python -m app";
  }
}

/* ------------------------------------------------------------------ coloration Python */
const PY_KW = new Set(["and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except",
  "False", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or",
  "pass", "raise", "return", "True", "try", "while", "with", "yield"]);
const PY_NAMES = new Set(["df", "pd", "np", "stats", "result"]);
function highlight(code) {
  const re = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g;
  let out = "", last = 0, m;
  while ((m = re.exec(code))) {
    out += esc(code.slice(last, m.index));
    const [tok, com, str, num, word] = m;
    if (com) out += `<span class="tk-com">${esc(tok)}</span>`;
    else if (str) out += `<span class="tk-str">${esc(tok)}</span>`;
    else if (num) out += `<span class="tk-num">${esc(tok)}</span>`;
    else if (PY_KW.has(word)) out += `<span class="tk-kw">${esc(tok)}</span>`;
    else if (PY_NAMES.has(word)) out += `<span class="tk-name">${esc(tok)}</span>`;
    else out += esc(tok);
    last = m.index + tok.length;
  }
  return out + esc(code.slice(last));
}

/* ------------------------------------------------------------------ réponse annotée */
function sourceLabel(s) {
  if (s === "question") return "présent dans la question";
  return `calculé par l'appel n° ${s + 1} à run_pandas`;
}
function annotated(text, spans) {
  let out = "", last = 0;
  for (const s of spans || []) {
    out += esc(text.slice(last, s.start));
    const tip = s.ok
      ? `<b>✓ Vérifié</b><br><span class="tt-muted">${esc(sourceLabel(s.source))}</span>`
      : `<b>✕ Non justifié</b><br><span class="tt-muted">aucun calcul n'a produit ${s.kind === "date" ? "cette date" : "ce chiffre"}</span>`;
    out += `<span class="num ${s.ok ? "ok" : "bad"}" data-tip="${esc(tip)}">${esc(text.slice(s.start, s.end))}</span>`;
    last = s.end;
  }
  return out + esc(text.slice(last));
}

/* ------------------------------------------------------------------ infobulle */
function initTooltip() {
  const tt = $("#tooltip");
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-tip]");
    if (!t) return;
    tt.innerHTML = t.dataset.tip;
    tt.hidden = false;
    const r = t.getBoundingClientRect();
    const w = tt.offsetWidth, h = tt.offsetHeight;
    let x = r.left + r.width / 2 - w / 2;
    x = Math.max(8, Math.min(x, innerWidth - w - 8));
    let y = r.top - h - 10;
    if (y < 8) y = r.bottom + 10;
    tt.style.left = `${x}px`; tt.style.top = `${y}px`;
  });
  document.addEventListener("pointerout", (e) => {
    if (e.target.closest("[data-tip]")) tt.hidden = true;
  });
}

/* ------------------------------------------------------------------ pipeline */
const NODES_SYSTEM = [
  ["question", "Question", ICON.q], ["qwen", "Qwen", ICON.qwen], ["tool", "run_pandas", ICON.code],
  ["guard", "Arbitre", ICON.scale], ["answer", "Réponse", ICON.answer]];
const NODES_ALONE = [["question", "Question", ICON.q], ["qwen", "Qwen seul", ICON.qwen], ["answer", "Réponse", ICON.answer]];

function Pipeline(el, mode) {
  const nodes = mode === "system" ? NODES_SYSTEM : NODES_ALONE;
  el.className = `pipeline ${mode === "system" ? "" : "alone"}`;
  el.innerHTML = nodes.map(([id, label, icon]) =>
    `<div class="node" data-node="${id}"><div class="node-dot">${icon}</div>
     <div class="node-label">${label}</div><div class="node-sub"></div></div>`).join("");
  const get = (id) => $(`[data-node="${id}"]`, el);
  return {
    set(id, cls, sub) {
      const n = get(id); if (!n) return;
      n.classList.remove("active", "done", "ok", "fail", "skip");
      if (cls) cls.split(" ").forEach((c) => n.classList.add(c));
      if (sub !== undefined) $(".node-sub", n).textContent = sub;
    },
    sub(id, text) { const n = get(id); if (n) $(".node-sub", n).textContent = text; },
  };
}

/* ------------------------------------------------------------------ cartes du fil */
function card({ icon, iconCls = "", title, step, body, cls = "" }) {
  const el = document.createElement("div");
  el.className = `card ${cls}`;
  el.innerHTML = `<div class="card-head"><div class="card-icon ${iconCls}">${icon}</div>${title}
    ${step !== undefined ? `<span class="step">étape ${step + 1}</span>` : ""}</div>
    <div class="card-body">${body}</div>`;
  return el;
}

/* ------------------------------------------------------------------ lancer une question */
function runQuestion({ question, mode, timeline, pipeline, onClock, onDone, compact = false }) {
  return new Promise((resolve) => {
    const pipe = pipeline ? Pipeline(pipeline, mode) : null;
    timeline.innerHTML = "";
    const t0 = performance.now();
    let thinkingCard = null, thinkStart = 0, finished = false;
    const toolOutputs = [];
    const timer = setInterval(() => {
      const s = (performance.now() - t0) / 1000;
      onClock && onClock(s);
      if (thinkingCard) $(".clock", thinkingCard).textContent = `${fr((performance.now() - thinkStart) / 1000, 1)} s`;
      if (pipe && thinkingCard) pipe.sub("qwen", `${fr((performance.now() - thinkStart) / 1000, 1)} s`);
    }, 100);
    const add = (el) => { timeline.appendChild(el); return el; };
    const dropThinking = () => { if (thinkingCard) { thinkingCard.remove(); thinkingCard = null; } };

    const es = new EventSource(`/api/ask?q=${encodeURIComponent(question)}&mode=${mode}`);
    const finish = (payload) => {
      if (finished) return; finished = true;
      clearInterval(timer); es.close(); dropThinking();
      onDone && onDone(payload); resolve(payload);
    };

    es.onmessage = (msg) => {
      const ev = JSON.parse(msg.data);
      if (ev.type === "start") {
        pipe && pipe.set("question", "done", "");
      } else if (ev.type === "thinking") {
        pipe && pipe.set("qwen", "active");
        thinkStart = performance.now();
        thinkingCard = add(card({ icon: ICON.qwen, iconCls: "qwen", cls: "thinking",
          title: ev.step === 0 ? "Qwen lit la question" : "Qwen reprend la main", step: ev.step,
          body: `<div class="spinner"></div><div class="shimmer"></div><span class="clock">0,0 s</span>` }));
      } else if (ev.type === "llm") {
        dropThinking();
        const secs = fr((performance.now() - thinkStart) / 1000, 1);
        pipe && pipe.set("qwen", "done", `${secs} s`);
        if (ev.tool_calls && ev.tool_calls.length) {
          for (const c of ev.tool_calls) {
            const code = (c.arguments && c.arguments.code) || JSON.stringify(c.arguments);
            add(card({ icon: ICON.code, iconCls: "qwen", step: ev.step,
              title: `Qwen écrit du code <span class="clock">· ${secs} s</span>`,
              body: `<pre class="code">${highlight(code)}</pre>` }));
          }
          pipe && pipe.set("tool", "active", "exécution…");
        } else if (ev.content && mode === "system") {
          add(card({ icon: ICON.qwen, iconCls: "qwen", step: ev.step,
            title: `Qwen propose une réponse <span class="clock">· ${secs} s</span>`,
            body: `<p>${esc(ev.content)}</p>` }));
          pipe && pipe.set("guard", "active", "vérification…");
        }
      } else if (ev.type === "tool") {
        if (ev.blocked) {
          pipe && pipe.set("tool", "fail", "bloqué");
          add(card({ icon: ICON.shield, iconCls: "bad", step: ev.step, cls: "blocked",
            title: "La barrière bloque le code", body: `<pre class="out err">${esc(ev.result)}</pre>` }));
        } else {
          const err = ev.result.startsWith("ERREUR");
          if (!err) toolOutputs.push(ev.result);
          pipe && pipe.set("tool", err ? "fail" : "done", err ? "erreur" : `${toolOutputs.length} calcul${toolOutputs.length > 1 ? "s" : ""}`);
          add(card({ icon: ICON.out, iconCls: err ? "bad" : "tool", step: ev.step,
            title: err ? "Le code a échoué (renvoyé à Qwen)" : `Résultat calculé <span class="clock">· sortie n° ${toolOutputs.length}</span>`,
            body: `<pre class="out ${err ? "err" : ""}">${esc(ev.result)}</pre>` }));
        }
      } else if (ev.type === "guard") {
        if (ev.ok) {
          pipe && pipe.set("guard", "ok", "accepté");
          add(card({ icon: ICON.check, iconCls: "ok", step: ev.step, title: "L'arbitre accepte",
            body: `<p>Chaque chiffre de la réponse sort d'un calcul.</p>` }));
        } else {
          pipe && pipe.set("guard", "fail", "refusé");
          add(card({ icon: ICON.scale, iconCls: "bad", step: ev.step, cls: "refused", title: "L'arbitre refuse",
            body: `<p>Chiffres sans calcul : ${ev.unsupported.map((u) => `<span class="badge bad">${esc(u)}</span>`).join(" ")}</p>
                   <p style="margin-top:8px;color:var(--text-2);font-size:13.5px">La réponse est renvoyée à Qwen avec ce message.</p>` }));
        }
      } else if (ev.type === "done") {
        const refused = ev.status !== "answered";
        if (pipe) {
          if (mode === "system" && !refused) pipe.set("guard", "ok", "accepté");
          pipe.set("answer", refused ? "fail" : "ok", refused ? "refus" : `${fr(ev.seconds, 1)} s`);
        }
        const legend = mode === "system" && (ev.spans || []).length
          ? `<div class="legend-inline"><span><i class="lg-swatch ok"></i>chiffre vérifié</span><span><i class="lg-swatch bad"></i>chiffre non justifié</span><span>survolez un chiffre pour sa source</span></div>` : "";
        const textHtml = mode === "system" ? annotated(ev.answer, ev.spans) : esc(ev.answer);
        add(card({ icon: refused ? ICON.cross : ICON.answer, iconCls: refused ? "bad" : "ok",
          cls: `answer-card ${refused ? "refused" : ""}`,
          title: refused ? "Réponse refusée par le système" : mode === "system" ? "Réponse vérifiée" : "Réponse du modèle seul",
          body: `<div class="answer-text">${textHtml}</div>${legend}` }));
        finish(ev);
      } else if (ev.type === "error") {
        add(card({ icon: ICON.warn, iconCls: "bad", cls: "error-card", title: "Erreur", body: `<p>${esc(ev.message)}</p>` }));
        pipe && pipe.set("qwen", "fail", "erreur");
        finish(ev);
      }
    };
    es.onerror = () => {
      if (finished) return;
      add(card({ icon: ICON.warn, iconCls: "bad", cls: "error-card", title: "Connexion interrompue",
        body: "<p>Le serveur ne répond plus. Est-il toujours lancé (python -m app) ?</p>" }));
      finish({ type: "error" });
    };
  });
}

/* ------------------------------------------------------------------ vue Analyste */
function metaHtml(ev) {
  if (!ev || ev.type !== "done") return "";
  const u = ev.usage || {};
  const parts = [
    `<span class="meta">Durée <b>${fr(ev.seconds, 1)} s</b></span>`,
    `<span class="meta">Tokens lus <b>${frInt(u.prompt_tokens || 0)}</b></span>`,
    `<span class="meta">Tokens écrits <b>${frInt(u.completion_tokens || 0)}</b></span>`,
  ];
  if (ev.expected !== undefined) {
    parts.push(`<span class="meta">Réponse attendue <b>${esc(fmtExpected(ev.expected))}</b></span>`);
    parts.push(`<span class="badge ${ev.correct ? "ok" : "bad"}">${ev.correct ? "✓ juste" : "✕ faux"}</span>`);
  }
  if (ev.trace_path) parts.push(`<span class="meta" title="${esc(ev.trace_path)}">Trace sauvegardée <b>traces/</b></span>`);
  return parts.join("");
}
function fmtExpected(v) {
  return typeof v === "number" ? (Number.isInteger(v) ? frInt(v) : fr(v, 2)) : String(v);
}

function autoGrow(ta) {
  const f = () => { ta.style.height = "auto"; ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`; };
  ta.addEventListener("input", f); f();
}
function submitOnEnter(ta, form) {
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
  });
}

function initAsk() {
  const form = $("#ask-form"), input = $("#ask-input");
  autoGrow(input); submitOnEnter(input, form);
  Pipeline($("#ask-pipeline"), "system");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || state.running) return;
    state.running = true;
    const btn = $(".send", form); btn.disabled = true;
    $("#ask-meta").innerHTML = "";
    const ev = await runQuestion({ question: q, mode: "system", timeline: $("#ask-timeline"),
      pipeline: $("#ask-pipeline") });
    $("#ask-meta").innerHTML = metaHtml(ev);
    btn.disabled = false; state.running = false;
  });
}

/* ------------------------------------------------------------------ vue Duel */
function initDuel() {
  const form = $("#duel-form"), input = $("#duel-input");
  autoGrow(input); submitOnEnter(input, form);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || state.running) return;
    state.running = true;
    const btn = $(".send", form); btn.disabled = true;
    const ex = state.examples.find((x) => x.question === q);
    const banner = $("#duel-expected");
    banner.hidden = true;
    const runs = ["model_alone", "system"].map((mode) => {
      $(`#duel-verdict-${mode}`).innerHTML = "";
      const clock = $(`#duel-clock-${mode}`);
      return runQuestion({ question: q, mode, timeline: $(`#duel-tl-${mode}`), compact: true,
        onClock: (s) => { clock.textContent = `${fr(s, 1)} s`; },
        onDone: (ev) => {
          if (ev.type === "done" && ev.expected !== undefined) {
            $(`#duel-verdict-${mode}`).innerHTML = ev.correct
              ? `<div class="big-verdict ok"><span class="mark">✓</span>Juste</div>`
              : `<div class="big-verdict bad"><span class="mark">✕</span>${ev.status === "refused" ? "Refus : pas de chiffre vérifié" : "Faux"}</div>`;
          }
        } });
    });
    const results = await Promise.all(runs);
    const withExp = results.find((r) => r && r.expected !== undefined);
    if (withExp || ex) {
      banner.innerHTML = `Réponse attendue (calculée par mon code de référence) : <b>${esc(fmtExpected(withExp ? withExp.expected : ex.expected))}</b>`;
      banner.hidden = false;
    }
    btn.disabled = false; state.running = false;
  });
}

/* ------------------------------------------------------------------ puces d'exemples */
const TRAP = "Combien de trajets y aura-t-il en octobre 2024 ?";
function fillChips(el, input, list) {
  el.innerHTML = "";
  for (const item of list) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `chip ${item.trap ? "trap" : ""}`;
    b.textContent = item.label;
    b.title = item.question;
    b.addEventListener("click", () => {
      input.value = item.question; input.dispatchEvent(new Event("input"));
      input.focus();
    });
    el.appendChild(b);
  }
}
async function loadExamples() {
  try { state.examples = await (await fetch("/api/examples")).json(); } catch (e) { state.examples = []; }
  const short = (q) => q.replace(/ \?$/, "").replace(/^(Quel(le)?|Combien|À quelle|Parmi|De combien) /, (m) => m);
  const picks = ["t07", "t03", "t05", "t08", "t09", "t12"];
  const list = state.examples.filter((x) => picks.includes(x.id))
    .map((x) => ({ label: short(x.question), question: x.question }));
  const withTrap = [...list, { label: "Piège : trajets en octobre 2024", question: TRAP, trap: true }];
  fillChips($("#ask-chips"), $("#ask-input"), withTrap);
  fillChips($("#duel-chips"), $("#duel-input"),
    state.examples.map((x) => ({ label: `${x.id} · ${short(x.question)}`, question: x.question })));
}

/* ------------------------------------------------------------------ vue Barrière & arbitre */
const ATTACKS = [
  { label: "Calcul normal", safe: true, code: "result = df[df['start_city'] == 'Hoboken'].shape[0]" },
  { label: "Moyenne avec IC", safe: true, code: "result = stats.mean_ci(df['duration_min'])" },
  { label: "import os", code: "import os\nresult = os.listdir('.')" },
  { label: "Lire /etc/passwd", code: "result = open('/etc/passwd').read()" },
  { label: "Écrire un fichier", code: "df.to_csv('vol.csv')" },
  { label: "__import__", code: "result = __import__('os').system('ls')" },
  { label: "Évasion __subclasses__", code: "result = ().__class__.__bases__[0].__subclasses__()" },
  { label: "pd.io.common.os", code: "result = pd.io.common.os.system('ls')" },
  { label: "Boucle infinie", code: "while True:\n    pass" },
];
const GUARD_PRESETS = [
  { label: "Réponse juste", outputs: "55380", answer: "55 380 trajets ont commencé à Hoboken." },
  { label: "Chiffre inventé", outputs: "55380", answer: "55 380 trajets ont commencé à Hoboken, soit 52 % du total." },
  { label: "Arrondi correct", outputs: "9.781234", answer: "La durée moyenne d'un trajet est de 9,78 minutes." },
  { label: "Mauvais arrondi", outputs: "9.781234", answer: "La durée moyenne d'un trajet est de 9,9 minutes." },
  { label: "Proportion → %", outputs: "0.738908", answer: "73,9 % des trajets sont faits par des abonnés." },
  { label: "Date inventée", outputs: "2024-09-13    5210", answer: "Le jour le plus chargé est le 2024-09-21." },
];

function initRules() {
  const code = $("#sb-code"), chips = $("#sb-chips");
  ATTACKS.forEach((a) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = `chip ${a.safe ? "safe" : "danger"}`; b.textContent = a.label;
    b.addEventListener("click", () => { code.value = a.code; runSandbox(); });
    chips.appendChild(b);
  });
  code.value = ATTACKS[2].code;
  $("#sb-run").addEventListener("click", runSandbox);
  code.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runSandbox(); }
  });

  const gchips = $("#gd-chips"), outs = $("#gd-outputs"), ans = $("#gd-answer");
  GUARD_PRESETS.forEach((p) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = p.label;
    b.addEventListener("click", () => { outs.value = p.outputs; ans.value = p.answer; runGuard(); });
    gchips.appendChild(b);
  });
  outs.value = GUARD_PRESETS[1].outputs; ans.value = GUARD_PRESETS[1].answer;
  let t = null;
  [outs, ans].forEach((el) => el.addEventListener("input", () => { clearTimeout(t); t = setTimeout(runGuard, 180); }));
  runGuard();
}

async function runSandbox() {
  const box = $("#sb-result");
  box.innerHTML = `<div class="loading">Analyse du code…</div>`;
  const r = await (await fetch("/api/sandbox", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: $("#sb-code").value }) })).json();
  if (r.blocked) {
    box.innerHTML = `<div class="verdict-box bad"><div class="v-icon">${ICON.shield}</div><div>
      <div class="v-title">Bloqué avant exécution</div>
      <div class="v-text">${esc(r.reason)}. Le code n'a jamais tourné.</div></div></div>`;
  } else if (!r.ok) {
    box.innerHTML = `<div class="verdict-box bad"><div class="v-icon">${ICON.warn}</div><div style="min-width:0;flex:1">
      <div class="v-title">Autorisé, mais en erreur</div>
      <div class="v-text">Le code a passé la barrière ; son erreur est renvoyée au modèle.</div>
      <pre class="out err">${esc(r.error)}</pre></div></div>`;
  } else {
    box.innerHTML = `<div class="verdict-box ok"><div class="v-icon">${ICON.check}</div><div style="min-width:0;flex:1">
      <div class="v-title">Autorisé et exécuté</div>
      <div class="v-text">Valeur de <code>result</code> renvoyée au modèle :</div>
      <pre class="out">${esc(r.output || r.stdout || "(vide)")}</pre></div></div>`;
  }
}

async function runGuard() {
  const outputs = $("#gd-outputs").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const answer = $("#gd-answer").value;
  const r = await (await fetch("/api/guard", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer, outputs }) })).json();
  const n = r.unsupported.length;
  $("#gd-result").innerHTML = `
    <div class="gd-answer">${annotated(answer, r.spans) || '<span style="color:var(--muted)">(réponse vide)</span>'}</div>
    <div class="verdict-box ${r.ok ? "ok" : "bad"}" style="margin-top:12px">
      <div class="v-icon">${r.ok ? ICON.check : ICON.scale}</div><div>
      <div class="v-title">${r.ok ? "Réponse acceptée" : `Réponse refusée : ${n} chiffre${n > 1 ? "s" : ""} sans calcul`}</div>
      <div class="v-text">${r.ok ? "Chaque chiffre et chaque date se retrouvent dans une sortie de run_pandas."
        : `Non justifié : ${r.unsupported.map((u) => `<b>${esc(u)}</b>`).join(", ")}. L'agent renverrait la réponse à Qwen.`}</div>
      </div></div>`;
}

/* ------------------------------------------------------------------ vue Benchmark */
async function loadBench() {
  const body = $("#bench-body");
  if (!state.bench) body.innerHTML = `<div class="loading">Lecture des résultats…</div>`;
  try { state.bench = await (await fetch("/api/bench")).json(); } catch (e) { state.bench = { available: false }; }
  renderBench(state.bench);
}

const MODE_LABEL = { system: "Système", model_alone: "Modèle seul" };
function renderBench(b) {
  const body = $("#bench-body");
  if (!b.available) {
    body.innerHTML = `<div class="empty"><h3>Pas encore de résultats</h3>
      <p>Lancez le benchmark (30 à 45 minutes avec Qwen3.5-4B), puis revenez sur cette page.</p>
      <span class="cmd">python bench/run_bench.py --runs 3 <button class="copy" data-copy="python bench/run_bench.py --runs 3">Copier</button></span></div>`;
    bindCopy(body);
    return;
  }
  const modes = ["system", "model_alone"].filter((m) => b.modes[m]);
  const sys = b.modes.system, alone = b.modes.model_alone;
  const tile = (m) => {
    const d = b.modes[m];
    return `<div class="tile"><div class="tile-label"><span class="swatch ${m === "system" ? "s-system" : "s-alone"}"></span>${MODE_LABEL[m]}</div>
      <div class="tile-value">${fr(100 * d.mean, 0)}<small> %</small></div>
      <div class="tile-foot">±\u00a0${fr(100 * d.sd, 1)}\u00a0pts (écart-type) · lancements : ${d.per_run.map((a) => `${fr(100 * a, 0)}\u00a0%`).join(" · ")}</div></div>`;
  };
  const gap = sys && alone ? `<div class="tile"><div class="tile-label">Gain du système</div>
      <div class="tile-value">${sys.mean - alone.mean >= 0 ? "+" : "−"}${fr(Math.abs(100 * (sys.mean - alone.mean)), 0)}<small> pts</small></div>
      <div class="tile-foot">${sys.refused} refus de l'arbitre · ${frInt(Math.round(sys.tokens))} tokens/tâche contre ${frInt(Math.round(alone.tokens))}</div></div>` : "";

  // grille tâches × lancements
  const cols = [];
  modes.forEach((m) => b.modes[m].runs.forEach((r, i) => cols.push({ m, r, first: i === 0 })));
  const cellOf = (t, m, r) => b.cells.find((c) => c.task === t && c.mode === m && c.run === r);
  const head = `<tr><th class="q">Tâche</th>${cols.map((c) =>
    `<th class="${c.first ? "grp" : ""}">${c.first ? `<span class="swatch ${c.m === "system" ? "s-system" : "s-alone"}" style="display:inline-block;margin-right:6px"></span>${MODE_LABEL[c.m]} · ` : ""}L${c.r}</th>`).join("")}</tr>`;
  const rows = b.tasks.map((t) => `<tr><th class="q"><span class="tid">${esc(t.id)}</span>${esc(t.question)}</th>${cols.map((c) => {
    const cell = cellOf(t.id, c.m, c.r);
    if (!cell) return `<td class="${c.first ? "grp" : ""}"><span class="cell na">·</span></td>`;
    const tip = `<b>${cell.correct ? "✓ Juste" : "✕ Faux"}</b> · ${MODE_LABEL[c.m]}, lancement ${c.r}<br><span class="tt-muted">Attendu : ${esc(fmtExpected(cell.expected))}</span><br>${esc((cell.answer || "(pas de réponse)").slice(0, 160))}<br><span class="tt-muted">Cliquez pour la trace</span>`;
    return `<td class="${c.first ? "grp" : ""}"><button class="cell ${cell.correct ? "ok" : "bad"}" data-tip="${esc(tip)}"
      data-mode="${c.m}" data-run="${c.r}" data-task="${esc(t.id)}" aria-label="${esc(t.id)} ${MODE_LABEL[c.m]} lancement ${c.r} : ${cell.correct ? "juste" : "faux"}">${cell.correct ? "✓" : "✕"}</button></td>`;
  }).join("")}</tr>`).join("");

  body.innerHTML = `
    <div class="tiles">${modes.map(tile).join("")}${gap}</div>
    <div class="section-title">Exactitude moyenne et dispersion</div>
    <p class="section-sub">Barre : moyenne des ${Math.max(...modes.map((m) => b.modes[m].runs.length))} lancements. Trait : ± un écart-type. Points : chaque lancement.</p>
    <div class="chart-card">${accuracyChart(b, modes)}</div>
    <div class="section-title">Chaque tâche, chaque lancement</div>
    <p class="section-sub">✓ juste, ✕ faux (un refus de l'arbitre compte comme faux). Survolez pour la réponse, cliquez pour la trace complète.</p>
    <div class="grid-wrap"><table class="hm"><thead>${head}</thead><tbody>${rows}</tbody></table></div>`;
  $$(".cell[data-task]", body).forEach((el) => el.addEventListener("click", () =>
    openTrace(el.dataset.mode, Number(el.dataset.run), el.dataset.task)));
}

function cssVar(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }

function accuracyChart(b, modes) {
  const W = 760, rowH = 64, padL = 120, padR = 70, top = 10, H = top + rowH * modes.length + 34;
  const x = (v) => padL + (W - padL - padR) * v;
  const colors = { system: cssVar("--accent"), model_alone: cssVar("--alone") };
  const surface = cssVar("--panel-solid");
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Exactitude moyenne par mode, avec écart-type">`;
  [0, .25, .5, .75, 1].forEach((v) => {
    svg += `<line class="grid" x1="${x(v)}" x2="${x(v)}" y1="${top}" y2="${H - 26}"/>`;
    svg += `<text x="${x(v)}" y="${H - 8}" text-anchor="middle">${v * 100} %</text>`;
  });
  modes.forEach((m, i) => {
    const d = b.modes[m], cy = top + rowH * i + rowH / 2, bh = 22;
    const lo = Math.max(0, d.mean - d.sd), hi = Math.min(1, d.mean + d.sd);
    const w = Math.max(0, x(d.mean) - x(0));
    svg += `<text class="t-strong" x="${padL - 14}" y="${cy + 4}" text-anchor="end">${MODE_LABEL[m]}</text>`;
    svg += `<path d="M${x(0)},${cy - bh / 2} h${Math.max(0, w - 4)} a4,4 0 0 1 4,4 v${bh - 8} a4,4 0 0 1 -4,4 h-${Math.max(0, w - 4)} z" fill="${colors[m]}" opacity=".9"/>`;
    svg += `<line x1="${x(lo)}" x2="${x(hi)}" y1="${cy}" y2="${cy}" stroke="${cssVar("--text")}" stroke-width="2"/>`;
    svg += `<line x1="${x(lo)}" x2="${x(lo)}" y1="${cy - 7}" y2="${cy + 7}" stroke="${cssVar("--text")}" stroke-width="2"/>`;
    svg += `<line x1="${x(hi)}" x2="${x(hi)}" y1="${cy - 7}" y2="${cy + 7}" stroke="${cssVar("--text")}" stroke-width="2"/>`;
    d.per_run.forEach((a, k) => {
      svg += `<circle cx="${x(a)}" cy="${cy + bh / 2 + 9}" r="4.5" fill="${colors[m]}" stroke="${surface}" stroke-width="2"
        data-tip="<b>${MODE_LABEL[m]}</b>, lancement ${d.runs[k]} : ${fr(100 * a, 0)} %"/>`;
    });
    svg += `<text class="t-strong" x="${x(hi) + 10}" y="${cy + 4}">${fr(100 * d.mean, 0)} %</text>`;
    svg += `<rect class="hit" x="${padL}" y="${cy - rowH / 2}" width="${W - padL - padR}" height="${rowH}"
      data-tip="<b>${MODE_LABEL[m]}</b><br>moyenne ${fr(100 * d.mean, 1)} % · écart-type ${fr(100 * d.sd, 1)} pts<br><span class='tt-muted'>lancements : ${d.per_run.map((a) => fr(100 * a, 0) + " %").join(", ")}</span>"/>`;
  });
  return svg + "</svg>";
}

async function openTrace(mode, run, task) {
  const drawer = $("#drawer"), body = $("#drawer-body");
  body.innerHTML = `<div class="loading">Chargement de la trace…</div>`;
  drawer.hidden = false;
  const r = await (await fetch(`/api/bench/trace?mode=${mode}&run=${run}&task=${encodeURIComponent(task)}`)).json();
  const q = (state.bench.tasks.find((t) => t.id === task) || {}).question || task;
  body.innerHTML = `<h3 id="drawer-title">${esc(task)} · ${esc(q)}</h3>
    <div class="sub">${MODE_LABEL[mode]}, lancement ${run} · statut : ${esc(r.status)} · ${frInt(r.tokens || 0)} tokens</div>
    <div class="answer-foot" style="margin:0 0 16px">
      <span class="badge ${r.correct ? "ok" : "bad"}">${r.correct ? "✓ juste" : "✕ faux"}</span>
      <span class="meta">Attendu <b>${esc(fmtExpected(r.expected))}</b></span></div>
    <div class="timeline">${traceCards(r.trace || []).join("")}
      <div class="card answer-card"><div class="card-head"><div class="card-icon ${r.correct ? "ok" : "bad"}">${ICON.answer}</div>Réponse finale</div>
      <div class="card-body"><div class="answer-text" style="font-size:18px">${esc(r.answer || "(aucune)")}</div></div></div></div>`;
}

function traceCards(trace) {
  return trace.map((t) => {
    let el;
    if (t.type === "llm") {
      if (t.tool_calls && t.tool_calls.length) {
        el = card({ icon: ICON.code, iconCls: "qwen", step: t.step, title: "Qwen écrit du code",
          body: t.tool_calls.map((c) => `<pre class="code">${highlight((c.arguments && c.arguments.code) || "")}</pre>`).join("") });
      } else {
        el = card({ icon: ICON.qwen, iconCls: "qwen", step: t.step, title: "Qwen répond", body: `<p>${esc(t.content)}</p>` });
      }
    } else if (t.type === "tool") {
      const err = t.blocked || String(t.result).startsWith("ERREUR");
      el = card({ icon: t.blocked ? ICON.shield : ICON.out, iconCls: err ? "bad" : "tool", step: t.step,
        title: t.blocked ? "Bloqué par la barrière" : err ? "Erreur du code" : "Résultat calculé",
        body: `<pre class="out ${err ? "err" : ""}">${esc(t.result)}</pre>` });
    } else if (t.type === "guard") {
      el = card({ icon: t.ok ? ICON.check : ICON.scale, iconCls: t.ok ? "ok" : "bad", step: t.step,
        title: t.ok ? "L'arbitre accepte" : "L'arbitre refuse",
        body: t.ok ? "<p>Tous les chiffres sortent d'un calcul.</p>"
          : `<p>Sans calcul : ${t.unsupported.map((u) => `<span class="badge bad">${esc(u)}</span>`).join(" ")}</p>` });
    }
    return el ? el.outerHTML : "";
  });
}

function initDrawer() {
  const drawer = $("#drawer");
  drawer.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) drawer.hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") drawer.hidden = true; });
}

function bindCopy(rootEl) {
  $$("[data-copy]", rootEl).forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); b.textContent = "Copié"; } catch (e) { b.textContent = "Ctrl+C"; }
  }));
}

/* ------------------------------------------------------------------ vue Données */
async function loadData() {
  if (state.data) return renderData(state.data);
  try { state.data = await (await fetch("/api/data")).json(); renderData(state.data); }
  catch (e) { $("#data-body").innerHTML = `<div class="empty"><h3>Données indisponibles</h3><p>Lancez python scripts/prepare_data.py</p></div>`; }
}

function renderData(d) {
  const steps = d.log.steps || [];
  const raw = steps.length ? steps[0].rows_before : 0;
  const clean = steps.length ? steps[steps.length - 1].rows_after : 0;
  const stepsHtml = steps.map((s, i) => {
    const isDoc = /citibike|Citi Bike|Carte/.test(s.source);
    const k = s.rows_removed > 0 ? `<b>−${frInt(s.rows_removed)}</b>lignes retirées`
      : s.values_changed && s.step.includes("reconstitué") ? `<b>${frInt(s.values_changed)}</b>libellés corrigés`
      : s.values_changed ? `<b>${frInt(s.values_changed)}</b>valeurs converties`
      : `<b class="zero">0</b>vérifié`;
    return `<div class="stepi"><span class="n">${i + 1}</span><div><div class="t">${esc(s.step)}</div>
      <div class="r">${esc(s.reason)}</div><span class="src ${isDoc ? "doc" : ""}" title="${esc(s.source)}">${isDoc ? "règle d'un document : " : ""}${esc(s.source.length > 70 ? s.source.slice(0, 70) + "…" : s.source)}</span></div>
      <div class="k">${k}</div></div>`;
  }).join("");
  const u = d.uncertainty;
  $("#data-body").innerHTML = `
    <div class="data-grid">
      <div class="chart-card">
        <div class="label-sm">Brique 6 · journal de nettoyage</div>
        <div class="funnel-head"><span class="from">${frInt(raw)}</span><span class="arrow">→</span><span class="to">${frInt(clean)}</span>
          <span class="meta">−${frInt(raw - clean)} lignes · ${fr(100 * (raw - clean) / raw, 2)} %</span></div>
        <div class="steps">${stepsHtml}</div>
      </div>
      <div class="stack">
        <div class="chart-card">
          <div class="label-sm">Brique 8 · durée moyenne d'un trajet (IC à 95 %)</div>
          ${ciChart([
            { label: "Abonnés", ci: u.mean.member, n: u.n.member },
            { label: "Occasionnels", ci: u.mean.casual, n: u.n.casual },
          ], { unit: " min", d: 2 })}
          <div class="answer-foot"><span class="meta">Différence occasionnels − abonnés <b>+${fr(u.diff_mean.estimate)} min</b></span>
            <span class="meta">IC 95 % <b>[${fr(u.diff_mean.low)} ; ${fr(u.diff_mean.high)}]</b></span></div>
        </div>
        <div class="chart-card">
          <div class="label-sm">Brique 8 · part des vélos électriques (IC de Wilson)</div>
          ${ciChart([
            { label: "Abonnés", ci: u.electric.member, n: u.n.member },
            { label: "Occasionnels", ci: u.electric.casual, n: u.n.casual },
          ], { pct: true, d: 1 })}
          <div class="answer-foot"><span class="meta">Écart <b>+${fr(100 * u.diff_electric.estimate, 1)} pts</b></span>
            <span class="meta">IC 95 % <b>[${fr(100 * u.diff_electric.low, 1)} ; ${fr(100 * u.diff_electric.high, 1)}]</b></span></div>
        </div>
        <div class="callout"><h4>⚠ Ce que ces données ne permettent pas de conclure</h4><ul>
          <li><b>Pas de causalité.</b> Personne n'a été tiré au sort : être abonné ne « raccourcit » pas un trajet.</li>
          <li><b>Intervalles trop étroits.</b> Un même usager fait beaucoup de trajets, et le fichier n'a pas d'identifiant d'usager : les trajets ne sont pas indépendants.</li>
          <li><b>Un mois, deux villes.</b> Septembre 2024 à Jersey City et Hoboken seulement.</li>
        </ul></div>
      </div>
    </div>`;
}

function ciChart(rows, { unit = "", pct: isPct = false, d = 2 }) {
  const k = isPct ? 100 : 1, u = isPct ? " %" : unit;
  const lo = Math.min(...rows.map((r) => r.ci.low)), hi = Math.max(...rows.map((r) => r.ci.high));
  const span = hi - lo, a = lo - span * 0.25, b = hi + span * 0.25;
  const W = 520, padL = 110, padR = 80, rowH = 46, top = 6, H = top + rowH * rows.length + 30;
  const x = (v) => padL + (W - padL - padR) * (v - a) / (b - a);
  const ink = cssVar("--text"), acc = cssVar("--accent"), surface = cssVar("--panel-solid");
  const ticks = niceTicks(a, b, 4);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Intervalles de confiance">`;
  ticks.forEach((t) => {
    svg += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${top}" y2="${H - 24}"/>`;
    svg += `<text x="${x(t)}" y="${H - 6}" text-anchor="middle">${fr(t * k, isPct ? 0 : 1)}${u}</text>`;
  });
  rows.forEach((r, i) => {
    const cy = top + rowH * i + rowH / 2;
    svg += `<text class="t-strong" x="${padL - 14}" y="${cy + 4}" text-anchor="end">${r.label}</text>`;
    svg += `<line x1="${x(r.ci.low)}" x2="${x(r.ci.high)}" y1="${cy}" y2="${cy}" stroke="${ink}" stroke-width="2"/>`;
    svg += `<line x1="${x(r.ci.low)}" x2="${x(r.ci.low)}" y1="${cy - 7}" y2="${cy + 7}" stroke="${ink}" stroke-width="2"/>`;
    svg += `<line x1="${x(r.ci.high)}" x2="${x(r.ci.high)}" y1="${cy - 7}" y2="${cy + 7}" stroke="${ink}" stroke-width="2"/>`;
    svg += `<circle cx="${x(r.ci.estimate)}" cy="${cy}" r="6" fill="${acc}" stroke="${surface}" stroke-width="2"/>`;
    const right = x(r.ci.high) + 12 < W - 4 - 70;
    svg += `<text class="t-strong" x="${right ? x(r.ci.high) + 12 : x(r.ci.low) - 12}" y="${cy + 4}" text-anchor="${right ? "start" : "end"}">${fr(r.ci.estimate * k, d)}${u}</text>`;
    svg += `<rect class="hit" x="${padL}" y="${cy - rowH / 2}" width="${W - padL - padR}" height="${rowH}"
      data-tip="<b>${r.label}</b> · n = ${frInt(r.n)}<br>${fr(r.ci.estimate * k, d)}${u}<br><span class='tt-muted'>IC 95 % [${fr(r.ci.low * k, d)} ; ${fr(r.ci.high * k, d)}]</span>"/>`;
  });
  return svg + "</svg>";
}

function niceTicks(a, b, n) {
  const step0 = (b - a) / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) || step0;
  const out = [];
  for (let t = Math.ceil(a / step) * step; t <= b + 1e-9; t += step) out.push(+t.toFixed(10));
  return out;
}

/* ------------------------------------------------------------------ démarrage */
function init() {
  initTheme();
  initTooltip();
  initDrawer();
  $$(".nav-btn").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
  initAsk(); initDuel(); initRules();
  loadExamples();
  pollStatus(); setInterval(pollStatus, 15000);
  const start = location.hash.slice(1);
  if (["ask", "duel", "rules", "bench", "data"].includes(start)) show(start);
}
init();
