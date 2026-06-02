"""
Generate "region" (country-domain) variants of a Vinted search URL.

Vinted serves the *same* global catalog on every country domain, so the filter
parameters that make up a search URL are reusable across regions by swapping
only the host:

  * ``catalog[]``      – category ids        (global)
  * ``brand_ids[]``    – brand ids           (global)
  * ``size_ids[]``     – size ids            (global)
  * ``color_ids[]``    – color ids           (global)
  * ``status_ids[]``   – condition ids       (global)
  * ``search_text``    – free-text query     (global)
  * ``order``          – sort order          (global)

The only parameters tied to a specific site are money related:

  * ``price_from`` / ``price_to`` – expressed in the site's *local currency*,
  * ``currency``                  – the ISO code of that currency.

A naive host swap therefore "works" for every filter but would leave a French
EUR price range on a Czech CZK page (50 € would be read as 50 Kč). So when a
search carries a price filter we *adapt* those params to the target site's
currency, converting the bounds with the same Frankfurter rates used elsewhere
in the project. Everything else is copied verbatim.
"""

from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from parser.locales import DOMAIN_LOCALES, LocaleConfig, resolve as resolve_locale


# The two domain groups are *equivalence classes*: any domain inside a group is
# considered the same "region" for de-duplication. A given search (combination
# of filters) only ever needs two copies — one anywhere in group 1 (the "fr
# group") and one anywhere in group 2 (the "cz group"). fr / cz are the default
# representatives used when a twin has to be created.
REGION_GROUP_1: tuple[str, ...] = (
    "vinted.fr", "vinted.es", "vinted.it", "vinted.pt",
    "vinted.nl", "vinted.be", "vinted.lu", "vinted.de", "vinted.at",
)
REGION_GROUP_2: tuple[str, ...] = (
    "vinted.pl", "vinted.lt", "vinted.cz", "vinted.sk", "vinted.se",
    "vinted.dk", "vinted.fi", "vinted.ro", "vinted.hu", "vinted.hr",
    "vinted.gr", "vinted.lv", "vinted.ee", "vinted.si",
)

REGION_GROUPS: tuple[tuple[str, ...], ...] = (REGION_GROUP_1, REGION_GROUP_2)

# Domain created for a group when that group is missing a copy of a search.
GROUP_REPRESENTATIVES: tuple[str, ...] = ("vinted.fr", "vinted.cz")

_PRICE_PARAMS = ("price_from", "price_to")
# Excluded from the "same search" signature: the host is dropped already,
# price/currency are just the localized expression of the same filter, and
# time/page are pagination/timestamp noise that does not change which listings
# a search matches.
_SIGNATURE_EXCLUDE = _PRICE_PARAMS + ("currency", "time", "page")


def group_of(domain: str) -> int | None:
    """Return the index (0 or 1) of the region group ``domain`` belongs to."""
    for index, group in enumerate(REGION_GROUPS):
        if domain in group:
            return index
    return None


def param_signature(url: str) -> str:
    """Domain/currency/price-independent signature of a search's filters.

    Two URLs that select the same items (same catalog, brand, size, text, ...)
    share a signature regardless of which country domain they point at or which
    local-currency price bounds they carry. Used to tell whether a given group
    already has a copy of a search.
    """
    parts = urlsplit(url)
    pairs = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in _SIGNATURE_EXCLUDE
    )
    return f"{parts.path.rstrip('/')}?{urlencode(pairs)}"


def _swap_host(url: str, source_domain: str, target_domain: str) -> str:
    """Return ``url`` with its Vinted domain replaced by ``target_domain``.

    Any subdomain (e.g. ``www.``) and the port are preserved.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()

    if host == source_domain:
        new_host = target_domain
    elif host.endswith("." + source_domain):
        prefix = host[: -len(source_domain)]  # keeps the trailing dot
        new_host = prefix + target_domain
    else:
        new_host = target_domain

    netloc = f"{new_host}:{parts.port}" if parts.port else new_host
    return urlunsplit(
        (parts.scheme or "https", netloc, parts.path, parts.query, parts.fragment)
    )


def _convert_price(value: str, rate: float) -> str | None:
    """Convert a price-bound string by ``rate``, rounded to a whole unit."""
    try:
        amount = float(value.replace(",", "."))
    except ValueError:
        return None
    return str(int(round(amount * rate)))


async def _adapt_currency(url: str, source: LocaleConfig, target: LocaleConfig) -> str:
    """Rewrite price bounds / ``currency`` param of ``url`` into ``target``'s currency.

    Returns ``url`` untouched when there is no price filter (then the currency
    of the page is irrelevant) or when the two sites share a currency.
    """
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)

    if not any(k in _PRICE_PARAMS for k, _ in pairs):
        return url
    if source.currency == target.currency:
        return url

    # Imported lazily: bot.currency pulls in the bot package, which imports this
    # module at startup — a top-level import would create a circular dependency.
    from bot.currency import get_rate

    rate = await get_rate(source.currency, target.currency)

    new_pairs: list[tuple[str, str]] = []
    currency_seen = False
    for key, value in pairs:
        if key in _PRICE_PARAMS and rate is not None and value.strip():
            converted = _convert_price(value, rate)
            if converted is not None:
                value = converted
        elif key == "currency":
            value = target.currency
            currency_seen = True
        new_pairs.append((key, value))

    if not currency_seen:
        new_pairs.append(("currency", target.currency))

    query = urlencode(new_pairs, doseq=True)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, parts.fragment)
    )


async def make_region_twin(url: str, target_domain: str) -> str | None:
    """Build the ``target_domain`` copy of ``url``.

    Swaps the host and adapts any price filter to the target site's currency.
    Returns ``None`` if ``target_domain`` is not a domain we can localize.
    """
    source = resolve_locale(url)
    target = DOMAIN_LOCALES.get(target_domain)
    if target is None:
        return None
    swapped = _swap_host(url, source.domain, target_domain)
    return await _adapt_currency(swapped, source, target)
