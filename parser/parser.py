from playwright.async_api import async_playwright
from dataclasses import dataclass
from typing import Optional
import re
import asyncio




@dataclass
class VintedItem:
    """Class representing a Vinted item"""
    url: str
    parsed_title: Optional['titleParsed'] = None
    brand_id: Optional[int] = None
    image_src: Optional[str] = None
    vinted_id: Optional[int] = None
    
    def __repr__(self) -> str:
        return f"VintedItem(title='{self.title}')"
    
@dataclass
class titleParsed:
    """Class representing a parsed title"""
    name: str
    brand : Optional[str] = None
    condition: Optional[str] = None
    size: Optional[str] = None
    price: Optional[str] = None

def extract_vinted_id(href: str) -> Optional[int]:
    """Extract Vinted ID from item href URL"""
    if not href:
        return None
    match = re.search(r'/items/(\d+)', href)
    return int(match.group(1)) if match else None


def title_parser(title: str) -> titleParsed:
    # example of unparsed title: Dětský Nike batoh nový, značka: Nike, stav: Nový s visačkou, velikost: Univerzální, 400,00 Kč, 438,00 Kč včetně Ochrany kupujících

    
    name = None
    brand = None
    condition = None
    size = None
    price = None
    
    # Extract prices with currency (handles decimal comma separator)
    # Pattern: number,number currency (e.g., "400,00 Kč")
    price_pattern = r'(\d+,\d+\s+\w+)'
    prices = re.findall(price_pattern, title)
    
    # Get second price if available, otherwise first price
    if len(prices) >= 2:
        price = prices[1]
    elif len(prices) == 1:
        price = prices[0]
    
    # Remove prices from title for easier field extraction
    title_without_prices = re.sub(price_pattern, '', title).strip()
    
    # Split by comma and process fields
    parts = [part.strip() for part in title_without_prices.split(',')]
    
    # First part is the name
    if parts:
        name = parts[0]
    
    # Parse other fields
    for part in parts[1:]:
        if part.startswith('značka:'):
            brand = part.replace('značka:', '').strip()
        elif part.startswith('stav:'):
            condition = part.replace('stav:', '').strip()
        elif part.startswith('velikost:'):
            size = part.replace('velikost:', '').strip()
    
    return titleParsed(
        name=name or "",
        brand=brand,
        condition=condition,
        size=size,
        price=price
    )
    

async def parse_vinted(URL: Optional[str] = None) -> list[VintedItem]:
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
            locale="cs-CZ",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        await page.goto(URL, wait_until="networkidle")

        # Ждём элементы, которые имеют основной класс, но НЕ имеют класса для полных строк
        await page.wait_for_selector(
            ".feed-grid__item:not(.feed-grid__item--full-row)",
            timeout=15000
        )

        # Выбираем только нужные элементы
        items = await page.query_selector_all(
            ".feed-grid__item:not(.feed-grid__item--full-row)"
        )

        print(f"Найдено элементов (исключая рекламные/полные строки): {len(items)}")

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
            
            
            parsedTitle = title_parser(title) if title else None
            vinted_id = extract_vinted_id(href)
            vinted_item = VintedItem(url=href, parsed_title=parsedTitle, brand_id=brand_id_int, image_src=image_src, vinted_id=vinted_id)
            vinted_items.append(vinted_item)

        await browser.close()
        return vinted_items

