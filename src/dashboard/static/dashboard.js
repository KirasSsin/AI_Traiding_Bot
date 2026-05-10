// QUANT::TERMINAL — S26 ADR 0040 dashboard frontend.
// Vanilla JS, no framework. Tab navigation + docs render + terminal aesthetic.
"use strict";

const API = {
  strategies: "/api/strategies",
  intervals: "/api/intervals",
  availability: "/api/data/availability",
  backtest: "/api/backtest",
  runs: "/api/runs",
  docs: "/api/docs",
  strategyInfo: (id) => `/api/strategy/${id}/info`,  // S42 T6 — supported_combos lookup
};

const $ = (id) => document.getElementById(id);

let availability = {};
let docsLoaded = false;

// ──────────────────────────────────────────────
//  CLOCK (header)
// ──────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  const el = $("clock");
  if (el) el.textContent = `${hh}:${mm}:${ss}`;
}
setInterval(updateClock, 1000);
updateClock();

// ──────────────────────────────────────────────
//  TAB NAVIGATION
// ──────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`tab-${tab}`).classList.add("active");
    if (tab === "documentation" && !docsLoaded) loadDocs();
    if (tab === "history") loadHistory();
  });
});

// ──────────────────────────────────────────────
//  INIT
// ──────────────────────────────────────────────
async function init() {
  try {
    const [strategies, intervals, avail] = await Promise.all([
      fetch(API.strategies).then((r) => r.json()),
      fetch(API.intervals).then((r) => r.json()),
      fetch(API.availability).then((r) => r.json()),
    ]);
    availability = avail;

    const stratSel = $("strategy-select");
    for (const sid in strategies) {
      const opt = document.createElement("option");
      opt.value = sid;
      opt.textContent = strategies[sid].label;
      stratSel.appendChild(opt);
    }

    const symSel = $("symbol-select");
    for (const sym of Object.keys(availability).sort()) {
      const opt = document.createElement("option");
      opt.value = sym;
      opt.textContent = sym;
      symSel.appendChild(opt);
    }

    const ivSel = $("interval-select");
    for (const iv of intervals) {
      const opt = document.createElement("option");
      opt.value = iv.id;
      opt.textContent = iv.label;
      ivSel.appendChild(opt);
    }

    symSel.addEventListener("change", () => {
      updateDataInfo();
      applyComboGates(stratSel.value);
    });
    ivSel.addEventListener("change", updateDataInfo);
    stratSel.addEventListener("change", () => {
      applyComboGates(stratSel.value);
    });
    updateDataInfo();
    // Initial gating apply for default selected strategy
    applyComboGates(stratSel.value);

    $("backtest-form").addEventListener("submit", handleSubmit);
    $("refresh-history").addEventListener("click", loadHistory);
    loadHistory();
  } catch (err) {
    console.error("Init error:", err);
    alert(`Init error: ${err.message}`);
  }
}

// ──────────────────────────────────────────────
//  DATA AVAILABILITY INFO
// ──────────────────────────────────────────────
function updateDataInfo() {
  const sym = $("symbol-select").value;
  const iv = $("interval-select").value;
  const symData = availability[sym] || {};
  const ivData = symData[iv];
  const el = $("data-info");
  if (!ivData) {
    el.innerHTML = `<span class="warn">⚠ Нет данных для ${sym} ${iv}.</span><br>Запусти backfill: <code>TESTNET=false .venv/bin/python -m src backfill --symbol ${sym} --interval ${iv} --from 2023-01-01 --to 2026-04-26</code>`;
    return;
  }
  el.innerHTML = `<span class="ok">▸ DATA OK</span> · ${ivData.bars.toLocaleString()} bars · ${ivData.start.slice(0, 10)} → ${ivData.end.slice(0, 10)}`;
}

// ──────────────────────────────────────────────
//  S42 T6 — COMBO GATES (atr_breakout-style multi-combo presets)
// ──────────────────────────────────────────────
let _strategyInfoCache = {};

async function fetchStrategyInfo(strategyId) {
  if (_strategyInfoCache[strategyId]) return _strategyInfoCache[strategyId];
  try {
    const r = await fetch(API.strategyInfo(strategyId));
    if (!r.ok) return null;
    const data = await r.json();
    _strategyInfoCache[strategyId] = data;
    return data;
  } catch {
    return null;
  }
}

async function applyComboGates(strategyId) {
  const symSel = $("symbol-select");
  const tfSel = $("interval-select");
  // Reset: enable all options first
  for (const sel of [symSel, tfSel]) {
    Array.from(sel.options).forEach((opt) => { opt.disabled = false; });
  }
  const info = await fetchStrategyInfo(strategyId);
  if (!info) return;

  // S42.1 — legacy single-combo lock (S39 ADR 0059): locked_symbol + locked_interval
  // Disable everything except the locked combo. Auto-switch к it.
  if (info.locked_symbol || info.locked_interval) {
    if (info.locked_symbol) {
      Array.from(symSel.options).forEach((opt) => {
        if (opt.value !== info.locked_symbol) opt.disabled = true;
      });
      symSel.value = info.locked_symbol;
    }
    if (info.locked_interval) {
      Array.from(tfSel.options).forEach((opt) => {
        if (opt.value !== info.locked_interval) opt.disabled = true;
      });
      tfSel.value = info.locked_interval;
    }
    updateDataInfo();
    return;
  }

  const supported = info.supported_combos || [];
  if (supported.length === 0) return;  // legacy preset — no gating
  const validSymbols = new Set(supported.map((c) => c[0]));
  // Disable symbols not in supported list
  Array.from(symSel.options).forEach((opt) => {
    if (!validSymbols.has(opt.value)) opt.disabled = true;
  });
  // If currently selected symbol is now disabled — switch to first valid
  if (symSel.options[symSel.selectedIndex] && symSel.options[symSel.selectedIndex].disabled) {
    const firstValid = Array.from(symSel.options).find((o) => !o.disabled);
    if (firstValid) symSel.value = firstValid.value;
  }
  // Disable TFs not valid for current symbol
  const tfsForSym = new Set(supported.filter((c) => c[0] === symSel.value).map((c) => c[1]));
  Array.from(tfSel.options).forEach((opt) => {
    if (!tfsForSym.has(opt.value)) opt.disabled = true;
  });
  if (tfSel.options[tfSel.selectedIndex] && tfSel.options[tfSel.selectedIndex].disabled) {
    const firstValidTf = Array.from(tfSel.options).find((o) => !o.disabled);
    if (firstValidTf) tfSel.value = firstValidTf.value;
  }
  updateDataInfo();
}

// ──────────────────────────────────────────────
//  BACKTEST SUBMIT
// ──────────────────────────────────────────────
async function handleSubmit(e) {
  e.preventDefault();
  const btn = $("run-btn");
  btn.disabled = true;
  btn.classList.add("btn-loading");
  btn.querySelector(".btn-text").textContent = "EXECUTING";
  btn.querySelector(".btn-meta").textContent = "running WFA";

  try {
    const data = new FormData($("backtest-form"));
    const payload = {
      strategy_id: data.get("strategy_id"),
      symbol: data.get("symbol"),
      interval: data.get("interval"),
      start: data.get("start"),
      end: data.get("end"),
      force: !!data.get("force"),
    };
    const resp = await fetch(API.backtest, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      let detail = err.detail || resp.statusText;
      if (Array.isArray(detail)) {
        detail = detail.map((d) => `${(d.loc || []).join(".")}: ${d.msg || d.type}`).join("\n");
      } else if (typeof detail === "object") {
        detail = JSON.stringify(detail, null, 2);
      }
      throw new Error(`HTTP ${resp.status}: ${detail}`);
    }
    const result = await resp.json();
    renderResult(result);
    loadHistory();
  } catch (err) {
    alert(`❌ Backtest error:\n${err.message}`);
  } finally {
    btn.disabled = false;
    btn.classList.remove("btn-loading");
    btn.querySelector(".btn-text").textContent = "▶ EXECUTE";
    btn.querySelector(".btn-meta").textContent = "~30-60s";
  }
}

// ──────────────────────────────────────────────
//  HELPERS
// ──────────────────────────────────────────────
function fmt(v, digits = 4) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(digits);
  return String(v);
}
function fmtPct(v, digits = 2) {
  if (v === null || v === undefined) return "—";
  return (v * 100).toFixed(digits) + "%";
}
function fmtMoney(v) {
  if (v === null || v === undefined) return "—";
  return Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ──────────────────────────────────────────────
//  RENDER BACKTEST RESULT
// ──────────────────────────────────────────────
function renderResult(r) {
  $("results-section").style.display = "block";

  const cachedTag = r.cached ? `<span class="cached-tag">CACHED</span>` : "";
  const req = r.request || {};
  const barsPerYear = r.bars_per_year ?? 0;
  $("run-meta").innerHTML = `
    <div class="meta-key">RUN_ID</div><div class="meta-val">${r.run_id ?? "—"}${cachedTag}</div>
    <div class="meta-key">STRATEGY</div><div class="meta-val">${req.strategy_label ?? req.strategy_id ?? "?"}</div>
    <div class="meta-key">SYMBOL · TF</div><div class="meta-val">${req.symbol ?? "?"} · ${req.interval_label ?? req.interval ?? "?"}</div>
    <div class="meta-key">RANGE</div><div class="meta-val">${req.start ?? "?"} → ${req.end ?? "?"} · ${barsPerYear.toLocaleString()} bars/year</div>
  `;

  const verdict = r.verdict ?? "—";
  const verdictCls = verdict === "PASS" ? "verdict-pass" : (verdict === "RAW" ? "verdict-raw" : "verdict-fail");
  const failedCriteria = r.failed_criteria ?? [];
  const failedHtml = failedCriteria.length
    ? `<div class="verdict-failed-list">FAILED CRITERIA: ${failedCriteria.map((c) => `<span class="chip">${c.toUpperCase()}</span>`).join(" ")}</div>`
    : "";
  $("verdict").innerHTML = `
    <div class="verdict-label">▸ FINAL VERDICT</div>
    <div class="verdict-value ${verdictCls}">${verdict}</div>
    ${failedHtml}
  `;

  const wPanel = $("warnings-panel");
  if (r.warnings && r.warnings.length) {
    wPanel.style.display = "block";
    const lvlClass = { high: "warn-high", warn: "warn-mid", info: "warn-info" };
    const icons = { high: "⚠", warn: "▲", info: "i" };
    $("warnings").innerHTML = r.warnings.map((w) => `
      <div class="warning ${lvlClass[w.level] || "warn-info"}">
        <div class="warning-icon">${icons[w.level] || "i"}</div>
        <div class="warning-content">
          <span class="warning-tag">[${w.level}] · ${w.code}</span>
          <div class="warning-message">${w.message}</div>
        </div>
      </div>
    `).join("");
  } else {
    wPanel.style.display = "none";
  }

  // T1-T6 + DSR + MC table
  const m = r.metrics || {};
  const ts = r.trade_stats || {};

  // S42.2 — RAW mode (research presets atr_breakout/volume_breakout): show envelope's actual values,
  // hide WFA-specific TIER 1-T6 + DSR + MC (deferred к S43 retrofit).
  if (r.verdict === "RAW") {
    const totalPnl = m.total_pnl_pct ?? r.total_pnl_pct;
    const sharpeVal = m.sharpe ?? r.sharpe;
    const nTr = m.n_trades ?? r.n_trades ?? 0;
    const winR = m.win_rate ?? r.win_rate;
    const nWin = (winR != null && nTr) ? Math.round(nTr * winR) : null;
    const nLos = (nWin != null) ? nTr - nWin : null;
    $("metrics-table").innerHTML = `
      <thead><tr><th>METRIC</th><th>VALUE</th><th>NOTE</th></tr></thead>
      <tbody>
        <tr><td>Total PnL</td><td class="${totalPnl > 0 ? "metric-pass" : "metric-fail"}"><strong>${fmt(totalPnl, 2)}%</strong></td><td>Full-period training (no WFA OOS split)</td></tr>
        <tr><td>Sharpe (annualized)</td><td class="${sharpeVal >= 1 ? "metric-pass" : "metric-warn"}">${fmt(sharpeVal, 4)}</td><td>per-trade Sharpe × √(bars/year ÷ mean_holding)</td></tr>
        <tr><td>Trade count (n)</td><td>${nTr}</td><td>Full-period (no train/test split)</td></tr>
        <tr><td>Win rate</td><td>${fmtPct(winR)}</td><td>—</td></tr>
        <tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding:var(--space-3);">▸ T1-T6 / DSR / MC acceptance gates skipped — see RAW_FULL_PERIOD warning above (WFA retrofit pending S43)</td></tr>
      </tbody>
    `;
    $("trades-table").innerHTML = `
      <thead><tr><th>STAT</th><th>VALUE</th></tr></thead>
      <tbody>
        <tr><td>Profitable trades</td><td class="metric-pass">${nWin ?? "—"}</td></tr>
        <tr><td>Losing trades</td><td class="metric-fail">${nLos ?? "—"}</td></tr>
        <tr><td>Win rate</td><td>${fmtPct(winR)}</td></tr>
        <tr><td>Total PnL %</td><td class="${totalPnl > 0 ? "metric-pass" : "metric-fail"}">${fmt(totalPnl, 2)}%</td></tr>
        <tr><td colspan="2" style="text-align:center;color:var(--text-muted);padding:var(--space-3);">▸ Quote-currency stats (USDT amounts, profit factor, avg win/loss) deferred к S43 WFA retrofit</td></tr>
      </tbody>
    `;
  } else {
    // Legacy WFA path (replay engine — ema_crossover / mean_reversion / donchian)
    const cellCls = (val, threshold, op = ">=") => {
      if (val === null || val === undefined) return "metric-fail";
      return op === ">=" ? (val >= threshold ? "metric-pass" : "metric-fail")
                         : (val < threshold ? "metric-pass" : "metric-fail");
    };
    const t1Cls = m.t1_sharpe_oos === null ? "metric-fail" : (m.t1_sharpe_oos > 3 ? "metric-warn" : (m.t1_sharpe_oos >= 1 ? "metric-pass" : "metric-fail"));
    const t1Status = m.t1_sharpe_oos === null || m.t1_sharpe_oos < 1 ? "FAIL" : (m.t1_sharpe_oos > 3 ? "OVERFIT?" : "PASS");
    $("metrics-table").innerHTML = `
      <thead><tr><th>METRIC</th><th>VALUE</th><th>THRESHOLD</th><th>STATUS</th></tr></thead>
      <tbody>
        <tr><td>T1 · Sharpe OOS (annualized)</td><td class="${t1Cls}">${fmt(m.t1_sharpe_oos, 2)}</td><td>≥ 1.0 (>3.0 = overfit)</td><td class="${t1Cls}">${t1Status}</td></tr>
        <tr><td>T2 · Sortino OOS</td><td class="${m.t2_sortino_anomaly_guard ? "metric-warn" : cellCls(m.t2_sortino_oos, 1.5)}">${m.t2_sortino_anomaly_guard ? "N/A" : fmt(m.t2_sortino_oos, 2)}</td><td>≥ 1.5</td><td class="${m.t2_sortino_anomaly_guard ? "metric-warn" : cellCls(m.t2_sortino_oos, 1.5)}">${m.t2_sortino_anomaly_guard ? "GUARD" : (m.t2_sortino_oos === null || m.t2_sortino_oos < 1.5 ? "FAIL" : "PASS")}</td></tr>
        <tr><td>T3 · Max Drawdown</td><td class="${cellCls(m.t3_max_drawdown, 0.25, "<")}">${fmtPct(m.t3_max_drawdown)}</td><td>&lt; 25%</td><td class="${cellCls(m.t3_max_drawdown, 0.25, "<")}">${m.t3_max_drawdown === null || m.t3_max_drawdown >= 0.25 ? "FAIL" : "PASS"}</td></tr>
        <tr><td>T4 · Win rate</td><td>${fmtPct(m.t4_win_rate)}</td><td>≥ 45%@RR≥1.5 OR ≥ 35%@RR≥2</td><td>—</td></tr>
        <tr><td>T4 · Avg RR</td><td>${fmt(m.t4_avg_rr, 2)}</td><td>—</td><td>—</td></tr>
        <tr><td><strong>T5 · Trade count (n)</strong></td><td class="${m.t5_n_trades < 100 ? "metric-fail" : "metric-pass"}"><strong>${m.t5_n_trades}</strong></td><td>≥ 100 (Bailey 2014)</td><td class="${m.t5_n_trades < 100 ? "metric-fail" : "metric-pass"}">${m.t5_n_trades < 100 ? "FAIL" : "PASS"}</td></tr>
        <tr><td>T5 · Mean PnL %</td><td>${fmtPct(m.t5_mean_pnl_pct, 4)}</td><td>&gt; 0</td><td class="${m.t5_mean_pnl_pct === null || m.t5_mean_pnl_pct <= 0 ? "metric-fail" : "metric-pass"}">${m.t5_mean_pnl_pct === null || m.t5_mean_pnl_pct <= 0 ? "FAIL" : "PASS"}</td></tr>
        <tr><td>T5 · t-stat</td><td class="${cellCls(m.t5_t_stat, 2.0)}">${fmt(m.t5_t_stat, 2)}</td><td>≥ 2.0</td><td class="${cellCls(m.t5_t_stat, 2.0)}">${m.t5_t_stat === null || m.t5_t_stat < 2 ? "FAIL" : "PASS"}</td></tr>
        <tr><td>T6 · OOS/IS Sharpe ratio mean</td><td class="${cellCls(m.t6_oos_is_sharpe_ratio_mean, 0.7)}">${fmt(m.t6_oos_is_sharpe_ratio_mean, 2)}</td><td>≥ 0.7 (overfit detector)</td><td class="${cellCls(m.t6_oos_is_sharpe_ratio_mean, 0.7)}">${m.t6_oos_is_sharpe_ratio_mean === null || m.t6_oos_is_sharpe_ratio_mean < 0.7 ? "FAIL" : "PASS"}</td></tr>
        <tr><td>DSR · Deflated Sharpe Ratio</td><td class="${r.dsr_pass ? "metric-pass" : "metric-fail"}">${fmt(r.dsr, 4)}</td><td>&gt; 0</td><td class="${r.dsr_pass ? "metric-pass" : "metric-fail"}">${r.dsr_pass ? "PASS" : "FAIL"}</td></tr>
        <tr><td>MC · p-value (sign-flip)</td><td class="${r.mc_p_value <= 0.05 ? "metric-pass" : (r.mc_p_value > 0.10 ? "metric-fail" : "metric-warn")}">${fmt(r.mc_p_value, 4)}</td><td>≤ 0.05</td><td class="${r.mc_p_value <= 0.05 ? "metric-pass" : "metric-fail"}">${r.mc_p_value <= 0.05 ? "PASS" : "FAIL"}</td></tr>
      </tbody>
    `;
    $("trades-table").innerHTML = `
      <thead><tr><th>STAT</th><th>VALUE</th></tr></thead>
      <tbody>
        <tr><td>Profitable trades</td><td class="metric-pass">${ts.n_winners}</td></tr>
        <tr><td>Losing trades</td><td class="metric-fail">${ts.n_losers}</td></tr>
        <tr><td>Win rate</td><td>${fmtPct(m.t4_win_rate)}</td></tr>
        <tr><td>Total PnL</td><td>${fmtMoney(ts.total_pnl_quote)} USDT</td></tr>
        <tr><td>Total Commissions</td><td>${fmtMoney(ts.total_commissions_quote)} USDT</td></tr>
        <tr><td>Avg Win</td><td>${fmtMoney(ts.avg_win_quote)} USDT</td></tr>
        <tr><td>Avg Loss</td><td>${fmtMoney(ts.avg_loss_quote)} USDT</td></tr>
        <tr><td>Profit Factor</td><td>${fmt(ts.profit_factor, 2)}</td></tr>
      </tbody>
    `;
  }

  // Per-fold table
  const folds = r.fold_sharpe_ratios || [];
  const failed = new Set(r.failed_folds || []);
  let foldHtml = `<thead><tr><th>FOLD</th><th>SHARPE RATIO</th><th>STATUS</th></tr></thead><tbody>`;
  folds.forEach((s, i) => {
    const cls = failed.has(i) ? "metric-fail" : (s >= 0.7 ? "metric-pass" : "metric-warn");
    foldHtml += `<tr><td>#${i}</td><td class="${cls}">${fmt(s, 4)}</td><td class="${cls}">${failed.has(i) ? "✗ < 0.7" : "✓"}</td></tr>`;
  });
  foldHtml += "</tbody>";
  $("folds-table").innerHTML = foldHtml;

  $("raw-json").textContent = JSON.stringify(r, null, 2);
  $("results-section").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ──────────────────────────────────────────────
//  HISTORY
// ──────────────────────────────────────────────
async function loadHistory() {
  const runs = await fetch(API.runs).then((r) => r.json());
  if (!runs.length) {
    $("history-table").innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:var(--space-6);">NO RUNS · execute first backtest above</td></tr>`;
    return;
  }
  let html = `<thead><tr><th>STRATEGY</th><th>SYMBOL</th><th>TF</th><th>RANGE</th><th>VERDICT</th><th>T1</th><th>T5 N</th><th>DSR</th><th>MC P</th></tr></thead><tbody>`;
  runs.forEach((r) => {
    const req = r.request || {};
    const m = r.metrics || {};
    const verdictCls = r.verdict === "PASS" ? "metric-pass" : "metric-fail";
    html += `<tr>
      <td>${(req.strategy_label || req.strategy_id || "").substring(0, 50)}</td>
      <td>${req.symbol || "—"}</td>
      <td>${req.interval_label || req.interval || "—"}</td>
      <td>${(req.start || "—").slice(0, 10)}…${(req.end || "—").slice(-5)}</td>
      <td class="${verdictCls}">${r.verdict || "—"}</td>
      <td>${fmt(m.t1_sharpe_oos, 2)}</td>
      <td class="${m.t5_n_trades < 100 ? "metric-fail" : "metric-pass"}">${m.t5_n_trades || "—"}</td>
      <td>${fmt(r.dsr, 3)}</td>
      <td>${fmt(r.mc_p_value, 3)}</td>
    </tr>`;
  });
  html += "</tbody>";
  $("history-table").innerHTML = html;
}

// ──────────────────────────────────────────────
//  DOCUMENTATION TAB
// ──────────────────────────────────────────────
async function loadDocs() {
  try {
    const docs = await fetch(API.docs).then((r) => r.json());
    renderIndicators(docs.indicators);
    renderMultipliers(docs.multipliers);
    renderStrategies(docs.strategies);
    renderMethodology(docs.methodology);
    docsLoaded = true;
  } catch (err) {
    console.error("Docs load error:", err);
  }
}

function renderIndicators(arr) {
  $("docs-indicators").innerHTML = arr.map((i) => `
    <article class="doc-card">
      <div class="doc-card-header">
        <div>
          <div class="doc-card-name">${i.name}</div>
          <div class="doc-card-fullname">${i.full_name}</div>
        </div>
        <div class="doc-card-category">${i.category}</div>
      </div>
      <div class="doc-card-author">${i.author}</div>
      <p>${i.description}</p>
      <div class="doc-card-formula">${escapeHtml(i.formula)}</div>
      <div class="doc-card-section">
        <h4>Range</h4>
        <p>${i.range}</p>
      </div>
      <div class="doc-card-section">
        <h4>Interpretation</h4>
        <ul>${i.interpretation.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
      </div>
      <div class="doc-card-section">
        <h4>Параметры в стратегиях</h4>
        <table class="doc-params-table">
          ${Object.entries(i.params_in_strategies).map(([k, v]) => `<tr><td>${k}</td><td>${escapeHtml(v)}</td></tr>`).join("")}
        </table>
      </div>
      <div class="doc-card-source">${i.source}</div>
    </article>
  `).join("");
}

function renderMultipliers(arr) {
  $("docs-multipliers").innerHTML = arr.map((m) => `
    <article class="doc-card">
      <div class="doc-card-header">
        <div>
          <div class="doc-card-name">${m.name}</div>
          <div class="doc-card-fullname"><code>${m.id}</code> · default = ${m.default}</div>
        </div>
      </div>
      <p>${m.description}</p>
      <div class="doc-card-section">
        <h4>Tradeoff</h4>
        <p style="font-style:italic;color:var(--text-muted);">${m.tradeoff}</p>
      </div>
    </article>
  `).join("");
}

function renderStrategies(arr) {
  $("docs-strategies").innerHTML = arr.map((s) => `
    <article class="strategy-card">
      <div class="strategy-main">
        <div class="strategy-category">${s.category}</div>
        <div class="strategy-name">${s.name}</div>
        <div class="strategy-tagline">${s.tagline}</div>
        <div class="strategy-section">
          <h5>Entry logic</h5>
          <p>${s.entry_logic}</p>
        </div>
        <div class="strategy-section">
          <h5>Exit logic</h5>
          <p>${s.exit_logic}</p>
        </div>
        <div class="strategy-section">
          <h5>Historical results</h5>
          <div class="strategy-historical">${s.historical_results}</div>
        </div>
        <div class="strategy-section">
          <h5>Best for</h5>
          <div class="strategy-best">${s.best_for}</div>
        </div>
      </div>
      <aside class="strategy-aside">
        <h5>Indicators used</h5>
        <div class="strategy-indicators">
          ${s.indicators_used.map((x) => `<span class="strategy-indicator-chip">${x}</span>`).join("")}
        </div>
        <h5>Key parameters</h5>
        <table class="doc-params-table">
          ${Object.entries(s.key_params).map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}
        </table>
        <div class="strategy-academic">${s.academic_reference}</div>
      </aside>
    </article>
  `).join("");
}

function renderMethodology(arr) {
  $("docs-methodology").innerHTML = arr.map((m) => {
    let body = `<p>${m.description || ""}</p>`;
    if (m.formula) body += `<div class="doc-card-formula">${escapeHtml(m.formula)}</div>`;
    if (m.params) body += `<div class="doc-card-section"><h4>Params</h4><p>${m.params}</p></div>`;
    if (m.interpretation) {
      body += `<div class="doc-card-section"><h4>Interpretation</h4><ul>${m.interpretation.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>`;
    }
    if (m.criteria) {
      body += `<div class="doc-card-section"><h4>Criteria</h4><table class="doc-params-table">`;
      m.criteria.forEach((c) => {
        body += `<tr><td><strong>${c.id}</strong> · ${c.metric}</td><td>${c.threshold}<br><span style="font-style:italic;color:var(--text-muted);font-size:10px;">${c.note}</span></td></tr>`;
      });
      body += `</table></div>`;
    }
    return `
      <article class="doc-card">
        <div class="doc-card-header">
          <div>
            <div class="doc-card-name">${m.name}</div>
            <div class="doc-card-fullname">${m.purpose}</div>
          </div>
        </div>
        ${body}
        <div class="doc-card-source">${m.source}</div>
      </article>
    `;
  }).join("");
}

function escapeHtml(s) {
  if (typeof s !== "string") return s;
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

init();
