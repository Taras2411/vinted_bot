Vinted Monitor Bot 🤖

An advanced, asynchronous Telegram bot designed to monitor Vinted listings in real-time. The bot scrapes Vinted based on user-defined search URLs and sends instant notifications when new items matching the criteria are found.

![alt text](https://img.shields.io/badge/python-3.10%2B-blue.svg)


![alt text](https://img.shields.io/badge/aiogram-3.x-orange.svg)


![alt text](https://img.shields.io/badge/playwright-v1.x-green.svg)


![alt text](https://img.shields.io/badge/sqlite-3-lightgrey.svg)

🌟 Features

    Real-time Monitoring: Automatically polls Vinted at configurable intervals.

    Asynchronous Architecture: Built with asyncio, allowing the bot, the parser, and the notifier to run concurrently without blocking each other.

    Headless Scraping: Uses Playwright with anti-detection headers to bypass basic bot protections.

    Smart Filtering: Parses titles, prices, brands, and images from Vinted items.

    Multi-location Support: Works with any Vinted country site (vinted.cz, vinted.de, vinted.fr, vinted.co.uk, vinted.pl, vinted.com, ...). The locale, language labels, and currency are detected automatically from each search URL's domain (see parser/locales.py).

    Currency Conversion: Prices from any site are automatically converted to CZK in notifications using the free Frankfurter (ECB) exchange-rate API, with in-memory rate caching.

    Multi-user Support: Users can manage their own list of search queries via Telegram commands.

    Graceful Shutdown: Handles SIGINT and SIGTERM signals for safe database closure and task cancellation.

🛠 Tech Stack

    Framework: Aiogram 3.x (Telegram Bot API)

    Scraping: Playwright (Chromium)

    Database: Aiosqlite (Asynchronous SQLite wrapper)

    Concurrency: Python asyncio with Semaphores for resource management.


Installation

Clone the repository:
  
    git clone https://github.com/Taras2411/vinted_bot
    cd vinted_bot

Create venv:

    python -m venv nev

Activate venv:
Linux / macOS

    source venv/bin/activate
Windows (PowerShell)

    .\venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r requirements.txt
    pip install pytest-playwright
    
Install Playwright browsers:
    
    playwright install

Configuration

Open bot/config.py and update the settings:
    
    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    PARSER_INTERVAL_MINUTES = 0.5  # How often to check Vinted
    NOTIFIER_INTERVAL_MINUTES = 0.5 # How often to check DB for new items
    TELEGRAM_NOTIFICATIONS_INTRVAL_MS = 1000 # Delay between messages to avoid spam limits

  

Database Setup

The bot uses SQLite. On the first launch, it will automatically create a data/vinted.db file and initialize the schema using db/schema.sql.

🎮 Usage

Run the bot:
   
    python main.py

  

Telegram Commands

    /start - Register in the system.

    /add_search <vinted_url> <title> - Add a new Vinted search URL to monitor.

    /auto_region [search_id] - Mirror existing search(es) so each one is covered
        in both Vinted region groups. With a search_id only that search is
        mirrored; omit it to process all of your active searches. Each unique
        search needs at most two copies: one anywhere in the fr group (fr, es,
        it, pt, nl, be, lu, de, at) and one anywhere in the cz group (pl, lt,
        cz, sk, se, dk, fi, ro, hu, hr, gr, lv, ee, si). If a group already has
        the search on any of its domains it is left alone; otherwise a copy is
        created on that group's default domain (fr / cz). Filters (catalog,
        brand, size, search text...) are copied verbatim; price bounds are
        converted into the new region's local currency.

    /list_searches - View all your active searches and their IDs.

    /remove_search <id> - Stop monitoring a specific search.

    /help - Show available commands.

🏗 Project Structure

    main.py: Entry point. Orchestrates the bot, parser, and notification loops.

    bot/: Contains Telegram logic, command handlers, and the notification engine.

    parser/: Contains the Playwright scraper logic, the scheduling loop, and parser/locales.py (per-domain locale & currency configuration). To support an additional Vinted country site, add an entry to DOMAIN_LOCALES.

    bot/currency.py: Converts item prices to CZK via the free Frankfurter API.

    db/: Database connection management and Repository pattern implementation for Users, Searches, and Items.

    core/: Shared utilities like the global shutdown event.

🔒 Resource Management

The project includes a browser_semaphore in the parser_service.py to limit the number of concurrent browser instances (default: 5). This prevents the bot from consuming excessive RAM when many searches are active simultaneously.

Developed for educational purposes. Please respect Vinted's Terms of Service regarding automated access.
