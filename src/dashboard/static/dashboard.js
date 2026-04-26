// S25 ADR 0039 — dashboard frontend (vanilla JS, no framework).
"use strict";

const API = {
  strategies: "/api/strategies",
  intervals: "/api/intervals",
  availability: "/api/data/availability",
  backtest: "/api/backtest",
  runs: "/api/runs",
};

const els = {
  strategySelect: document.getElementById("strategy-select"),
  symbolSelect: document.getElementById("symbol-select"),
  intervalSelect: document.getElementById("interval-select"),
  form: document.getElementById("backtest-form"),
  runBtn: document.getElementById("run-btn"),
  dataInfo: document.getElementById("data-info"),
  resultsSection: document.getElementById("results-section"),
  runMeta: document.getElementById("run-meta"),
  warnings: document.getElementById("warnings"),
  verdict: document.getElementById("verdict"),
  metricsTable: document.getElementById("metrics-table"),
  tradesTable: document.getElementById("trades-table"),
  foldsTable: document.getElementById("folds-table"),
  rawJson: document.getElementById("raw-json"),
  historyTable: document.getElementById("history-table"),
  refreshHistory: document.getElementById("refresh-history"),
};

let availability = {};

async function init() {
  const [strategies, intervals, avail] = await Promise.all([
    fetch(API.strategies).then(r => r.json()),
    fetch(API.intervals).then(r => r.json()),
    fetch(API.availability).then(r => r.json()),
  ]);
  availability = avail;

  // Populate strategy dropdown
  for (const sid in strategies) {
    const opt = document.createElement("option");
    opt.value = sid;
    opt.textContent = strategies[sid].label;
    els.strategySelect.appendChild(opt);
  }

  // Populate symbol dropdown (from availability)
  for (const sym of Object.keys(availability).sort()) {
    const opt = document.createElement("option");
    opt.value = sym;
    opt.textContent = sym;
    els.symbolSelect.appendChild(opt);
  }

  // Populate interval dropdown
  for (const iv of intervals) {
    const opt = document.createElement("option");
    opt.value = iv.id;
    opt.textContent = iv.label;
    els.intervalSelect.appendChild(opt);
  }

  els.symbolSelect.addEventListener("change", updateDataInfo);
  els.intervalSelect.addEventListener("change", updateDataInfo);
  updateDataInfo();

  els.form.addEventListener("submit", handleSubmit);
  els.refreshHistory.addEventListener("click", loadHistory);
  loadHistory();
}

function updateDataInfo() {
  const sym = els.symbolSelect.value;
  const iv = els.intervalSelect.value;
  const symData = availability[sym] || {};
  const ivData = symData[iv];
  if (!ivData) {
    els.dataInfo.innerHTML = `<span class="warn">⚠ Нет данных для ${sym} ${iv}. Запусти backfill: <code>python -m src backfill --symbol ${sym} --interval ${iv} --from 2023-01-01 --to 2026-04-26</code></span>`;
    return;
  }
  els.dataInfo.innerHTML = `<span class="ok">✓ Данные доступны: ${ivData.bars.toLocaleString()} баров, ${ivData.start.slice(0,10)} → ${ivData.end.slice(0,10)}</span>`;
}

async function handleSubmit(e) {
  e.preventDefault();
  els.runBtn.disabled = true;
  els.runBtn.textContent = "⏳ Запуск backtest (~30-60s)...";
  try {
    const data = new FormData(els.form);
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
      throw new Error(err.detail || resp.statusText);
    }
    const result = await resp.json();
    renderResult(result);
    loadHistory();
  } catch (err) {
    alert(`❌ Ошибка backtest:\n${err.message}`);
  } finally {
    els.runBtn.disabled = false;
    els.runBtn.textContent = "▶ Запустить backtest";
  }
}

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

function renderResult(r) {
  els.resultsSection.style.display = "block";

  // Meta
  const cached = r.cached ? " <span class=\"info\">(cached)</span>" : "";
  els.runMeta.innerHTML = `
    <p><strong>Run ID:</strong> ${r.run_id}${cached}</p>
    <p><strong>Strategy:</strong> ${r.request.strategy_label}</p>
    <p><strong>Symbol/TF:</strong> ${r.request.symbol} ${r.request.interval_label} | <strong>Range:</strong> ${r.request.start} → ${r.request.end} | <strong>bars/year:</strong> ${r.bars_per_year.toLocaleString()}</p>
  `;

  // Warnings
  els.warnings.innerHTML = "";
  if (r.warnings && r.warnings.length) {
    const lvlClass = { high: "warn-high", warn: "warn-mid", info: "warn-info" };
    r.warnings.forEach(w => {
      const div = document.createElement("div");
      div.className = "warning " + (lvlClass[w.level] || "warn-info");
      div.innerHTML = `<strong>[${w.level.toUpperCase()}]</strong> ${w.message}`;
      els.warnings.appendChild(div);
    });
  }

  // Verdict
  const verdictClass = r.verdict === "PASS" ? "verdict-pass" : "verdict-fail";
  els.verdict.innerHTML = `
    <h3 class="${verdictClass}">VERDICT: ${r.verdict}</h3>
    ${r.failed_criteria.length ? `<p>Failed: <code>${r.failed_criteria.join(", ")}</code></p>` : ""}
  `;

  // Metrics T1-T6
  const m = r.metrics;
  const acceptanceColor = (val, threshold, op = ">=") => {
    if (val === null || val === undefined) return "metric-fail";
    const passed = op === ">=" ? val >= threshold : val < threshold;
    return passed ? "metric-pass" : "metric-fail";
  };
  const t1Class = m.t1_sharpe_oos === null ? "metric-fail" : (m.t1_sharpe_oos > 3 ? "metric-warn" : (m.t1_sharpe_oos >= 1 ? "metric-pass" : "metric-fail"));
  els.metricsTable.innerHTML = `
    <tr><th>Метрика</th><th>Значение</th><th>Threshold</th><th>Status</th></tr>
    <tr><td>T1 Sharpe OOS (annualized)</td><td class="${t1Class}">${fmt(m.t1_sharpe_oos, 2)}</td><td>≥ 1.0 (>3.0 = overfit warn)</td><td>${m.t1_sharpe_oos === null || m.t1_sharpe_oos < 1 ? "❌" : (m.t1_sharpe_oos > 3 ? "⚠" : "✅")}</td></tr>
    <tr><td>T2 Sortino OOS</td><td class="${m.t2_sortino_anomaly_guard ? 'metric-warn' : acceptanceColor(m.t2_sortino_oos, 1.5)}">${m.t2_sortino_anomaly_guard ? "N/A (anomaly guard)" : fmt(m.t2_sortino_oos, 2)}</td><td>≥ 1.5 (or N/A if Sortino>50 + n<100)</td><td>${m.t2_sortino_anomaly_guard ? "⚠" : (m.t2_sortino_oos === null || m.t2_sortino_oos < 1.5 ? "❌" : "✅")}</td></tr>
    <tr><td>T3 Max Drawdown</td><td class="${acceptanceColor(m.t3_max_drawdown, 0.25, "<")}">${fmtPct(m.t3_max_drawdown)}</td><td>< 25%</td><td>${m.t3_max_drawdown === null || m.t3_max_drawdown >= 0.25 ? "❌" : "✅"}</td></tr>
    <tr><td>T4 Win Rate</td><td>${fmtPct(m.t4_win_rate)}</td><td>≥45%@RR≥1.5 OR ≥35%@RR≥2.0</td><td></td></tr>
    <tr><td>T4 Avg RR</td><td>${fmt(m.t4_avg_rr, 2)}</td><td>—</td><td></td></tr>
    <tr><td><strong>T5 Trade count (n)</strong></td><td class="${m.t5_n_trades < 100 ? 'metric-fail' : 'metric-pass'}"><strong>${m.t5_n_trades}</strong></td><td>≥ 100 (Bailey 2014 t-test minimum)</td><td>${m.t5_n_trades < 100 ? "❌" : "✅"}</td></tr>
    <tr><td>T5 Mean PnL %</td><td>${fmtPct(m.t5_mean_pnl_pct, 4)}</td><td>> 0</td><td>${m.t5_mean_pnl_pct === null || m.t5_mean_pnl_pct <= 0 ? "❌" : "✅"}</td></tr>
    <tr><td>T5 t-stat</td><td class="${acceptanceColor(m.t5_t_stat, 2.0)}">${fmt(m.t5_t_stat, 2)}</td><td>≥ 2.0</td><td>${m.t5_t_stat === null || m.t5_t_stat < 2 ? "❌" : "✅"}</td></tr>
    <tr><td>T6 OOS/IS Sharpe ratio mean</td><td class="${acceptanceColor(m.t6_oos_is_sharpe_ratio_mean, 0.7)}">${fmt(m.t6_oos_is_sharpe_ratio_mean, 2)}</td><td>≥ 0.7 (overfit detector)</td><td>${m.t6_oos_is_sharpe_ratio_mean === null || m.t6_oos_is_sharpe_ratio_mean < 0.7 ? "❌" : "✅"}</td></tr>
    <tr><td>DSR (Deflated Sharpe Ratio)</td><td class="${r.dsr_pass ? 'metric-pass' : 'metric-fail'}">${fmt(r.dsr, 4)}</td><td>> 0</td><td>${r.dsr_pass ? "✅" : "❌"}</td></tr>
    <tr><td>MC p-value (sign-flip permutation)</td><td class="${r.mc_p_value <= 0.05 ? 'metric-pass' : (r.mc_p_value > 0.10 ? 'metric-fail' : 'metric-warn')}">${fmt(r.mc_p_value, 4)}</td><td>≤ 0.05 (>0.10 noise warn)</td><td>${r.mc_p_value <= 0.05 ? "✅" : "❌"}</td></tr>
  `;

  // Trade-level stats
  const ts = r.trade_stats;
  els.tradesTable.innerHTML = `
    <tr><th>Stat</th><th>Value</th></tr>
    <tr><td>Profitable trades</td><td>${ts.n_winners}</td></tr>
    <tr><td>Losing trades</td><td>${ts.n_losers}</td></tr>
    <tr><td>Win rate</td><td>${fmtPct(m.t4_win_rate)}</td></tr>
    <tr><td>Total PnL (quote)</td><td>${fmtMoney(ts.total_pnl_quote)} USDT</td></tr>
    <tr><td>Total Commissions</td><td>${fmtMoney(ts.total_commissions_quote)} USDT</td></tr>
    <tr><td>Avg Win (quote)</td><td>${fmtMoney(ts.avg_win_quote)} USDT</td></tr>
    <tr><td>Avg Loss (quote)</td><td>${fmtMoney(ts.avg_loss_quote)} USDT</td></tr>
    <tr><td>Profit Factor (gross profit / gross loss)</td><td>${fmt(ts.profit_factor, 2)}</td></tr>
  `;

  // Per-fold table
  const folds = r.fold_sharpe_ratios || [];
  const failed = new Set(r.failed_folds || []);
  let foldHtml = `<tr><th>Fold #</th><th>Sharpe ratio</th><th>Status</th></tr>`;
  folds.forEach((s, i) => {
    const cls = failed.has(i) ? "metric-fail" : (s >= 0.7 ? "metric-pass" : "metric-warn");
    foldHtml += `<tr><td>${i}</td><td class="${cls}">${fmt(s, 4)}</td><td>${failed.has(i) ? "❌ < 0.7" : "✅"}</td></tr>`;
  });
  els.foldsTable.innerHTML = foldHtml;

  // Raw JSON
  els.rawJson.textContent = JSON.stringify(r, null, 2);

  // Scroll к results
  els.resultsSection.scrollIntoView({ behavior: "smooth" });
}

async function loadHistory() {
  const runs = await fetch(API.runs).then(r => r.json());
  if (!runs.length) {
    els.historyTable.innerHTML = `<tr><td>Нет запусков. Запусти первый backtest выше.</td></tr>`;
    return;
  }
  let html = `<tr><th>Strategy</th><th>Symbol</th><th>TF</th><th>Range</th><th>Verdict</th><th>T1</th><th>T5 n</th><th>DSR</th><th>MC p</th><th>Warnings</th></tr>`;
  runs.forEach(r => {
    const req = r.request || {};
    const m = r.metrics || {};
    const verdictCls = r.verdict === "PASS" ? "metric-pass" : "metric-fail";
    html += `<tr>
      <td>${req.strategy_label || req.strategy_id}</td>
      <td>${req.symbol}</td>
      <td>${req.interval_label || req.interval}</td>
      <td>${req.start}..${req.end}</td>
      <td class="${verdictCls}">${r.verdict}</td>
      <td>${fmt(m.t1_sharpe_oos, 2)}</td>
      <td class="${m.t5_n_trades < 100 ? 'metric-fail' : 'metric-pass'}">${m.t5_n_trades}</td>
      <td>${fmt(r.dsr, 3)}</td>
      <td>${fmt(r.mc_p_value, 3)}</td>
      <td>${r.warnings_count > 0 ? "⚠ " + r.warnings_count : "—"}</td>
    </tr>`;
  });
  els.historyTable.innerHTML = html;
}

init().catch(err => alert("Init error: " + err.message));
