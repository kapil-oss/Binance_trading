"""Trading API module for TradingView webhook integration with Binance."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Request
from binance_client import Client, BinanceAPIException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_USE_TESTNET
from database import (
    Execution,
    SessionLocal,
    get_db,
    get_or_create_preference,
    store_execution,
    store_signal,
)

router = APIRouter()


class ExecutionRecord(BaseModel):
    """Pydantic model for execution record API responses."""
    class Config:
        orm_mode = True

    id: int
    timestamp: datetime
    execution_time: Optional[datetime] = None
    action: Optional[str] = None
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    status: Optional[str] = None
    order_id: Optional[str] = None

    # Timing fields
    signal_sent_time: Optional[datetime] = None
    received_time: Optional[datetime] = None
    processed_time: Optional[datetime] = None
    sent_to_binance_time: Optional[datetime] = None
    binance_executed_time: Optional[datetime] = None

    # Computed property for frontend timing display
    @property
    def timing(self) -> Optional[dict]:
        """Return timing information for frontend display."""
        if any([self.signal_sent_time, self.received_time, self.processed_time,
                self.sent_to_binance_time, self.binance_executed_time]):
            return {
                'signal_sent': (
                    self.signal_sent_time.isoformat()
                    if self.signal_sent_time else None
                ),
                'received': self.received_time.isoformat() if self.received_time else None,
                'processed': self.processed_time.isoformat() if self.processed_time else None,
                'sent_to_binance': (
                    self.sent_to_binance_time.isoformat()
                    if self.sent_to_binance_time else None
                ),
                'executed': (
                    self.binance_executed_time.isoformat()
                    if self.binance_executed_time else None
                )
            }
        return None


class BinanceTrader:
    """Handles Binance trading operations and account management."""

    def __init__(self):
        self.client = None
        if BINANCE_API_KEY and BINANCE_API_SECRET:
            print(f"🔧 BINANCE CLIENT: Initializing with testnet={BINANCE_USE_TESTNET}")
            self.client = Client(
                BINANCE_API_KEY,
                BINANCE_API_SECRET,
                testnet=BINANCE_USE_TESTNET,
            )
            print("✅ BINANCE CLIENT: Successfully initialized")
        else:
            print("❌ BINANCE CLIENT: Missing API credentials")


    async def execute_trade(self, signal_data, preference=None, reference_price=None):
        """Execute trade on Binance based on signal data and user preferences."""
        if not self.client:
            return {"error": "Binance client not initialized"}

        try:
            # Validate and process signal data
            validation_result = self._validate_signal_data(signal_data)
            if "error" in validation_result:
                return validation_result

            action, symbol, base_quantity = (
                validation_result["action"],
                validation_result["symbol"],
                validation_result["base_quantity"]
            )

            # Handle leverage settings
            preference_data = preference if isinstance(preference, dict) else {}
            leverage_result = self._apply_leverage(symbol, preference_data)
            if "error" in leverage_result:
                return leverage_result
            applied_leverage = leverage_result.get("applied_leverage")

            # Calculate final quantity
            quantity_result = self._calculate_quantity(
                base_quantity, preference_data, reference_price, signal_data, symbol
            )
            if "error" in quantity_result:
                return quantity_result
            applied_quantity, percent_value = (
                quantity_result["quantity"],
                quantity_result.get("percent_value")
            )

            # Update signal data
            signal_data.update({
                "symbol": symbol,
                "quantity": applied_quantity
            })
            if applied_leverage is not None:
                signal_data["applied_leverage"] = applied_leverage
            if percent_value is not None:
                signal_data["applied_capital_percent"] = percent_value

            # Execute order
            return self._execute_order(
                symbol, action, applied_quantity, applied_leverage, percent_value
            )

        except BinanceAPIException as exc:
            return {"error": f"Binance API error: {exc}"}
        except Exception as exc:  # pylint: disable=broad-except
            return {"error": f"Trade execution error: {exc}"}

    def _validate_signal_data(self, signal_data):
        """Validate and process signal data."""
        action_raw = signal_data.get("action")
        if not action_raw:
            return {"error": "Missing action"}
        action = action_raw.lower()

        symbol_raw = signal_data.get("symbol") or ""
        symbol = symbol_raw.replace("BINANCE:", "")
        if symbol.endswith(".P"):
            symbol = symbol[:-2]

        quantity_raw = signal_data.get("quantity")
        try:
            base_quantity = abs(float(quantity_raw))
        except (TypeError, ValueError):
            return {"error": f"Invalid quantity: {quantity_raw}"}

        return {
            "action": action,
            "symbol": symbol,
            "base_quantity": base_quantity
        }

    def _apply_leverage(self, symbol, preference_data):
        """Apply leverage settings if specified."""
        leverage_value = preference_data.get("leverage")
        if leverage_value is None:
            return {}

        try:
            leverage_numeric = float(leverage_value)
        except (TypeError, ValueError):
            return {}

        if not leverage_numeric:
            return {}

        leverage_int = max(1, min(125, int(round(leverage_numeric))))
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage_int)
            return {"applied_leverage": leverage_int}
        except BinanceAPIException as exc:
            return {"error": f"Failed to set leverage: {exc}"}

    def _calculate_quantity(
        self, base_quantity, preference_data, reference_price, signal_data, symbol
    ):
        """Calculate final trading quantity based on preferences."""
        capital_percent = preference_data.get("capital_allocation_percent")

        # Get price for sizing
        price_for_sizing = reference_price
        if price_for_sizing is None:
            price_hint = signal_data.get("price")
            try:
                price_for_sizing = float(price_hint) if price_hint else None
            except (TypeError, ValueError):
                price_for_sizing = None

        applied_quantity = base_quantity
        percent_value = None

        if capital_percent is not None:
            try:
                percent_value = max(0.0, float(capital_percent))
            except (TypeError, ValueError):
                percent_value = None

        # Calculate quantity based on capital allocation
        if percent_value and percent_value > 0:
            quantity_calc_result = self._calculate_quantity_from_capital(
                percent_value, base_quantity, price_for_sizing, symbol
            )
            if "error" in quantity_calc_result:
                return quantity_calc_result
            calculated_quantity = quantity_calc_result["quantity"]

            # Use whichever is larger: webhook quantity or calculated quantity
            applied_quantity = max(base_quantity, calculated_quantity)
            print(f"💰 QUANTITY CHOICE: base={base_quantity}, calculated={calculated_quantity}, using={applied_quantity}")

        # Apply precision and validate
        precision_result = self._apply_quantity_precision(applied_quantity, symbol)
        if "error" in precision_result:
            return precision_result

        return {
            "quantity": precision_result["quantity"],
            "percent_value": percent_value
        }

    def _calculate_quantity_from_capital(
        self, percent_value, base_quantity, price_for_sizing, symbol
    ):
        """Calculate quantity based on capital allocation percentage."""
        summary, summary_error = self.get_account_summary()
        available_balance = None

        if not summary_error and summary:
            available_balance = summary.get("available_balance")

        if price_for_sizing is None:
            try:
                ticker = self.client.futures_symbol_ticker(symbol=symbol)
                price_for_sizing = float(ticker.get("price"))
            except Exception:  # pylint: disable=broad-except
                price_for_sizing = None

        if available_balance is not None and price_for_sizing:
            computed_quantity = (
                (float(available_balance) * (percent_value / 100.0)) / price_for_sizing
            )
            if computed_quantity > 0:
                return {"quantity": computed_quantity}

        return {"quantity": base_quantity * (percent_value / 100.0)}

    def _apply_quantity_precision(self, quantity, symbol):
        """Apply symbol-specific precision to quantity using proper step size."""
        # Expanded symbol step sizes for major trading pairs
        symbol_step_sizes = {
            # BTC pairs
            "BTCUSDT": "0.001",
            "BTCUSD": "0.001",
            "BTCBUSD": "0.001",
            "BTCFDUSD": "0.001",

            # ETH pairs
            "ETHUSDT": "0.0001",
            "ETHUSD": "0.0001",
            "ETHBUSD": "0.0001",
            "ETHBTC": "0.00001",

            # Major altcoins
            "ADAUSDT": "1",
            "BNBUSDT": "0.001",
            "SOLUSDT": "0.001",
            "XRPUSDT": "0.1",
            "DOGEUSDT": "1",
            "AVAXUSDT": "0.01",
            "LINKUSDT": "0.01",
            "DOTUSDT": "0.01",
            "UNIUSDT": "0.01",
            "LTCUSDT": "0.001",
            "BCHUSDT": "0.001",
            "FILUSDT": "0.01",
            "TRXUSDT": "1",
            "EOSUSDT": "0.1",
            "XLMUSDT": "1",
            "XMRUSDT": "0.001",
            "ETCUSDT": "0.01",
            "VETUSDT": "1",
            "ICPUSDT": "0.01",
            "FTMUSDT": "1",
            "HBARUSDT": "1",
            "NEARUSDT": "0.01",
            "ATOMUSDT": "0.01",
            "ALGOUSDT": "1",
            "MATICUSDT": "1",
            "SANDUSDT": "1",
            "MANAUSDT": "1",

            # Popular futures symbols
            "1000PEPEUSDT": "1000",
            "1000SHIBUSDT": "1000",
            "1000FLOKIUSDT": "1000",
        }

        symbol_for_precision = symbol.upper().replace('.P', '')
        step_size = symbol_step_sizes.get(symbol_for_precision)

        # If symbol not found, try to get step size dynamically from Binance
        if step_size is None:
            try:
                step_size = self._get_dynamic_step_size(symbol_for_precision)
            except Exception:
                # Fallback to conservative default
                step_size = "0.001"

        # Convert to Decimal for precise calculations
        quantity_decimal = Decimal(str(quantity))
        step_size_decimal = Decimal(step_size)

        print(f"🔢 QUANTITY PRECISION: symbol={symbol}, quantity={quantity}, step_size={step_size}")
        print(f"🔢 DECIMALS: quantity_decimal={quantity_decimal}, step_size_decimal={step_size_decimal}")

        # Round down to nearest valid step size multiple
        applied_quantity = (quantity_decimal // step_size_decimal) * step_size_decimal

        print(f"🔢 APPLIED QUANTITY: {applied_quantity}")

        if applied_quantity <= 0:
            print(f"❌ QUANTITY ERROR: Applied quantity {applied_quantity} is zero or negative")
            return {"error": "Calculated quantity is zero"}

        # Format as string with appropriate decimal places for Binance API
        decimal_places = max(0, -step_size_decimal.as_tuple().exponent)
        quantity_str = f"{applied_quantity:.{decimal_places}f}"

        return {"quantity": float(applied_quantity), "quantity_str": quantity_str}

    def _execute_order(self, symbol, action, quantity, applied_leverage=None, percent_value=None):
        """Execute the actual order on Binance."""
        side = "BUY" if action == "buy" else "SELL"

        # Get precision-adjusted quantity
        precision_result = self._apply_quantity_precision(quantity, symbol)
        if "error" in precision_result:
            return {"error": precision_result["error"]}

        # Use string quantity for better Binance API compatibility
        quantity_for_order = precision_result.get("quantity_str", str(precision_result["quantity"]))

        order = self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity_for_order,  # Use string quantity
        )

        result = {"success": True, "order": order}
        if applied_leverage is not None:
            result["applied_leverage"] = applied_leverage
        if percent_value is not None:
            result["applied_capital_percent"] = percent_value
        return result

    def _get_dynamic_step_size(self, symbol):
        """Get step size dynamically from Binance exchange info."""
        if not self.client:
            return "0.001"  # Default fallback

        try:
            exchange_info = self.client.futures_exchange_info()
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info['symbol'] == symbol:
                    for filter_info in symbol_info.get('filters', []):
                        if filter_info['filterType'] == 'LOT_SIZE':
                            return filter_info['stepSize']
        except Exception as exc:
            # Log error but don't fail the trade
            print(f"Failed to get dynamic step size for {symbol}: {exc}")

        return "0.001"  # Conservative default

    def get_account_summary(self):
        """Return key futures account balances for display."""
        if not self.client:
            return None, "Binance client not initialized"

        try:
            account_info = self.client.futures_account()
            balances = self.client.futures_account_balance()

            def _to_float(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None

            asset_balance = next(
                (entry for entry in balances if entry.get("asset") == "USDT"), None
            )
            available_balance = (
                _to_float(asset_balance.get("availableBalance"))
                if asset_balance else None
            )
            wallet_balance = _to_float(asset_balance.get("balance")) if asset_balance else None
            cross_wallet_balance = (
                _to_float(asset_balance.get("crossWalletBalance"))
                if asset_balance else None
            )

            summary = {
                "asset": asset_balance.get("asset") if asset_balance else None,
                "available_balance": available_balance,
                "wallet_balance": wallet_balance,
                "cross_wallet_balance": cross_wallet_balance,
                "total_wallet_balance": _to_float(account_info.get("totalWalletBalance")),
                "total_unrealized_profit": _to_float(account_info.get("totalUnrealizedProfit")),
                "total_margin_balance": _to_float(account_info.get("totalMarginBalance")),
                "update_time": account_info.get("updateTime"),
            }
            return summary, None
        except BinanceAPIException as exc:
            return None, f"Binance API error: {exc}"
        except Exception as exc:  # pylint: disable=broad-except
            return None, f"Failed to fetch account summary: {exc}"




# Global trader instance
trader = BinanceTrader()


def _load_preference_data():
    """Fetch stored preference values as a plain dictionary."""
    session = SessionLocal()
    try:
        preference = get_or_create_preference(session)
        if not preference:
            return None, "No strategy preferences configured"
        return {
            "product": preference.product,
            "strategy": preference.strategy,
            "direction_mode": preference.direction_mode,
            "leverage": preference.leverage,
            "capital_allocation_percent": preference.capital_allocation_percent,
        }, None
    except Exception as exc:  # pylint: disable=broad-except
        return None, f"Failed to load strategy preference: {exc}"
    finally:
        session.close()


def _strategy_allows_execution(signal_strategy: Optional[str]):
    """Return (is_allowed, reason, preference_dict)."""
    preference_data, load_error = _load_preference_data()
    if load_error:
        return False, load_error, preference_data

    selected_strategy = (preference_data.get("strategy") or "").strip()
    incoming = (signal_strategy or "").strip()

    if not selected_strategy:
        return False, "No strategy selected in control panel", preference_data
    if not incoming:
        return False, "Signal missing strategy value", preference_data
    if incoming.lower() != selected_strategy.lower():
        selected_label = selected_strategy or "--"
        incoming_label = incoming or "--"
        return (
            False,
            f"Strategy mismatch (selected {selected_label}, signal {incoming_label})",
            preference_data
        )
    return True, None, preference_data


def _direction_allows_action(action: Optional[str], preference: Optional[dict]):
    """Validate that the alert action is compatible with direction settings."""
    if not preference:
        return True, None

    direction_mode = (preference.get("direction_mode") or "").lower()
    if not direction_mode or direction_mode == "allow_long_short":
        return True, None

    if not action:
        return False, "Signal missing action value"

    action_value = action.lower()
    if direction_mode == "allow_long_only" and action_value != "buy":
        return False, "Blocked short signal: long-only mode enabled"
    if direction_mode == "allow_short_only" and action_value != "sell":
        return False, "Blocked long signal: short-only mode enabled"
    return True, None




def _normalise_symbol(symbol: Optional[str]) -> str:
    if not symbol:
        return ""
    cleaned = symbol.strip().upper()
    if ':' in cleaned:
        cleaned = cleaned.split(':', 1)[1]
    if '.' in cleaned:
        cleaned = cleaned.split('.', 1)[0]
    cleaned = cleaned.replace('_', '')
    for suffix in ("USDT", "USD", "PERP", "USDC"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            break
    base = ''.join(ch for ch in cleaned if ch.isalpha())
    return base


def _product_allows_symbol(symbol: Optional[str], preference: Optional[dict]):
    if not preference:
        return True, None
    selected_product = (preference.get("product") or "").strip()
    if not selected_product:
        return True, None
    incoming_base = _normalise_symbol(symbol)
    if not incoming_base:
        return False, "Signal missing tradable symbol"
    if incoming_base.lower() != selected_product.lower():
        return False, f"Product mismatch (selected {selected_product}, signal {incoming_base})"
    return True, None


def _initialize_timing_data():
    """Initialize timing data structure."""
    return {
        'signal_sent': None,
        'received': datetime.now(),
        'processed': None,
        'sent_to_binance': None,
        'executed': None
    }


def _extract_signal_time(data, timing_data):
    """Extract signal sent time from TradingView data."""
    if data.get("time"):
        try:
            utc_time = datetime.fromisoformat(data.get("time").replace('Z', '+00:00'))
            timing_data['signal_sent'] = utc_time.replace(tzinfo=None)
        except Exception:  # pylint: disable=broad-except
            pass


def _validate_signal_permissions(data):
    """Validate signal permissions and extract relevant data."""
    signal_strategy = data.get("strategy")
    strategy_allowed, strategy_reason, preference = _strategy_allows_execution(signal_strategy)
    direction_allowed, direction_reason = _direction_allows_action(data.get("action"), preference)
    product_allowed, product_reason = _product_allows_symbol(data.get("symbol"), preference)

    price_value = data.get("price")
    try:
        clean_price = float(price_value)
    except (TypeError, ValueError):
        clean_price = None

    try:
        clean_quantity = float(data.get("quantity"))
    except (TypeError, ValueError):
        clean_quantity = None

    allow_execution = (
        bool(data) and trader.client and strategy_allowed
        and direction_allowed and product_allowed
    )

    ignore_messages = [
        message for message in (strategy_reason, direction_reason, product_reason)
        if message
    ]
    ignore_message = "; ".join(ignore_messages) if ignore_messages else None

    return {
        "allow_execution": allow_execution,
        "ignore_message": ignore_message,
        "preference": preference,
        "clean_price": clean_price,
        "clean_quantity": clean_quantity,
        "signal_strategy": signal_strategy
    }


async def _process_execution(data, preference, clean_price, timing_data):
    """Process signal execution."""
    timing_data['sent_to_binance'] = datetime.now()
    execution_result = await trader.execute_trade(data, preference, clean_price)
    timing_data['executed'] = datetime.now()

    try:
        clean_quantity = float(data.get("quantity"))
    except (TypeError, ValueError):
        clean_quantity = None

    quantity_for_storage = (
        clean_quantity if clean_quantity is not None
        else data.get("quantity", "")
    )

    if execution_result.get("success"):
        order_id = execution_result.get("order", {}).get("orderId")
        print(f"💾 STORING SUCCESS: action={data.get('action')}, symbol={data.get('symbol')}, order_id={order_id}")
        store_execution(
            data.get("action", ""),
            data.get("symbol", ""),
            quantity_for_storage,
            "success",
            order_id,
            timing_data
        )
    else:
        print(f"💾 STORING FAILURE: action={data.get('action')}, symbol={data.get('symbol')}, error={execution_result.get('error')}")
        store_execution(
            data.get("action", ""),
            data.get("symbol", ""),
            quantity_for_storage,
            "failed",
            execution_result.get("error"),
            timing_data
        )

    return execution_result


def _process_ignored_signal(data, ignore_message, timing_data):
    """Process ignored signal."""
    if ignore_message:
        try:
            clean_quantity = float(data.get("quantity"))
        except (TypeError, ValueError):
            clean_quantity = None

        quantity_for_storage = (
            clean_quantity if clean_quantity is not None
            else data.get("quantity", "")
        )

        store_execution(
            data.get("action", ""),
            data.get("symbol", ""),
            quantity_for_storage,
            "ignored",
            ignore_message,
            timing_data
        )


def _store_signal_data(data, clean_quantity, clean_price):
    """Store signal data."""
    store_signal(
        data.get("action", ""),
        data.get("symbol", ""),
        clean_quantity if clean_quantity is not None else data.get("quantity", ""),
        clean_price,
        data.get("time", ""),
    )


def _build_response(allow_execution, execution_result, ignore_message, preference,
                   data, timing_data, signal_strategy=None):
    """Build the final response."""
    selected_product = preference.get("product") if preference else None

    if allow_execution and execution_result:
        return {
            "status": "success",
            "message": "Trade executed",
            "result": execution_result,
            "selected_strategy": preference.get("strategy") if preference else None,
            "selected_product": selected_product,
            "timing": timing_data
        }

    if ignore_message:
        return {
            "status": "ignored",
            "message": ignore_message,
            "selected_strategy": preference.get("strategy") if preference else None,
            "selected_product": selected_product,
            "signal_strategy": signal_strategy,
            "signal_product": _normalise_symbol(data.get("symbol")),
            "timing": timing_data
        }

    return {"status": "success", "message": "Signal received", "timing": timing_data}


@router.get("/executions", response_model=List[ExecutionRecord])
def list_executions(limit: int = 20, db: Session = Depends(get_db)) -> List[Execution]:
    """Return the most recent execution records."""
    limit = max(1, min(limit, 100))
    executions = (
        db.query(Execution)
        .order_by(Execution.timestamp.desc())
        .limit(limit)
        .all()
    )
    print(f"📊 EXECUTIONS ENDPOINT: Returning {len(executions)} executions")
    for i, exec in enumerate(executions[:3]):  # Show first 3 for debug
        print(f"📊 EXECUTION #{i+1}: id={exec.id}, status={exec.status}, action={exec.action}, symbol={exec.symbol}, order_id={exec.order_id}")
        print(f"📊 EXECUTION #{i+1} TIMES: timestamp={exec.timestamp}, execution_time={exec.execution_time}")
    return executions


@router.get("/account/summary")
async def account_summary():
    """Expose a lightweight futures account snapshot for the UI."""
    summary, error = trader.get_account_summary()
    if error:
        return {"status": "error", "message": error}
    return {"status": "success", "data": summary}


@router.post("/webhook")
async def receive_signal(request: Request):
    """Receive TradingView webhook signals"""
    timing_data = _initialize_timing_data()

    try:
        data = await request.json()
        if not isinstance(data, dict):
            data = {}

        # DEBUG: Log received webhook data
        print(f"🔍 WEBHOOK RECEIVED: {data}")

        _extract_signal_time(data, timing_data)

        validation_result = _validate_signal_permissions(data)
        allow_execution = validation_result["allow_execution"]
        ignore_message = validation_result["ignore_message"]
        preference = validation_result["preference"]
        clean_price = validation_result["clean_price"]

        # DEBUG: Log validation results
        print(f"🔍 VALIDATION: allow_execution={allow_execution}, ignore_message='{ignore_message}'")
        print(f"🔍 PREFERENCES: {preference}")

        timing_data['processed'] = datetime.now()

        if allow_execution:
            print("✅ EXECUTING TRADE...")
            execution_result = await _process_execution(data, preference, clean_price, timing_data)
            print(f"✅ EXECUTION RESULT: {execution_result}")
        else:
            print(f"❌ TRADE IGNORED: {ignore_message}")
            _process_ignored_signal(data, ignore_message, timing_data)
            execution_result = None

        _store_signal_data(data, validation_result["clean_quantity"], clean_price)

        return _build_response(allow_execution, execution_result, ignore_message, preference,
                              data, timing_data, validation_result.get("signal_strategy"))

    except Exception as exc:  # pylint: disable=broad-except
        print(f"🚨 WEBHOOK ERROR: {str(exc)}")
        return {"status": "error", "message": str(exc), "timing": timing_data}


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "TradingView Webhook Receiver is running"}
