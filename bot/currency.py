"""
Currency conversion to CZK using the free, key-less Frankfurter API
(https://www.frankfurter.app, ECB reference rates).

Rates are cached in memory per source currency for ``_TTL`` seconds so we do not
hit the API for every notification. If the API is unreachable we fall back to the
last cached rate (if any) and otherwise return ``None`` so the caller can simply
skip the conversion.
"""

import time
import aiohttp

_TARGET = "CZK"
_API = "https://api.frankfurter.app/latest"
_TTL = 3600  # seconds

# (base, target) -> (rate, fetched_at)
_cache: dict[tuple[str, str], tuple[float, float]] = {}


async def get_rate(base: str, target: str) -> float | None:
    """Return how many ``target`` units one ``base`` unit is worth, or None."""
    if not base or not target:
        return None

    base = base.upper()
    target = target.upper()
    if base == target:
        return 1.0

    now = time.time()
    key = (base, target)
    cached = _cache.get(key)
    if cached and now - cached[1] < _TTL:
        return cached[0]

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {"base": base, "symbols": target}
            async with session.get(_API, params=params) as resp:
                if resp.status != 200:
                    print(f"[WARN] currency API returned {resp.status} for {base}->{target}")
                    return cached[0] if cached else None
                data = await resp.json()

        rate = data.get("rates", {}).get(target)
        if rate is None:
            print(f"[WARN] no {target} rate returned for {base}")
            return cached[0] if cached else None

        _cache[key] = (float(rate), now)
        return float(rate)

    except Exception as e:
        print(f"[WARN] currency conversion failed for {base}->{target}: {e}")
        return cached[0] if cached else None


async def convert(amount: float | None, base: str | None, target: str | None) -> float | None:
    """Convert ``amount`` from ``base`` currency to ``target``. None if not possible."""
    if amount is None or not base or not target:
        return None

    rate = await get_rate(base, target)
    if rate is None:
        return None

    return amount * rate


async def get_rate_to_czk(currency: str) -> float | None:
    """Return how many CZK one unit of ``currency`` is worth, or None on failure."""
    return await get_rate(currency, _TARGET)


async def convert_to_czk(amount: float | None, currency: str | None) -> float | None:
    """Convert ``amount`` of ``currency`` to CZK. Returns None if not possible."""
    return await convert(amount, currency, _TARGET)