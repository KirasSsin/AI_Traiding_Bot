import asyncio
import logging
import pandas as pd
import json
import os
from typing import Optional
from datetime import datetime

from src.core.models import Kline, Signal
from src.data.consumer import BybitDataConsumer
from src.strategy.strategy import AdvancedStrategy
from src.risk.risk_manager import RiskManager
from src.execution.executor import BybitExecutor

logger = logging.getLogger(__name__)

class TradingController:
    """
    The orchestrator. Wires up all independent modules.
    Runs the main event loop and dumps state to JSON for Web UI.
    """
    def __init__(
        self,
        symbol: str,
        interval: str,
        initial_capital: float,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        category: str = "linear",
        live_trading: bool = False,
        demo: bool = False,
        rest_poll_interval_seconds: int = 2,
        startup_test_usd: float = 0.0,
    ):
        self.symbol = symbol
        self.interval = interval
        
        # Initialize modules
        self.consumer = BybitDataConsumer(
            symbol,
            interval,
            testnet=testnet,
            category=category,
            demo=demo,
            rest_poll_interval_seconds=rest_poll_interval_seconds,
        )
        self.strategy = AdvancedStrategy(symbol) # Now using Advanced strategy
        self.risk_manager = RiskManager(initial_capital)
        self.executor = BybitExecutor(
            api_key,
            api_secret,
            testnet=testnet,
            live_trading=live_trading,
            category=category,
            demo=demo,
        )
        self._last_signal_ts: Optional[int] = None
        self._startup_test_usd = startup_test_usd
        self._execution_history: list[dict] = []
        self._execution_sync_task: Optional[asyncio.Task] = None
        self._history_limit = 50
        
        self.consumer.register_callback(self.on_new_kline)
        self._running = False
        
        self.last_kline: Optional[Kline] = None
        self.dashboard_data_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'data.json')
        os.makedirs(os.path.dirname(self.dashboard_data_path), exist_ok=True)

    async def start(self):
        """Start all async components."""
        self._running = True
        logger.info(f"Starting Trading Bot for {self.symbol}...")
        
        await self.executor.start()
        
        # Synchronize live balance from Bybit V5
        live_balance = await self.executor.fetch_balance()
        if live_balance > 0:
            logger.info(f"Syncing Risk Manager to live Bybit equity: ${live_balance:.2f}")
            self.risk_manager.initial_capital = live_balance
            self.risk_manager.current_capital = live_balance
            self.risk_manager.high_water_mark = live_balance
        else:
            logger.warning(f"Could not sync live balance. Falling back to configured initial capital: ${self.risk_manager.initial_capital:.2f}")

        await self._sync_execution_history()
        self._execution_sync_task = asyncio.create_task(self._sync_execution_history_loop())

        if self._startup_test_usd > 0:
            await self._run_startup_test_trade()
        
        self.consumer_task = asyncio.create_task(self.consumer.start())
        self.ui_task = asyncio.create_task(self._update_ui_state_loop())
        
        try:
             while self._running:
                 await asyncio.sleep(1) 
        except asyncio.CancelledError:
             logger.info("Controller loop cancelled.")
        finally:
             await self.stop()

    async def stop(self):
         """Graceful shutdown."""
         self._running = False
         await self.consumer.stop()
         if hasattr(self, 'consumer_task'):
             self.consumer_task.cancel()
         if hasattr(self, 'ui_task'):
             self.ui_task.cancel()
         if self._execution_sync_task:
             self._execution_sync_task.cancel()
         await self.executor.stop()
         logger.info("Bot stopped.")

    async def _run_startup_test_trade(self):
        try:
            price, qty = await self.executor.get_qty_for_usdt(
                self.executor.category,
                self.symbol,
                self._startup_test_usd,
            )
            buy_signal = Signal(
                symbol=self.symbol,
                direction="BUY",
                entry_price=price,
                expected_sl=None,
                expected_tp=None,
            )
            await self.executor.execute_signal(buy_signal, qty)
            await asyncio.sleep(1)
            sell_signal = Signal(
                symbol=self.symbol,
                direction="SELL",
                entry_price=price,
                expected_sl=None,
                expected_tp=None,
            )
            await self.executor.execute_signal(sell_signal, qty)
            logger.info(f"Startup test trade complete for ${self._startup_test_usd:.2f}")
        except Exception as e:
            logger.error(f"Startup test trade failed: {e}")

    async def _sync_execution_history_loop(self):
        while self._running:
            try:
                await self._sync_execution_history()
            except Exception as e:
                logger.error(f"Execution history sync failed: {e}")
            await asyncio.sleep(60)

    async def _sync_execution_history(self):
        api_executions = await self.executor.fetch_execution_history(
            category=self.executor.category,
            symbol=self.symbol,
            limit=self._history_limit,
        )
        merged = self._merge_executions(api_executions, self.executor.execution_log)
        if merged:
            self._execution_history = merged[:self._history_limit]

    def on_new_kline(self, kline: Kline):
        """Callback fired by the Data Consumer."""
        self.last_kline = kline
        buffer = self.consumer.get_historical_buffer()
        if not buffer:
            return
        if not kline.is_closed:
            return
        if self._last_signal_ts == kline.timestamp:
            return
        self._last_signal_ts = kline.timestamp
            
        data = [{
            'timestamp': k.timestamp, 'open': k.open, 'high': k.high,
            'low': k.low, 'close': k.close, 'volume': k.volume
        } for k in buffer]
            
        df = pd.DataFrame(data)
        signal: Optional[Signal] = self.strategy.on_kline(df, kline.close)
        
        if signal and self.risk_manager.evaluate_signal(signal):
            size = self.risk_manager.calculate_position_size(signal)
            asyncio.create_task(self.executor.execute_signal(signal, size))

    async def _update_ui_state_loop(self):
        """Periodic task to write bot state to a JSON file for the HTML dashboard."""
        while self._running:
            try:
                state = {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": self.symbol,
                    "interval": self.interval,
                    "status": "RUNNING" if self._running else "STOPPED",
                    "capital": {
                        "initial": self.risk_manager.initial_capital,
                        "current": self.risk_manager.current_capital,
                        "high_water_mark": self.risk_manager.high_water_mark,
                        "kill_switch": self.risk_manager.is_kill_switch_active
                    },
                    "market": {
                        "current_price": self.last_kline.close if self.last_kline else 0.0,
                        "is_closed": self.last_kline.is_closed if self.last_kline else False,
                        "data_source": self.consumer.data_source,
                        "last_update_ts": self.consumer.last_update_ts,
                        "last_rest_poll_ts": self.consumer.last_rest_poll_ts,
                        "last_ws_message_ts": self.consumer.last_ws_message_ts,
                        "last_rest_message_ts": self.consumer.last_rest_message_ts,
                    },
                    "active_orders": [
                        {
                            "id": o.client_order_id,
                            "direction": o.direction,
                            "price": o.price,
                            "qty": o.quantity,
                            "status": o.status
                        } for o in self.executor.active_orders.values()
                    ],
                    "executions": self._execution_history,
                }
                
                with open(self.dashboard_data_path, 'w') as f:
                    json.dump(state, f, indent=4)
                    
            except Exception as e:
                logger.error(f"Error updating UI state: {e}")
                
            await asyncio.sleep(1) # Update dashboard every 1 second

    def _merge_executions(self, api_execs: list[dict], local_execs: list):
        merged: list[dict] = []
        seen: set[str] = set()

        def add_exec(e: dict):
            exec_id = e.get("id") or f"{e.get('direction')}-{e.get('timestamp')}-{e.get('price')}-{e.get('qty')}"
            if exec_id in seen:
                return
            seen.add(exec_id)
            merged.append(e)

        for e in api_execs or []:
            add_exec(e)

        for o in local_execs or []:
            add_exec({
                "id": o.client_order_id,
                "direction": o.direction,
                "price": o.price,
                "qty": o.quantity,
                "status": o.status,
                "timestamp": o.timestamp,
                "source": "LOCAL",
            })

        merged.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return merged
