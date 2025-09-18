from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import asyncio
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
import os
from typing import Optional

app = FastAPI(title="TradingView to Binance Bot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingViewSignal(BaseModel):
    action: str  # "buy" or "sell"
    symbol: str  # e.g., "BTCUSDT"
    quantity: Optional[float] = None
    price: Optional[float] = None
    order_type: str = "market"  # "market" or "limit"

class BinanceTrader:
    def __init__(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

        # Initialize client only if credentials are provided
        if self.api_key and self.api_secret:
            self.client = Client(self.api_key, self.api_secret, testnet=True)
        else:
            self.client = None
            logger.warning("Binance API credentials not found - trading disabled")

    async def execute_trade(self, signal: TradingViewSignal):
        try:
            if signal.action.lower() == "buy":
                if signal.order_type == "market":
                    if signal.quantity:
                        order = self.client.order_market_buy(
                            symbol=signal.symbol,
                            quantity=signal.quantity
                        )
                    else:
                        raise ValueError("Quantity required for buy orders")
                else:  # limit order
                    order = self.client.order_limit_buy(
                        symbol=signal.symbol,
                        quantity=signal.quantity,
                        price=str(signal.price)
                    )

            elif signal.action.lower() == "sell":
                if signal.order_type == "market":
                    if signal.quantity:
                        order = self.client.order_market_sell(
                            symbol=signal.symbol,
                            quantity=signal.quantity
                        )
                    else:
                        raise ValueError("Quantity required for sell orders")
                else:  # limit order
                    order = self.client.order_limit_sell(
                        symbol=signal.symbol,
                        quantity=signal.quantity,
                        price=str(signal.price)
                    )
            else:
                raise ValueError(f"Invalid action: {signal.action}")

            logger.info(f"Order executed: {order}")
            return order

        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            raise HTTPException(status_code=400, detail=f"Binance API error: {e}")
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            raise HTTPException(status_code=500, detail=f"Trade execution error: {e}")

trader = BinanceTrader()

@app.post("/webhook")
async def receive_tradingview_signal(signal: TradingViewSignal):
    try:
        logger.info(f"Received signal: {signal}")

        # If no Binance credentials, just log the signal
        if not trader.client:
            return {
                "status": "success",
                "message": "Signal received (trading disabled - no API credentials)",
                "signal": signal.dict()
            }

        # Execute the trade
        order_result = await trader.execute_trade(signal)

        return {
            "status": "success",
            "message": "Trade executed successfully",
            "order": order_result
        }

    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "TradingView to Binance Bot is running"}

@app.get("/account")
async def get_account_info():
    try:
        account = trader.client.get_account()
        return {
            "balances": [
                {"asset": balance["asset"], "free": balance["free"], "locked": balance["locked"]}
                for balance in account["balances"]
                if float(balance["free"]) > 0 or float(balance["locked"]) > 0
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)