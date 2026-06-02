"""
Configuration for the different Vinted country sites (vinted.cz, vinted.de, ...).

Every Vinted domain serves the UI in a local language and prices in a local
currency. To support more than one location we keep a small table that maps a
domain to:

  * the browser ``locale`` to request the page with,
  * the ISO currency code used on that site (used for conversion),
  * the currency token that appears in the item title (used to parse prices).

The brand / condition / size labels in the item ``title`` attribute are also
localized. Instead of keeping a label set per language (and risking a wrong
guess for a single domain) we keep the union of every known label and match
case-insensitively. The currency, which must be exact, is driven by the domain.
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class LocaleConfig:
    """Per-domain Vinted configuration."""
    domain: str            # registrable domain, e.g. "vinted.cz"
    browser_locale: str    # locale passed to the browser context, e.g. "cs-CZ"
    currency: str          # ISO 4217 code, e.g. "CZK"
    currency_symbol: str   # token shown in the title, e.g. "Kč"


# NOTE: order matters only for "longest suffix wins" matching (see resolve()).
DOMAIN_LOCALES: dict[str, LocaleConfig] = {
    "vinted.cz":     LocaleConfig("vinted.cz",     "cs-CZ", "CZK", "Kč"),
    "vinted.sk":     LocaleConfig("vinted.sk",     "sk-SK", "EUR", "€"),
    "vinted.de":     LocaleConfig("vinted.de",     "de-DE", "EUR", "€"),
    "vinted.at":     LocaleConfig("vinted.at",     "de-AT", "EUR", "€"),
    "vinted.fr":     LocaleConfig("vinted.fr",     "fr-FR", "EUR", "€"),
    "vinted.be":     LocaleConfig("vinted.be",     "fr-BE", "EUR", "€"),
    "vinted.nl":     LocaleConfig("vinted.nl",     "nl-NL", "EUR", "€"),
    "vinted.lu":     LocaleConfig("vinted.lu",     "fr-LU", "EUR", "€"),
    "vinted.es":     LocaleConfig("vinted.es",     "es-ES", "EUR", "€"),
    "vinted.it":     LocaleConfig("vinted.it",     "it-IT", "EUR", "€"),
    "vinted.pt":     LocaleConfig("vinted.pt",     "pt-PT", "EUR", "€"),
    "vinted.ie":     LocaleConfig("vinted.ie",     "en-IE", "EUR", "€"),
    "vinted.lt":     LocaleConfig("vinted.lt",     "lt-LT", "EUR", "€"),
    "vinted.fi":     LocaleConfig("vinted.fi",     "fi-FI", "EUR", "€"),
    "vinted.gr":     LocaleConfig("vinted.gr",     "el-GR", "EUR", "€"),
    "vinted.hr":     LocaleConfig("vinted.hr",     "hr-HR", "EUR", "€"),
    "vinted.co.uk":  LocaleConfig("vinted.co.uk",  "en-GB", "GBP", "£"),
    "vinted.pl":     LocaleConfig("vinted.pl",     "pl-PL", "PLN", "zł"),
    "vinted.se":     LocaleConfig("vinted.se",     "sv-SE", "SEK", "kr"),
    "vinted.dk":     LocaleConfig("vinted.dk",     "da-DK", "DKK", "kr."),
    "vinted.hu":     LocaleConfig("vinted.hu",     "hu-HU", "HUF", "Ft"),
    "vinted.ro":     LocaleConfig("vinted.ro",     "ro-RO", "RON", "lei"),
    "vinted.com":    LocaleConfig("vinted.com",    "en-US", "USD", "$"),
}

# Used when a domain is not in the table above; keeps the original CZ behaviour.
DEFAULT_LOCALE = DOMAIN_LOCALES["vinted.cz"]


# Union of brand / condition / size labels across the supported languages.
# Matching is case-insensitive on the part prefix before the first colon.
BRAND_LABELS = {
    "značka", "marke", "marque", "merk", "brand", "marca", "marka",
    "márka", "märke", "prekės ženklas", "marcă", "μάρκα",
}
CONDITION_LABELS = {
    "stav", "zustand", "état", "etat", "staat", "condition", "estado",
    "condizioni", "stan", "állapot", "skick", "būklė", "stare", "stand",
    "κατάσταση",
}
SIZE_LABELS = {
    "velikost", "veľkosť", "größe", "grösse", "taille", "maat", "size",
    "talla", "taglia", "rozmiar", "méret", "storlek", "dydis", "mărime",
    "tamanho", "μέγεθος", "koko", "størrelse",
}


def resolve(url: Optional[str]) -> LocaleConfig:
    """Return the LocaleConfig for the given Vinted URL (falls back to CZ)."""
    if not url:
        return DEFAULT_LOCALE

    host = (urlparse(url).hostname or url).lower()

    # Match the longest registered suffix so "vinted.co.uk" wins over "vinted.com".
    best: Optional[LocaleConfig] = None
    for domain, cfg in DOMAIN_LOCALES.items():
        if host == domain or host.endswith("." + domain):
            if best is None or len(domain) > len(best.domain):
                best = cfg

    return best or DEFAULT_LOCALE