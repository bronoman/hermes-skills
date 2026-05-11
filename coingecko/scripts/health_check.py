#!/usr/bin/env python3
"""
Health check for price service API and fallback to Kraken.
Verifies API key validity, rate limit status, and system readiness.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime




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

def health_check() -> dict:
    """
    Comprehensive health check.
    
    Returns:
        {
            "api_status": "ok" | "error",
            "key_type": "demo" | "pro" | "none",
            "rate_limit_remaining": int,
            "rate_limit_reset": str,
            "kraken_fallback": "ok" | "error",
            "timestamp": str,
            "error": str (if any failure)
        }
    """
    
    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Check API key
    api_key = get_coingecko_api_key()
    
    if not api_key:
        result["key_type"] = "none"
        result["api_status"] = "not_configured"
        result["note"] = "No API key configured; will use Kraken fallback"
    else:
        result["key_type"] = "demo" if api_key.startswith("CG-") else "unknown"
        
        # Test price service API
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "x_cg_demo_api_key": api_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if "bitcoin" in data and "usd" in data["bitcoin"]:
                    result["api_status"] = "ok"
                    result["price_sample"] = data["bitcoin"]["usd"]
                    
                    if "X-Ratelimit-Limit-Requests-Per-Minute" in response.headers:
                        limit = int(response.headers.get("X-Ratelimit-Limit-Requests-Per-Minute", 0))
                        remaining = int(response.headers.get("X-Ratelimit-Remaining-Requests", 0))
                        result["rate_limit_total"] = limit
                        result["rate_limit_remaining"] = remaining
                else:
                    result["api_status"] = "error"
                    result["error"] = "Unexpected API response format"
            elif response.status_code == 401:
                result["api_status"] = "error"
                result["error"] = "Invalid API key (401 Unauthorized)"
            elif response.status_code == 429:
                result["api_status"] = "rate_limited"
                result["error"] = "API rate limit exceeded (429)"
            else:
                result["api_status"] = "error"
                result["error"] = f"HTTP {response.status_code}"
        
        except requests.exceptions.Timeout:
            result["api_status"] = "timeout"
            result["error"] = "Request timeout (>5s)"
        except Exception as e:
            result["api_status"] = "error"
            result["error"] = str(e)
    
    # Test Kraken fallback
    try:
        response = requests.get(
            "https://api.kraken.com/0/public/Ticker",
            params={"pair": "XBTUSD"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and "XXBTZUSD" in data["result"]:
                result["kraken_fallback"] = "ok"
                price = float(data["result"]["XXBTZUSD"]["c"][0])
                result["kraken_price_sample"] = price
            else:
                result["kraken_fallback"] = "error"
                result["kraken_error"] = "No XXBTZUSD data"
        else:
            result["kraken_fallback"] = "error"
            result["kraken_error"] = f"HTTP {response.status_code}"
    
    except Exception as e:
        result["kraken_fallback"] = "error"
        result["kraken_error"] = str(e)
    
    return result

if __name__ == "__main__":
    result = health_check()
    print(json.dumps(result, indent=2))
