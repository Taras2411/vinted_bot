from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import Optional
import re

from parser.locales import (
    LocaleConfig,
    resolve as resolve_locale,
    BRAND_LABELS,
    CONDITION_LABELS,
    SIZE_LABELS,
)




@dataclass
class VintedItem:
    """Class representing a Vinted item"""
    url: str
    parsed_title: Optional['titleParsed'] = None
    brand_id: Optional[int] = None
    image_src: Optional[str] = None
    vinted_id: Optional[int] = None
    currency: Optional[str] = None      # ISO code of the site (CZK, EUR, ...)

    def __repr__(self) -> str:
        return f"VintedItem(url='{self.url}')"

@dataclass
class titleParsed:
    """Class representing a parsed title"""
    name: str
    brand : Optional[str] = None
    condition: Optional[str] = None
    size: Optional[str] = None
    price: Optional[str] = None              # original price as shown, e.g. "12,00 €"
    price_amount: Optional[float] = None     # numeric value of the price

def extract_vinted_id(href: str) -> Optional[int]:
    """Extract Vinted ID from item href URL"""
    if not href:
        return None
    match = re.search(r'/items/(\d+)', href)
    return int(match.group(1)) if match else None


def _amount_to_float(num_str: str) -> Optional[float]:
    """Normalise a localized number string ("1 234,56", "1,234.56") to float."""
    s = num_str.replace(' ', ' ').replace(' ', ' ').strip()
    s = s.replace(' ', '')

    if ',' in s and '.' in s:
        # The right-most separator is the decimal one.
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        # Comma is decimal only if it is followed by 1-2 trailing digits.
        if re.search(r',\d{1,2}$', s):
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    elif '.' in s:
        # A lone dot grouping thousands (e.g. "1.234") is not a decimal point.
        if re.search(r'\.\d{3}$', s) and not re.search(r'^\d{1,3}\.\d{1,2}$', s):
            s = s.replace('.', '')

    try:
        return float(s)
    except ValueError:
        return None


def _extract_prices(title: str, symbol: str) -> list[tuple[str, str]]:
    """
    Find every "<number> <symbol>" (or "<symbol><number>") occurrence in the
    title. Returns a list of (full_match, numeric_part) tuples in order.
    """
    sym = re.escape(symbol)
    number = r'\d{1,3}(?:[\s  .,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?'

    after = re.compile(rf'(?P<num>{number})\s*{sym}')
    matches = [(m.group(0), m.group('num')) for m in after.finditer(title)]
    if matches:
        return matches

    before = re.compile(rf'{sym}\s*(?P<num>{number})')
    return [(m.group(0), m.group('num')) for m in before.finditer(title)]


def title_parser(title: str, config: LocaleConfig) -> titleParsed:
    name = None
    brand = None
    condition = None
    size = None
    price = None
    price_amount = None

    # --- price -------------------------------------------------------------
    # Vinted lists the price twice (item price + total incl. buyer protection).
    # Keep the original behaviour of preferring the second value when present.
    prices = _extract_prices(title, config.currency_symbol)
    if len(prices) >= 2:
        chosen_full, chosen_num = prices[1]
    elif len(prices) == 1:
        chosen_full, chosen_num = prices[0]
    else:
        chosen_full, chosen_num = None, None

    if chosen_full is not None:
        price = chosen_full.strip()
        price_amount = _amount_to_float(chosen_num)

    # Remove every detected price so it does not interfere with field parsing.
    title_without_prices = title
    for full, _ in prices:
        title_without_prices = title_without_prices.replace(full, '')

    title_without_prices = re.sub(r',\s*,', ',', title_without_prices).strip()

    # --- name + labelled fields -------------------------------------------
    parts = [part.strip() for part in title_without_prices.split(',')]

    if parts:
        name = parts[0]

    for part in parts[1:]:
        if ':' not in part:
            continue
        key, _, value = part.partition(':')
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key in BRAND_LABELS:
            brand = value
        elif key in CONDITION_LABELS:
            condition = value
        elif key in SIZE_LABELS:
            size = value

    return titleParsed(
        name=name or "",
        brand=brand,
        condition=condition,
        size=size,
        price=price,
        price_amount=price_amount,
    )


async def parse_vinted(URL: Optional[str] = None) -> list[VintedItem]:
    config = resolve_locale(URL)

    # get brand id from URL
    brand_id = re.search(r'brand_ids\[\]=(\d+)', URL)
    brand_id_int = int(brand_id.group(1)) if brand_id else None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            locale=config.browser_locale,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # ИЗМЕНЕНИЕ 1: Увеличиваем таймаут и меняем стратегию ожидания
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[WARNING] Timeout or error during navigation: {e}")
            await browser.close()
            return []

        try:
            # ИЗМЕНЕНИЕ 2: Ждём появления контента явно
            # Vinted может показывать капчу или быть медленным, увеличим тут таймаут тоже
            await page.wait_for_selector(
                ".feed-grid__item:not(.feed-grid__item--full-row)",
                timeout=30000
            )
        except Exception:
            # Если селектор не найден за 30 сек — скорее всего бан или пустая страница
            print(f"[WARNING] Не удалось найти товары на странице (возможно, бан или пусто): {URL}")
            # Можно сделать скриншот для отладки: await page.screenshot(path="debug_error.png")
            await browser.close()
            return []

        # Выбираем только нужные элементы
        items = await page.query_selector_all(
            ".feed-grid__item:not(.feed-grid__item--full-row)"
        )

        print(f"[INFO] {config.domain}: найдено элементов (исключая рекламные/полные строки): {len(items)}")

        # Parse items into VintedItem objects
        vinted_items = []
        for item in items:
            # Find the overlay element within this feed-grid__item
            overlay = await item.query_selector(".new-item-box__overlay.new-item-box__overlay--clickable")
            if not overlay:
                continue

            href = await overlay.get_attribute("href")
            title = await overlay.get_attribute("title")

            # Find the image element within this feed-grid__item
            image_elem = await item.query_selector("img.web_ui__Image__content")
            image_src = await image_elem.get_attribute("src") if image_elem else None

            parsedTitle = title_parser(title, config) if title else None
            vinted_id = extract_vinted_id(href)
            vinted_item = VintedItem(
                url=href,
                parsed_title=parsedTitle,
                brand_id=brand_id_int,
                image_src=image_src,
                vinted_id=vinted_id,
                currency=config.currency,
            )
            vinted_items.append(vinted_item)

        await browser.close()
        return vinted_items