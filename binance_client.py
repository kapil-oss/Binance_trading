"""Simple Binance API client using requests (no Rust dependencies)."""
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, List
import requests
from urllib.parse import urlencode


class BinanceAPIException(Exception):
    """Binance API exception."""
    pass


class SimpleBinanceClient:
    """Simple Binance client using requests."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature."""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        """Make API request."""
        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)

        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise BinanceAPIException(f"Request failed: {str(e)}")
        except Exception as e:
            raise BinanceAPIException(f"API error: {str(e)}")

    def futures_account(self) -> Dict[str, Any]:
        """Get futures account information."""
        return self._make_request('GET', '/fapi/v2/account', signed=True)

    def futures_account_balance(self) -> List[Dict[str, Any]]:
        """Get futures account balance."""
        return self._make_request('GET', '/fapi/v2/balance', signed=True)

    def futures_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get symbol ticker."""
        return self._make_request('GET', '/fapi/v1/ticker/price', {'symbol': symbol})

    def futures_exchange_info(self) -> Dict[str, Any]:
        """Get exchange info."""
        return self._make_request('GET', '/fapi/v1/exchangeInfo')

    def futures_change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Change leverage for symbol."""
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        return self._make_request('POST', '/fapi/v1/leverage', params, signed=True)

    def futures_create_order(self, symbol: str, side: str, type: str, quantity: str, **kwargs) -> Dict[str, Any]:
        """Create futures order."""
        params = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'quantity': quantity
        }
        params.update(kwargs)
        return self._make_request('POST', '/fapi/v1/order', params, signed=True)


# Factory function to maintain compatibility
def Client(api_key: str, api_secret: str, testnet: bool = False) -> SimpleBinanceClient:
    """Create Binance client instance."""
    return SimpleBinanceClient(api_key, api_secret, testnet)