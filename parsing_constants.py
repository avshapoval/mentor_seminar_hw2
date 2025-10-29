BASE_URL = "https://www.cian.ru/cat.php"
CIAN_BASE_URL = "https://www.cian.ru"

# Поиск
DEFAULT_SEARCH_PARAMS = {
    "bbox": "55.211355124676885,35.29739844147115,56.011941010307225,39.51614844147116",
    "center": "55.61369999784865,37.40677344147117",
    "deal_type": "sale",
    "engine_version": "2",
    "offer_type": "flat",
    "region": "1",
    "zoom": "15"
}

# Браузер
BROWSER_VIEWPORT = {'width': 1920, 'height': 1080}
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
SLOW_MO = 150
HEADLESS = False

# Парсер
PAGE_LOAD_TIMEOUT = 90000
SELECTOR_TIMEOUT = 15000
SLEEP_BETWEEN_PAGES = 5
SLEEP_AFTER_LOAD = 3

# Селекторы
CARD_SELECTORS = [
    '[data-name="CardComponent"]',
    'article[data-name="CardComponent"]',
    '[data-testid="offer-card"]',
    'div[data-name="Offers"] > div',
    'article'
]

# Поля CSV
CSV_FIELDNAMES = [
    'offer_id',
    'title',
    'address',
    'district',
    'price',
    'total_area',
    'rooms',
    'floor',
    'floors_total',
    'house_type',
    'year_built',
    'description',
    'link'
]

# Имена файлов
DEFAULT_CSV_FILENAME = "data/cian_data.csv"
DEBUG_SCREENSHOT_FILENAME = "debug_screenshot.png"