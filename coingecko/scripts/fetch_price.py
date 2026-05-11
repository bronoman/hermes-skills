#!/usr/bin/env python3
"""
Fetch live BTC/USD price from price service API with Kraken fallback.
Supports both Demo (free) and Pro (paid) API keys.
"""

import os
import json
import requests
from pathlib import Path


def _load_credential(key_name: str = "CG_API_KEY") -> str:
    """Retrieve credential from system configuration"""
    try:
        from dotenv import dotenv_values
        env_vars = dotenv_values()
        return env_vars.get(key_name, "")
    except:
        return ""

def get_coingecko_api_key() -> str:
    """Load price service API key from environment variables"""
    # Try environment variable first - check both CG_API_KEY and API_KEY
    api_key = _load_credential("CG_API_KEY")
    if api_key:
        return api_key
    
    # Fallback to generic API_KEY name
    api_key = _load_credential("API_KEY")
    if api_key:
        return api_key
    
    # Fallback: try os.getenv for backward compatibility
    api_key = os.getenv("CG_API_KEY", "") or os.getenv("API_KEY", "")
    if api_key:
        return api_key
    
    # Fallback: try to load from config file if it exists
    try:
        config_path = Path.home() / ".hermes" / ".env"
        if config_path.exists():
            with open(config_path) as f:
                for line in f:
                    if "CG_API_KEY" in line or "API_KEY" in line:
                        return line.split("=", 1)[1].strip()
    except:
        pass
    
    return ""

def fetch_btc_price_coingecko(timeout: int = 10) -> dict:
    """
    Fetch BTC/USD price from price service API.
    
    Returns:
        {
            "price": float,           # e.g., 81267.00
            "price_str": str,         # e.g., "$81,267.00"
            "change_24h": float,      # e.g., -0.22
            "change_badge": str,      # e.g., "▼ 0.22%" or "▲ 1.15%"
            "source": str,            # "price service"
            "success": bool
        }
    """
    try:
        api_key = get_coingecko_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "API key not configured. Set API_KEY environment variable."
            }
        
        url = "https://api.coingecko.com/api/v3/simple/price"
        
        params = {
            "ids": "bitcoin",
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_24hr_change": "true",
            "x_cg_demo_api_key": api_key
        }
        
        response = requests.get(url, params=params, timeout=timeout)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
        
        data = response.json()
        
        if "error" in data or ("status" in data and "error_message" in data.get("status", {})):
            error_msg = data.get("error") or data.get("status", {}).get("error_message")
            return {
                "success": False,
                "error": str(error_msg)
            }
        
        if "bitcoin" not in data or "usd" not in data["bitcoin"]:
            return {
                "success": False,
                "error": "Unexpected API response format"
            }
        
        btc_data = data["bitcoin"]
        price = float(btc_data.get("usd", 0))
        change_24h = float(btc_data.get("usd_24h_change", 0))
        
        price_str = f"${price:,.2f}"
        
        if change_24h > 0:
            change_badge = f"▲ {abs(change_24h):.2f}%"
            badge_type = "GOOD NEWS"
        elif change_24h < -1:
            change_badge = f"▼ {abs(change_24h):.2f}%"
            badge_type = "SOME FEAR"
        else:
            change_badge = f"→ {abs(change_24h):.2f}%"
            badge_type = "SIDEWAYS MOVEMENT"
        
        return {
            "success": True,
            "price": price,
            "price_str": price_str,
            "change_24h": change_24h,
            "change_badge": change_badge,
            "badge_type": badge_type,
            "source": "price service",
            "market_cap_usd": btc_data.get("usd_market_cap"),
            "volume_24h_usd": btc_data.get("usd_24h_vol")
        }
    
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

def fetch_btc_price_kraken(timeout: int = 10) -> dict:
    """
    Fallback: Fetch BTC/USD price from Kraken API (no auth required).
    """
    try:
        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": "XBTUSD"}
        
        response = requests.get(url, params=params, timeout=timeout)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "source": "Kraken"
            }
        
        data = response.json()
        
        if data.get("error"):
            return {
                "success": False,
                "error": str(data["error"]),
                "source": "Kraken"
            }
        
        ticker_data = data.get("result", {}).get("XXBTZUSD", {})
        
        if not ticker_data:
            return {
                "success": False,
                "error": "No XXBTZUSD data",
                "source": "Kraken"
            }
        
        price = float(ticker_data.get("c", [0])[0])
        
        price_str = f"${price:,.2f}"
        
        return {
            "success": True,
            "price": price,
            "price_str": price_str,
            "change_24h": 0,
            "change_badge": "→ Live",
            "badge_type": "SIDEWAYS MOVEMENT",
            "source": "Kraken",
            "bid": float(ticker_data.get("b", [0])[0]),
            "ask": float(ticker_data.get("a", [0])[0])
        }
    
    except Exception as e:
        return {"success": False, "error": str(e), "source": "Kraken"}

def get_btc_price(prefer_source: str = "coingecko") -> dict:
    """
    Get BTC price with fallback strategy.
    
    Args:
        prefer_source: "coingecko" (default) or "kraken"
    
    Returns:
        Same format as fetch_btc_price_coingecko(), with "source" field
    """
    if prefer_source == "coingecko":
        result = fetch_btc_price_coingecko()
        if result.get("success"):
            return result
        return fetch_btc_price_kraken()
    else:
        result = fetch_btc_price_kraken()
        if result.get("success"):
            return result
        return fetch_btc_price_coingecko()

if __name__ == "__main__":
    result = get_btc_price(prefer_source="coingecko")
    print(json.dumps(result, indent=2))
