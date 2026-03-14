import asyncio
import logging
from src.execution.executor import BybitExecutor
from src.core.models import Signal

# Setting up basic logging to see exactly what happens
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_execution():
    print("="*50)
    print("Running Bybit API Execution Test...")
    print("="*50)
    
    # User's provided keys
    api_key = "zRZIO4RDDgOQMmb4D4"
    api_secret = "qtWIPIAOGK0ugvoev0u660jVBLQ1s540HS32"
    
    # Initializing executor in TESTNET mode
    executor = BybitExecutor(
        api_key,
        api_secret,
        testnet=True,
        live_trading=False,
        category="linear",
        demo=True,
    )
    await executor.start()
    
    # 1. Test fetching Account Balance
    balance = await executor.fetch_balance()
    print(f"\n[STEP 1]: Current Account Balance (Unified) = ${balance:.2f}\n")
    
    # 2. Test Real Order Execution
    # We will buy 0.001 BTCUSDT Market (Testnet)
    print("[STEP 2]: Firing Market BUY Order for 0.001 BTCUSDT\n")
    
    # Create an artificial signal
    test_signal = Signal(
        symbol="BTCUSDT",
        timestamp=0,     # Not used for execution
        direction="BUY", 
        entry_price=0,   # Market order doesn't need exact price here
        expected_sl=0,
        expected_tp=0
    )
    
    # Fire the actual execution method on the mocked/base class
    # Right now, evaluate what the executor does. It should create a mock order or real one depending on the code.
    # To truly test REAL execution, we would uncomment the V5 HTTP Request in executor.py.
    # For now, it will use the mock path, which proves the Python integration logic holds up.
    
    order = await executor.execute_signal(test_signal, quantity=0.001, category="linear")
    print("\n[RESULT]:")
    print(order)
    
    await executor.stop()

if __name__ == "__main__":
    asyncio.run(test_execution())
