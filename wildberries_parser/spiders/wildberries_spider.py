import scrapy
from scrapy import signals
from scrapy.utils.project import get_project_settings
from urllib.parse import quote, urlencode
import re
from wildberries_parser.items import WildberriesProductItem
from wildberries_parser.spiders.base_spider import BaseSpider


class WildberriesSpider(BaseSpider):
    name = 'wildberries_v2'
    allowed_domains = ['search.wb.ru', 'www.wildberries.ru']
    custom_settings = {
        'RETRY_TIMES': 3,
        'DOWNLOAD_TIMEOUT': 15,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, queries=None, categories=None, pages=1, limit=100,
                 min_price=None, max_price=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wb_api_url = "https://search.wb.ru/exactmatch/ru/common/v13/search"
        self.queries = self._parse_input(queries)
        self.categories = self._parse_input(categories)
        self.pages = int(pages)
        self.limit = int(limit)
        self.settings = get_project_settings()

        # Обработка ценового диапазона
        self.price_range = self._validate_price_range(min_price, max_price)

    def _parse_input(self, input_str):
        if not input_str:
            return []
        return [item.strip() for item in input_str.split(',') if item.strip()]

    def _validate_price_range(self, min_price, max_price):
        """Валидация и преобразование ценового диапазона"""
        if min_price is None and max_price is None:
            return None

        try:
            min_kop = int(float(min_price or 0) * 100)
            max_kop = int(float(max_price or 9999999) * 100)

            if min_kop > max_kop:
                raise ValueError("Минимальная цена не может быть больше максимальной")

            return f"{min_kop};{max_kop}"
        except (ValueError, TypeError):
            raise ValueError("Цены должны быть числовыми значениями")

    def start_requests(self):
        """Генерация начальных запросов с учетом ценового фильтра"""
        if not self.queries:
            self.logger.error("No queries provided for spider!")
            return

        for query in self.queries:
            categories = self.categories if self.categories else [None]
            for category in categories:
                for page in range(1, self.pages + 1):
                    yield self.make_wb_request(
                        query=query,
                        category=category,
                        page=page
                    )

    def make_wb_request(self, query, category=None, page=1):
        """Формирование запроса к API Wildberries с учетом всех параметров"""
        params = {
            'ab_testing': 'false',
            'appType': 1,
            'curr': 'rub',
            'dest': -364763,
            'lang': 'ru',
            'page': page,
            'query': f'{{{query}}}',
            'resultset': 'catalog',
            'sort': 'popular',
            'spp': 30,
            'suppressSpellcheck': 'false',
        }

        # Добавляем ценовой фильтр если он задан
        if self.price_range:
            params['priceU'] = self.price_range

        if category:
            params['kind'] = category

        # Формирование URL с особым параметром hide_dtype
        base_url = f"{self.wb_api_url}?{urlencode(params)}"
        parts = base_url.split('&', 4)
        url = '&'.join(parts[:4] + ['hide_dtype=13'] + parts[4:])

        headers = {
            'User-Agent': self.settings.get('USER_AGENT'),
            'Accept': 'application/json',
            'Referer': 'https://www.wildberries.ru/',
        }

        return scrapy.Request(
            url=url,
            callback=self.parse_api_response,
            errback=self.handle_error,
            meta={
                'query': query,
                'category': category,
                'page': page
            },
            dont_filter=True
        )

    def parse_api_response(self, response):
        """Обработка ответа от API Wildberries"""
        try:
            data = response.json()
            products = data.get('data', {}).get('products', [])

            if not products:
                self.logger.warning(
                    f"No products found for query: {response.meta['query']} "
                    f"(page {response.meta['page']})"
                )
                return

            for product in products[:self.limit]:
                yield self.extract_product_data(
                    product,
                    response.meta['query'],
                    response.meta.get('category')
                )

        except ValueError as e:
            self.logger.error(f"Invalid JSON: {e}. Response: {response.text[:200]}")

    def extract_product_data(self, product_data, query, category=None):
        """Извлечение данных о продукте из ответа API"""
        size_data = product_data.get('sizes', [{}])[0]
        price_data = size_data.get('price', {})

        return WildberriesProductItem(
            product_id=product_data.get('id'),
            name=product_data.get('name'),
            brand=product_data.get('brand'),
            price=float(price_data.get('product', 0)) / 100,
            sale_price=float(price_data.get('basic', 0)) / 100,
            rating=product_data.get('reviewRating', 0),
            reviews_count=product_data.get('feedbacks', 0),
            query=query,
            category=category or product_data.get('entity'),
            seller_id=product_data.get('supplierId'),
            in_stock=product_data.get('totalQuantity', 0) > 0,
            url=f"https://www.wildberries.ru/catalog/{product_data['id']}/detail.aspx"
        )

    def handle_error(self, failure):
        """Обработка ошибок запросов"""
        self.logger.error(f"Request failed: {failure.value}")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.logger.info(f"Spider closed. Processed queries: {self.queries}")