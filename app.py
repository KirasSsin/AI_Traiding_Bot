import copy
import os
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.backtest.data_collector import load_market_data
from src.backtest.replay_engine import run_replay
from src.backtest.reporter import write_artifacts
from src.config_loader import load_config

st.set_page_config(
    page_title="AI Trading Bot — бэктест",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    div[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    .block-container { padding-top: 1.25rem; }
    .formula-card {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(2, 6, 23, 0.86));
        border: 1px solid rgba(56, 189, 248, 0.28);
        border-radius: 12px;
        padding: 0.4rem 0.75rem 0.5rem 0.75rem;
        margin: 0.15rem 0 0.45rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("AI Trading Bot")
st.caption("MVP Backtester — симуляция на исторических OHLCV с учётом комиссий и проскальзывания")

# --- Session keys for calculation parameters (prefixed bt_) ---
_BT_KEYS = (
    "bt_initial_balance",
    "bt_commission_taker",
    "bt_slippage",
    "bt_position_size_pct",
    "bt_max_drawdown_pct",
    "bt_ema_fast",
    "bt_ema_slow",
    "bt_rsi_period",
    "bt_rsi_overbought",
    "bt_rsi_oversold",
    "bt_atr_period",
    "bt_sl_atr_mult",
    "bt_tp_atr_mult",
)


def _seed_bt_params_from_config(cfg: Dict[str, Any]) -> None:
    """Fill bt_* session keys from YAML config (when data is loaded)."""
    t = cfg.get("trading", {})
    ema = cfg.get("strategy", {}).get("indicators", {}).get("ema", {})
    rsi = cfg.get("strategy", {}).get("indicators", {}).get("rsi", {})
    atr = cfg.get("strategy", {}).get("indicators", {}).get("atr", {})
    st.session_state["bt_initial_balance"] = float(t.get("initial_balance", 10000.0))
    st.session_state["bt_commission_taker"] = float(t.get("commission_taker", 0.001))
    st.session_state["bt_slippage"] = float(t.get("slippage", 0.0005))
    st.session_state["bt_position_size_pct"] = float(t.get("position_size_pct", 10.0))
    st.session_state["bt_max_drawdown_pct"] = float(t.get("max_drawdown_pct", 20.0))
    st.session_state["bt_ema_fast"] = int(ema.get("fast_period", 12))
    st.session_state["bt_ema_slow"] = int(ema.get("slow_period", 26))
    st.session_state["bt_rsi_period"] = int(rsi.get("period", 14))
    st.session_state["bt_rsi_overbought"] = float(rsi.get("overbought", 70))
    st.session_state["bt_rsi_oversold"] = float(rsi.get("oversold", 30))
    st.session_state["bt_atr_period"] = int(atr.get("period", 14))
    st.session_state["bt_sl_atr_mult"] = float(atr.get("sl_atr_mult", 1.5))
    st.session_state["bt_tp_atr_mult"] = float(atr.get("tp_atr_mult", 3.0))


def _build_working_config(template: Dict[str, Any]) -> Dict[str, Any]:
    """Merge bt_* widget values into a deep copy of the loaded config."""
    c = copy.deepcopy(template)
    c.setdefault("trading", {})
    c.setdefault("strategy", {}).setdefault("indicators", {})
    c["strategy"]["indicators"].setdefault("ema", {})
    c["strategy"]["indicators"].setdefault("rsi", {})
    c["strategy"]["indicators"].setdefault("atr", {})

    c["trading"]["initial_balance"] = float(st.session_state["bt_initial_balance"])
    c["trading"]["commission_taker"] = float(st.session_state["bt_commission_taker"])
    c["trading"]["slippage"] = float(st.session_state["bt_slippage"])
    c["trading"]["position_size_pct"] = float(st.session_state["bt_position_size_pct"])
    c["trading"]["max_drawdown_pct"] = float(st.session_state["bt_max_drawdown_pct"])

    c["strategy"]["indicators"]["ema"]["fast_period"] = int(st.session_state["bt_ema_fast"])
    c["strategy"]["indicators"]["ema"]["slow_period"] = int(st.session_state["bt_ema_slow"])
    c["strategy"]["indicators"]["rsi"]["period"] = int(st.session_state["bt_rsi_period"])
    c["strategy"]["indicators"]["rsi"]["overbought"] = float(st.session_state["bt_rsi_overbought"])
    c["strategy"]["indicators"]["rsi"]["oversold"] = float(st.session_state["bt_rsi_oversold"])
    c["strategy"]["indicators"]["atr"]["period"] = int(st.session_state["bt_atr_period"])
    c["strategy"]["indicators"]["atr"]["sl_atr_mult"] = float(st.session_state["bt_sl_atr_mult"])
    c["strategy"]["indicators"]["atr"]["tp_atr_mult"] = float(st.session_state["bt_tp_atr_mult"])
    return c


def _config_sidebar_preview(cfg: Dict[str, Any]) -> None:
    data = cfg.get("data", {})
    trading = cfg.get("trading", {})
    strat = cfg.get("strategy", {}).get("indicators", {})
    ema = strat.get("ema", {})
    with st.expander("Краткий обзор конфигурации (файл)", expanded=False):
        c1, c2 = st.columns(2)
        c1.markdown(
            f"**Символ:** `{data.get('symbol', '—')}`  \n"
            f"**Таймфрейм:** `{data.get('timeframe', '—')}`  \n"
            f"**Источник:** `{data.get('source', '—')}`"
        )
        c2.markdown(
            f"**Период:** `{data.get('start_date', '—')}` — `{data.get('end_date', '—')}`  \n"
            f"**CSV:** `{data.get('csv_path', '—')}`  \n"
            f"**Parquet:** `{data.get('parquet_path', '—')}`"
        )
        st.markdown(
            f"**Капитал (файл):** `{trading.get('initial_balance', '—')}`  "
            f"· **EMA:** `{ema.get('fast_period', '?')}` / `{ema.get('slow_period', '?')}`"
        )


def _metric_value(metrics: Dict[str, Any], key: str):
    v = metrics.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_equity_figure(equity_df: pd.DataFrame, trades_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Кривая капитала", "Чистый PnL по сделкам"),
        vertical_spacing=0.1,
        row_heights=[0.58, 0.42],
    )
    if not equity_df.empty:
        fig.add_trace(
            go.Scatter(
                x=equity_df["timestamp"],
                y=equity_df["balance"],
                mode="lines",
                name="Баланс",
                line=dict(color="#38bdf8", width=2),
            ),
            row=1,
            col=1,
        )
    if not trades_df.empty and "timestamp_close" in trades_df.columns:
        colors = trades_df["net_pnl"].apply(
            lambda x: "#22c55e" if float(x) > 0 else "#ef4444" if float(x) < 0 else "#94a3b8"
        )
        fig.add_trace(
            go.Bar(
                x=trades_df["timestamp_close"],
                y=trades_df["net_pnl"],
                name="PnL",
                marker_color=colors,
            ),
            row=2,
            col=1,
        )
    fig.update_layout(
        height=720,
        margin=dict(l=40, r=24, t=48, b=40),
        paper_bgcolor="rgba(15,23,42,0)",
        plot_bgcolor="rgba(2,6,23,0.4)",
        font=dict(color="#e2e8f0"),
        showlegend=False,
        title=dict(text="Результаты бэктеста (текущие параметры)", x=0.02, xanchor="left"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.15)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.15)")
    return fig


def _number_input_with_formula(
    *,
    label: str,
    key: str,
    description: str,
    formula_latex: Optional[str] = None,
    formula_copy: Optional[str] = None,
    **kwargs: Any,
) -> None:
    title_col, help_col = st.columns([0.92, 0.08], gap="small")
    title_col.markdown(f"**{label}**")

    open_state_key = f"{key}__formula_open"
    if help_col.button("?", key=f"{key}__formula_btn", help="Показать или скрыть пояснение"):
        st.session_state[open_state_key] = not st.session_state.get(open_state_key, False)

    if st.session_state.get(open_state_key, False):
        st.markdown('<div class="formula-card">', unsafe_allow_html=True)
        st.caption(description)
        if formula_latex:
            st.latex(formula_latex)
        if formula_copy:
            st.code(formula_copy, language="text")
            st.caption("Формулу можно скопировать кнопкой в правом верхнем углу блока.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.number_input(label, key=key, label_visibility="collapsed", **kwargs)


def _render_param_panel() -> None:
    """All inputs that `replay_engine.run_replay` reads from config."""
    st.subheader("Параметры расчёта")
    st.caption(
        "Эти значения напрямую участвуют в `replay_engine`: торговые допущения, EMA/RSI/ATR. "
        "Изменение любого поля пересчитывает кривую и метрики."
    )

    tab_t, tab_i = st.tabs(["Торговля и риск", "Индикаторы (EMA / RSI / ATR)"])

    with tab_t:
        c1, c2, c3 = st.columns(3)
        with c1:
            _number_input_with_formula(
                label="Начальный баланс",
                key="bt_initial_balance",
                min_value=100.0,
                max_value=10_000_000.0,
                step=100.0,
                description=(
                    "Стартовый капитал для бэктеста. От него считаются размер позиции, "
                    "кривая капитала, доходность и просадка."
                ),
                formula_latex=r"Equity_{0} = InitialBalance",
                formula_copy="Equity_0 = initial_balance",
            )
        with c2:
            _number_input_with_formula(
                label="Комиссия taker",
                key="bt_commission_taker",
                min_value=0.0,
                max_value=0.05,
                step=0.0001,
                format="%.4f",
                description=(
                    "Комиссия биржи за рыночное исполнение. В бэктесте списывается "
                    "и на входе, и на выходе."
                ),
                formula_latex=r"Fee = Price \times Qty \times Commission_{taker}",
                formula_copy="fee = price * qty * commission_taker",
            )
        with c3:
            _number_input_with_formula(
                label="Slippage",
                key="bt_slippage",
                min_value=0.0,
                max_value=0.05,
                step=0.0001,
                format="%.4f",
                description=(
                    "Модель рыночного проскальзывания: цена входа/выхода становится "
                    "хуже на указанную долю."
                ),
                formula_latex=(
                    r"P_{entry}^{buy}=P_{open}\times(1+slippage),\ "
                    r"P_{exit}^{buy}=P\times(1-slippage)"
                ),
                formula_copy=(
                    "entry_buy = open_price * (1 + slippage)\n"
                    "exit_buy = price * (1 - slippage)"
                ),
            )
        c4, c5 = st.columns(2)
        with c4:
            _number_input_with_formula(
                label="Размер позиции, % капитала",
                key="bt_position_size_pct",
                min_value=0.1,
                max_value=100.0,
                step=0.5,
                description=(
                    "Доля капитала, выделяемая на одну сделку. Увеличение параметра "
                    "повышает и прибыль, и риск."
                ),
                formula_latex=(
                    r"Spend = Equity \times \frac{PositionSizePct}{100},\ "
                    r"Qty = \frac{Spend}{EntryPrice}"
                ),
                formula_copy=(
                    "spend = equity * (position_size_pct / 100)\n"
                    "qty = spend / entry_price"
                ),
            )
        with c5:
            _number_input_with_formula(
                label="Kill-switch: max просадка, %",
                key="bt_max_drawdown_pct",
                min_value=1.0,
                max_value=99.0,
                step=0.5,
                description=(
                    "Аварийный стоп стратегии. Когда просадка от исторического пика "
                    "капитала превышает порог, новые сделки блокируются."
                ),
                formula_latex=(
                    r"Drawdown=\frac{HWM-Equity}{HWM},\ "
                    r"Stop\ if\ Drawdown \ge \frac{MaxDD}{100}"
                ),
                formula_copy=(
                    "drawdown = (high_water_mark - equity) / high_water_mark\n"
                    "if drawdown >= max_drawdown_pct / 100: stop_trading = True"
                ),
            )

    with tab_i:
        st.markdown("**EMA** — пересечение fast/slow задаёт сигнал входа.")
        e1, e2 = st.columns(2)
        with e1:
            _number_input_with_formula(
                label="EMA fast period",
                key="bt_ema_fast",
                min_value=2,
                max_value=120,
                step=1,
                description=(
                    "Период быстрой EMA. Чем меньше значение, тем быстрее реакция "
                    "на новое движение цены."
                ),
                formula_latex=r"EMA_t=Price_t\cdot\alpha+EMA_{t-1}\cdot(1-\alpha),\ \alpha=\frac{2}{n+1}",
                formula_copy=(
                    "alpha = 2 / (period + 1)\n"
                    "ema_t = price_t * alpha + ema_prev * (1 - alpha)"
                ),
            )
        with e2:
            _number_input_with_formula(
                label="EMA slow period",
                key="bt_ema_slow",
                min_value=2,
                max_value=200,
                step=1,
                description=(
                    "Период медленной EMA. Больший период лучше сглаживает шум и "
                    "описывает долгосрочный тренд."
                ),
                formula_latex=r"EMA_t=Price_t\cdot\alpha+EMA_{t-1}\cdot(1-\alpha),\ \alpha=\frac{2}{n+1}",
                formula_copy=(
                    "alpha = 2 / (period + 1)\n"
                    "ema_t = price_t * alpha + ema_prev * (1 - alpha)"
                ),
            )

        st.markdown("**RSI** — фильтр входа (перекупленность / перепроданность).")
        r1, r2, r3 = st.columns(3)
        with r1:
            _number_input_with_formula(
                label="RSI period",
                key="bt_rsi_period",
                min_value=2,
                max_value=50,
                step=1,
                description=(
                    "Период RSI. Меньший период делает индикатор более нервным, "
                    "больший — более плавным."
                ),
                formula_latex=r"RSI = 100 - \frac{100}{1+RS},\ RS=\frac{AvgGain_n}{AvgLoss_n}",
                formula_copy=(
                    "RS = average_gain(period) / average_loss(period)\n"
                    "RSI = 100 - 100 / (1 + RS)"
                ),
            )
        with r2:
            _number_input_with_formula(
                label="Overbought",
                key="bt_rsi_overbought",
                min_value=50.0,
                max_value=95.0,
                step=1.0,
                description=(
                    "Верхний порог RSI. Если RSI выше него, стратегия не открывает "
                    "лонг (фильтр перекупленности)."
                ),
                formula_latex=r"Long\ entry\ allowed\ iff\ RSI < Overbought",
                formula_copy="allow_long = (rsi < overbought)",
            )
        with r3:
            _number_input_with_formula(
                label="Oversold",
                key="bt_rsi_oversold",
                min_value=5.0,
                max_value=50.0,
                step=1.0,
                description=(
                    "Нижний порог RSI. В полной двусторонней версии используется как "
                    "фильтр перепроданности для short-логики."
                ),
                formula_latex=r"Short\ entry\ allowed\ iff\ RSI > Oversold",
                formula_copy="allow_short = (rsi > oversold)",
            )

        st.markdown("**ATR** — волатильность для SL/TP.")
        a1, a2, a3 = st.columns(3)
        with a1:
            _number_input_with_formula(
                label="ATR period",
                key="bt_atr_period",
                min_value=2,
                max_value=50,
                step=1,
                description="Период ATR — базовая оценка текущей волатильности рынка.",
                formula_latex=(
                    r"TR_t=\max(H_t-L_t,\ |H_t-C_{t-1}|,\ |L_t-C_{t-1}|),\ "
                    r"ATR_t=EMA_n(TR_t)"
                ),
                formula_copy=(
                    "true_range = max(high-low, abs(high-prev_close), abs(low-prev_close))\n"
                    "atr = ema(true_range, period)"
                ),
            )
        with a2:
            _number_input_with_formula(
                label="SL × ATR",
                key="bt_sl_atr_mult",
                min_value=0.1,
                max_value=10.0,
                step=0.1,
                description="Множитель ATR для стоп-лосса позиции.",
                formula_latex=r"SL_{long}=EntryPrice-(SL_{mult}\times ATR)",
                formula_copy="stop_loss = entry_price - sl_atr_mult * atr",
            )
        with a3:
            _number_input_with_formula(
                label="TP × ATR",
                key="bt_tp_atr_mult",
                min_value=0.1,
                max_value=20.0,
                step=0.1,
                description="Множитель ATR для тейк-профита позиции.",
                formula_latex=r"TP_{long}=EntryPrice+(TP_{mult}\times ATR)",
                formula_copy="take_profit = entry_price + tp_atr_mult * atr",
            )

    if int(st.session_state.get("bt_ema_fast", 0)) >= int(st.session_state.get("bt_ema_slow", 1)):
        st.warning("Обычно fast EMA < slow EMA; иначе сигналы могут вести себя нестандартно.")


# --- Sidebar ---
config_path = st.sidebar.text_input("Путь к config", value="config.yaml")

try:
    config = load_config(config_path)
except Exception as exc:
    st.error(f"Ошибка конфигурации: {exc}")
    st.stop()

_config_sidebar_preview(config)

run = st.sidebar.button("Загрузить данные и запустить", type="primary", use_container_width=True)

if run:
    with st.spinner("Загрузка OHLCV…"):
        df = load_market_data(config)
        if df.empty:
            st.error("Нет данных. Проверьте `data.source`, `csv_path` / `parquet_path` и диапазон дат в config.yaml.")
            st.stop()
        st.session_state["backtest_cache"] = {
            "config_path": os.path.abspath(config_path),
            "market_df": df,
            "cfg_template": copy.deepcopy(config),
        }
        _seed_bt_params_from_config(config)
        st.session_state["artifacts_last"] = None

cache = st.session_state.get("backtest_cache")
if cache is None or cache.get("config_path") != os.path.abspath(config_path):
    st.info(
        "Нажмите **«Загрузить данные и запустить»** в боковой панели: "
        "будут прочитаны CSV и параметры из YAML; затем можно менять расчёт ниже."
    )
    st.stop()

cfg_template = cache["cfg_template"]
market_df = cache["market_df"]

if not all(k in st.session_state for k in _BT_KEYS):
    _seed_bt_params_from_config(cfg_template)

_render_param_panel()

working_cfg = _build_working_config(cfg_template)
with st.spinner("Пересчёт бэктеста…"):
    replay = run_replay(market_df, working_cfg)

metrics = replay["metrics"]
m_total = _metric_value(metrics, "Total Return (%)")
m_dd = _metric_value(metrics, "Max Drawdown (%)")
m_sharpe = _metric_value(metrics, "Sharpe Ratio")
m_wr = _metric_value(metrics, "Win Rate (%)")
m_pf = _metric_value(metrics, "Profit Factor")
m_nt = _metric_value(metrics, "Total Trades")
m_gp = _metric_value(metrics, "Gross Profit")
m_gl = _metric_value(metrics, "Gross Loss")

st.subheader("Ключевые показатели")
r1, r2, r3, r4, r5, r6 = st.columns(6)
r1.metric("Доходность (%)", f"{m_total:.2f}" if m_total is not None else "—")
r2.metric("Max просадка (%)", f"{m_dd:.2f}" if m_dd is not None else "—")
r3.metric("Sharpe", f"{m_sharpe:.3f}" if m_sharpe is not None else "—")
r4.metric("Win rate (%)", f"{m_wr:.2f}" if m_wr is not None else "—")
r5.metric("Profit factor", f"{m_pf:.3f}" if m_pf is not None else "—")
r6.metric("Сделок", f"{int(m_nt)}" if m_nt is not None else "—")
r7, r8 = st.columns(2)
r7.metric("Gross profit", f"{m_gp:.2f}" if m_gp is not None else "—")
r8.metric("Gross loss", f"{m_gl:.2f}" if m_gl is not None else "—")

with st.expander("Все метрики расчёта (JSON)", expanded=False):
    st.json(metrics)

st.subheader("Графики")
fig = _build_equity_figure(replay["equity_df"], replay["trades_df"])
st.plotly_chart(fig, use_container_width=True)

st.subheader("Сделки")
trades_df = replay["trades_df"]
if trades_df.empty:
    st.warning("За выбранный период сделок нет.")
else:
    fdir = st.selectbox(
        "Фильтр по направлению",
        options=["Все", "BUY", "SELL"],
        index=0,
    )
    show = trades_df
    if fdir != "Все":
        show = trades_df[trades_df["direction"] == fdir]
    st.dataframe(show, use_container_width=True, height=min(420, 40 + len(show) * 36))

st.subheader("Экспорт в `output/`")
st.caption(
    "Файлы на диске не обновляются при каждом движении слайдера — только по кнопке "
    "(текущие параметры из панели выше)."
)
col_a, col_b = st.columns(2)
with col_a:
    if st.button("Сохранить отчёт с текущими параметрами", use_container_width=True):
        paths = write_artifacts(
            working_cfg,
            replay["equity_df"],
            replay["trades_df"],
            replay["metrics"],
        )
        st.session_state["artifacts_last"] = paths
        st.success("Сохранено.")
with col_b:
    if st.button("Сбросить параметры к значениям из YAML", use_container_width=True):
        _seed_bt_params_from_config(cfg_template)
        st.rerun()

if st.session_state.get("artifacts_last"):
    st.markdown("**Последние сохранённые файлы:**")
    for name, path in st.session_state["artifacts_last"].items():
        st.markdown(f"- **{name}** — `{path}`")

out_dir = (config.get("output") or {}).get("directory", "output")
st.caption(f"Каталог по умолчанию: `{os.path.abspath(out_dir)}`")
