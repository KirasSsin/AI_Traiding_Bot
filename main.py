import asyncio
import logging
import os
import threading
import http.server
import socketserver
from src.controller import TradingController

# Configure basic logging to terminal
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def start_ui_server():
    """Run a simple HTTP server in the background to serve the dashboard UI."""
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    os.chdir(web_dir) # Change working directory to serve the static files
    Handler = http.server.SimpleHTTPRequestHandler
    
    # Supress the default logging of SimpleHTTPRequestHandler
    class QuietHandler(Handler):
        def log_message(self, format, *args):
            pass
    # Allow quick restarts on the same port
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    preferred_port = int(os.environ.get("UI_PORT", "8000"))
    ports_to_try = [preferred_port, 8001, 8002, 8003]
    for port in ports_to_try:
        try:
            with ReusableTCPServer(("", port), QuietHandler) as httpd:
                logging.info(f"Web Dashboard is live! Open your browser to: http://localhost:{port}/dashboard.html")
                httpd.serve_forever()
            break
        except OSError as e:
            if port == ports_to_try[-1]:
                logging.error(f"Failed to start UI server on ports {ports_to_try}: {e}")
            else:
                logging.warning(f"Port {port} is in use, trying next port...")

async def main():
    print("="*60)
    print("AI TRADING BOT (Phase 1 Baseline - Bybit Edition)")
    print("="*60)
    
    # Start the web server in a background thread
    server_thread = threading.Thread(target=start_ui_server, daemon=True)
    server_thread.start()
    
    # These keys are automatically picked up from the user's instructions in README_RU.md
    API_KEY = "BaPkrSKaZBxVjqwBFM"
    API_SECRET = "ELq4mzNsA9xjUIqBM5k5nVdMUKI7gwzGyoou"
    CATEGORY = "linear"
    LIVE_TRADING = True
    DEMO_TRADING = True
    REST_POLL_INTERVAL = 1
    STARTUP_TEST_USD = 100.0
    
    if API_KEY == "PASTE_YOUR_API_KEY_HERE" or API_KEY == "":
        print("\n[WARNING]: API keys are not set. The bot will run, but cannot execute real testnet orders.")
        print("Please edit main.py to add your Bybit Testnet keys.\n")
    
    # Configure the Bot Instance
    controller = TradingController(
        symbol="BTCUSDT",
        interval="1",         # Bybit uses '1' for 1 minute
        initial_capital=100000.0,
        api_key=API_KEY,
        api_secret=API_SECRET,
        testnet=True,         # True = safety on (Testnet), False = REAL MONEY
        category=CATEGORY,
        live_trading=LIVE_TRADING,
        demo=DEMO_TRADING,
        rest_poll_interval_seconds=REST_POLL_INTERVAL,
        startup_test_usd=STARTUP_TEST_USD,
    )
    
    # Start the Event Loop
    try:
        await controller.start()
    except asyncio.CancelledError:
        print("Safely shutting down all tasks...")

if __name__ == "__main__":
    try:
        # For Windows/Mac compatibility with aiohttp
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[i] User pressed Ctrl+C. Bot shut down safely.")
