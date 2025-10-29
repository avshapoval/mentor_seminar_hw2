"""
Парсер данных о квартирах с сайта Cian.ru
"""
import asyncio
import csv
import re
import random
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page

from parsing_constants import (
    BASE_URL,
    CIAN_BASE_URL,
    DEFAULT_SEARCH_PARAMS,
    BROWSER_VIEWPORT,
    USER_AGENT,
    SLOW_MO,
    HEADLESS,
    PAGE_LOAD_TIMEOUT,
    SELECTOR_TIMEOUT,
    SLEEP_BETWEEN_PAGES,
    SLEEP_AFTER_LOAD,
    CARD_SELECTORS,
    CSV_FIELDNAMES,
    DEFAULT_CSV_FILENAME,
    DEBUG_SCREENSHOT_FILENAME
)


class CianParser:
    def __init__(self, search_params: Optional[Dict] = None):
        self.base_url = BASE_URL
        self.params = search_params or DEFAULT_SEARCH_PARAMS
        self.data = []
    
    async def human_like_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Случайная задержка для имитации человеческого поведения"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def random_mouse_movement(self, page: Page):
        """Случайные движения мышью"""
        try:
            width = BROWSER_VIEWPORT['width']
            height = BROWSER_VIEWPORT['height']
            
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except:
            pass
    
    async def random_scroll(self, page: Page):
        """Случайная прокрутка страницы"""
        try:
            scroll_distance = random.randint(300, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await self.human_like_delay(0.5, 1.5)
            
            await page.evaluate(f"window.scrollBy(0, -{scroll_distance // 2})")
            await self.human_like_delay(0.3, 0.8)
            
            await page.evaluate("window.scrollTo(0, 0)")
            await self.human_like_delay(0.5, 1.0)
        except:
            pass
        
    def build_url(self, page_num: int = 1) -> str:
        """Формирует URL с параметрами фильтров"""
        params_str = "&".join([f"{k}={v}" for k, v in self.params.items()])
        if page_num > 1:
            params_str += f"&p={page_num}"
        return f"{self.base_url}?{params_str}"
    
    async def safe_extract(self, card, selector: str, attribute: Optional[str] = None) -> Optional[str]:
        """Безопасно извлекает данные из элемента с обработкой ошибок"""
        try:
            element = await card.query_selector(selector)
            if element:
                if attribute:
                    return await element.get_attribute(attribute)
                else:
                    return await element.inner_text()
            return None
        except:
            return None
    
    def extract_offer_id(self, link: str) -> Optional[str]:
        """Извлекает offer_id из URL"""
        match = re.search(r'/(\d+)/', link)
        return match.group(1) if match else None
    
    def extract_rooms_from_title(self, title: str) -> Optional[str]:
        """Извлекает количество комнат из заголовка"""
        if not title:
            return None
        
        # Поиск комнат
        patterns = [
            r'(\d+)-комн',
            r'(\d+)\s*комн',
            r'(\d+)-комнатн',
            r'(\d+)\s*комнатн',
        ]
        
        for pattern in patterns:
            rooms_match = re.search(pattern, title, re.IGNORECASE)
            if rooms_match:
                return rooms_match.group(1)
        
        # Проверка на студию
        if re.search(r'студи[яюе]', title, re.IGNORECASE):
            return '0'
        
        return None
    
    def parse_offer_info(self, offer_info: str) -> Dict[str, Optional[str]]:
        """Парсит информацию из блока OfferInfo"""
        result = {
            'total_area': None,
            'floor': None,
            'floors_total': None
        }
        
        if not offer_info:
            return result
        
        # Парсим площадь
        area_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:м²|кв\.?\s*м|m²)',
            r'площадь[ью]?\s*[:-]?\s*(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*кв'
        ]
        for pattern in area_patterns:
            area_match = re.search(pattern, offer_info, re.IGNORECASE)
            if area_match:
                result['total_area'] = area_match.group(1).replace(',', '.')
                break
        
        # Парсим этаж
        floor_patterns = [
            r'(\d+)/(\d+)\s*(?:эт|этаж)',
            r'(\d+)\s*этаж.*?(\d+)\s*этаж',
            r'этаж\s*(\d+)\s*из\s*(\d+)',
            r'(\d+)\s*эт\.?\s*из\s*(\d+)'
        ]
        for pattern in floor_patterns:
            floor_match = re.search(pattern, offer_info, re.IGNORECASE)
            if floor_match:
                result['floor'] = floor_match.group(1)
                result['floors_total'] = floor_match.group(2)
                break
        
        return result
    
    async def parse_listing_card(self, card) -> Dict:
        """Извлекает данные из одной карточки объявления"""
        try:
            data = {}
            
            # Ссылка на объявление и offer_id
            link_selectors = [
                'a[href*="/sale/flat/"]',
                'a[data-name="LinkArea"]',
                'a.--media--link',
                'a[target="_blank"]'
            ]
            
            link = None
            for selector in link_selectors:
                link = await self.safe_extract(card, selector, 'href')
                if link:
                    break
            
            if link:
                if not link.startswith('http'):
                    link = f"{CIAN_BASE_URL}{link}"
                data['link'] = link
                data['offer_id'] = self.extract_offer_id(link)
            else:
                data['link'] = None
                data['offer_id'] = None
            
            # Заголовок
            title_selectors = [
                '[data-mark="OfferTitle"]',
                '[data-name="Title"]',
                'span[data-mark="OfferTitle"] span',
                'h3',
                '.--header--'
            ]
            title = None
            for selector in title_selectors:
                title = await self.safe_extract(card, selector)
                if title:
                    break
            data['title'] = title
            
            # Адрес
            address_selectors = [
                '[data-mark="Address"]',
                '[data-name="Geo"]',
                'a[data-name="GeoLabel"]',
                '.--address--'
            ]
            address = None
            for selector in address_selectors:
                address = await self.safe_extract(card, selector)
                if address:
                    break
            data['address'] = address
            
            # Район
            district_selectors = [
                '[data-mark="GeoLabel"]',
                '[data-name="District"]',
                'a[href*="district"]'
            ]
            district = None
            for selector in district_selectors:
                district = await self.safe_extract(card, selector)
                if district:
                    break
            data['district'] = district
            
            # Цена
            price_selectors = [
                '[data-mark="MainPrice"]',
                '[data-testid="price"]',
                'span[data-mark="MainPrice"]',
                '.--price--'
            ]
            price = None
            for selector in price_selectors:
                price = await self.safe_extract(card, selector)
                if price:
                    break
            data['price'] = price
            
            info_selectors = [
                '[data-mark="OfferInfo"]',
                '[data-name="ObjectSummaryDescription"]',
                '[data-testid="object-summary-info"]',
                '.--infos--'
            ]
            offer_info = None
            for selector in info_selectors:
                offer_info = await self.safe_extract(card, selector)
                if offer_info:
                    break
            
            offer_info_parsed = self.parse_offer_info(offer_info)
            data['total_area'] = offer_info_parsed['total_area']
            data['floor'] = offer_info_parsed['floor']
            data['floors_total'] = offer_info_parsed['floors_total']
            
            data['rooms'] = self.extract_rooms_from_title(data['title'])
            
            # Площадь
            if not data['total_area'] and data['title']:
                title_info = self.parse_offer_info(data['title'])
                if title_info['total_area']:
                    data['total_area'] = title_info['total_area']
            
            # Этаж
            if not data['floor'] and data['title']:
                title_info = self.parse_offer_info(data['title'])
                if title_info['floor']:
                    data['floor'] = title_info['floor']
                    data['floors_total'] = title_info['floors_total']
            
            # Тип дома
            house_type_selectors = [
                '[data-mark="HouseType"]',
                '[data-name="HouseType"]'
            ]
            house_type = None
            for selector in house_type_selectors:
                house_type = await self.safe_extract(card, selector)
                if house_type:
                    break
            data['house_type'] = house_type
            
            # Год постройки
            year_selectors = [
                '[data-mark="YearBuilt"]',
                '[data-name="YearBuilt"]'
            ]
            year = None
            for selector in year_selectors:
                year = await self.safe_extract(card, selector)
                if year:
                    break
            data['year_built'] = year
            
            # Описание
            description_selectors = [
                '[data-mark="Description"]',
                '[data-name="Description"]',
                'div[data-name="Description"]',
                '.--description--'
            ]
            description = None
            for selector in description_selectors:
                description = await self.safe_extract(card, selector)
                if description:
                    break
            data['description'] = description
            
            return data
        except Exception as e:
            print(f"Ошибка при парсинге карточки: {e}")
            return None
    
    async def parse_page(self, page: Page) -> List[Dict]:
        """Парсит все объявления на текущей странице"""
        print("Ожидание загрузки объявлений...")
        
        try:
            # Пробуем разные селекторы
            cards = []
            for selector in CARD_SELECTORS:
                try:
                    await page.wait_for_selector(selector, timeout=SELECTOR_TIMEOUT)
                    cards = await page.query_selector_all(selector)
                    if len(cards) > 0:
                        print(f"Использован селектор: {selector}")
                        break
                except:
                    continue
            
            if not cards:
                print("Не удалось найти карточки объявлений. Попытка сделать скриншот...")
                await page.screenshot(path=DEBUG_SCREENSHOT_FILENAME)
                return []
            
            await asyncio.sleep(SLEEP_AFTER_LOAD)
            print(f"Найдено {len(cards)} объявлений на странице")
            
            results = []
            for idx, card in enumerate(cards, 1):
                print(f"Парсинг объявления {idx}/{len(cards)}...")
                data = await self.parse_listing_card(card)
                if data:
                    results.append(data)
                    if idx <= 3:
                        print(f"  └─ offer_id: {data.get('offer_id', 'N/A')}")
                        print(f"  └─ title: {data.get('title', 'N/A')[:50]}...")
                        print(f"  └─ price: {data.get('price', 'N/A')}")
                        print(f"  └─ rooms: {data.get('rooms', 'N/A')}, area: {data.get('total_area', 'N/A')} м²")
                        print(f"  └─ floor: {data.get('floor', 'N/A')}/{data.get('floors_total', 'N/A')}")
                
                if idx % 5 == 0:
                    await self.human_like_delay(0.3, 0.7)
            
            return results
        except Exception as e:
            print(f"Ошибка при парсинге страницы: {e}")
            return []
    
    async def run(self, num_pages: int = 3):
        """entrypoint запуска парсера"""
        async with async_playwright() as p:
            print("Запуск браузера...")
            browser = await p.chromium.launch(
                headless=HEADLESS,
                slow_mo=SLOW_MO
            )
            
            context = await browser.new_context(
                viewport=BROWSER_VIEWPORT,
                user_agent=USER_AGENT,
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                permissions=['geolocation'],
                geolocation={'latitude': 55.7558, 'longitude': 37.6173},
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            page = await context.new_page()
            
            print("Начальная пауза перед запросами...")
            await self.human_like_delay(2.0, 5.0)
            
            for page_num in range(1, num_pages + 1):
                print(f"\n{'='*60}")
                print(f"Парсинг страницы {page_num} из {num_pages}")
                print(f"{'='*60}")
                
                url = self.build_url(page_num)
                print(f"Переход на: {url}")
                
                try:
                    await page.goto(url, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
                    
                    print("Имитация чтения страницы...")
                    await self.human_like_delay(2.0, 4.0)
                    
                    await self.random_mouse_movement(page)
                    await self.random_scroll(page)
                    
                    await self.human_like_delay(1.0, 2.0)
                    
                    page_data = await self.parse_page(page)
                    self.data.extend(page_data)
                    
                    print(f"Успешно спарсено {len(page_data)} объявлений со страницы {page_num}")
                    
                    if page_num < num_pages:
                        print("Пауза перед следующей страницей...")
                        await self.human_like_delay(
                            SLEEP_BETWEEN_PAGES, 
                            SLEEP_BETWEEN_PAGES + random.uniform(1.0, 3.0)
                        )
                        
                except Exception as e:
                    print(f"Ошибка при обработке страницы {page_num}: {e}")
                    print("Увеличенная пауза после ошибки...")
                    await self.human_like_delay(10.0, 20.0)
                    continue
            
            await browser.close()
            print(f"\n{'='*60}")
            print(f"Парсинг завершен. Всего собрано объявлений: {len(self.data)}")
            print(f"{'='*60}\n")
    
    def save_to_csv(self, filename: str = DEFAULT_CSV_FILENAME):
        """Сохраняет собранные данные в CSV файл"""
        if not self.data:
            print("Нет данных для сохранения!")
            return
        
        print(f"Сохранение данных в файл {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.data)
        
        print(f"Данные успешно сохранены в {filename}")
        print(f"Всего записей: {len(self.data)}")


async def main():
    parser = CianParser()
    await parser.run(num_pages=6)
    parser.save_to_csv("data/cian_data.csv")


if __name__ == "__main__":
    asyncio.run(main())

