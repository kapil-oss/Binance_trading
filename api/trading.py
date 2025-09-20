import json
from fastapi import APIRouter, Request
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_USE_TESTNET
from database import store_signal, store_execution

router = APIRouter()

class BinanceTrader:
    def __init__(self):
        self.client = None
        if BINANCE_API_KEY and BINANCE_API_SECRET:
            self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=BINANCE_USE_TESTNET)

    async def execute_trade(self, signal_data):
        """Execute trade on Binance based on signal data"""
        if not self.client:
            return {"error": "Binance client not initialized"}

        try:
            action = signal_data.get("action").lower()
            symbol = signal_data.get("symbol")
            quantity = signal_data.get("quantity")

            # Convert symbol if needed (remove .P suffix for futures)
            if symbol.endswith('.P'):
                symbol = symbol[:-2]

            side = "BUY" if action == "buy" else "SELL"

            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=quantity,
                # recvWindow=60000 // for time sychronization issue
            )

            return {"success": True, "order": order}

        except BinanceAPIException as e:
            return {"error": f"Binance API error: {str(e)}"}
        except Exception as e:
            return {"error": f"Trade execution error: {str(e)}"}

# Global trader instance
trader = BinanceTrader()

@router.post("/webhook")
async def receive_signal(request: Request):
    """Receive TradingView webhook signals"""
    try:
        data = await request.json()

        # Execute trade FIRST for speed
        if data and trader.client:
            execution_result = await trader.execute_trade(data)

            # Store execution result
            if execution_result.get("success"):
                store_execution(
                    data.get("action", ""),
                    data.get("symbol", ""),
                    data.get("quantity", ""),
                    "success",
                    execution_result.get("order", {}).get("orderId")
                )
            else:
                store_execution(
                    data.get("action", ""),
                    data.get("symbol", ""),
                    data.get("quantity", ""),
                    "failed",
                    execution_result.get("error")
                )

            # Store signal AFTER execution
            store_signal(
                data.get("action", ""),
                data.get("symbol", ""),
                data.get("quantity", ""),
                data.get("price", ""),
                data.get("time", "")
            )

            return {
                "status": "success",
                "message": "Trade executed",
                "result": execution_result
            }

        # Store signal if no trading
        store_signal(
            data.get("action", ""),
            data.get("symbol", ""),
            data.get("quantity", ""),
            data.get("price", ""),
            data.get("time", "")
        )

        return {"status": "success", "message": "Signal received"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "TradingView Webhook Receiver is running"}