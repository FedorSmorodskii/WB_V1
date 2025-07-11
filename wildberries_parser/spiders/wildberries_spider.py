import scrapy
from scrapy import signals
from scrapy.utils.project import get_project_settings

from wildberries_parser.items import WildberriesProductItem
from wildberries_parser.spiders.base_spider import BaseSpider
from urllib.parse import quote, urlencode


class WildberriesSpider(BaseSpider):
    name = 'wildberries_v2'
    allowed_domains = ['search.wb.ru', 'www.wildberries.ru']

    def __init__(self, queries=None, categories=None, pages=1, limit=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wb_api_url = "https://search.wb.ru/exactmatch/ru/common/v13/search"
        self.queries = self._parse_input(queries)
        self.categories = self._parse_input(categories)
        self.pages = int(pages)
        self.limit = int(limit)
        self.settings = get_project_settings()

    def _parse_input(self, input_str):
        if not input_str:
            return []
        return [item.strip() for item in input_str.split(',') if item.strip()]

    async def start(self):
        """Генерация начальных запросов"""
        if not self.queries:
            self.logger.error("No queries provided for spider!")
            return

        for query in self.queries:
            categories = self.categories if self.categories else [None]
            for category in categories:
                for page in range(1, self.pages + 1):
                    yield self.make_wb_request(query=query, category=category, page=page)

    def handle_error(self, failure):
        """Обработка ошибок запросов"""
        self.logger.error(f"Request failed: {failure.value}")

    def make_wb_request(self, query, category=None, page=1):
        params = {
            'ab_testing': 'false',
            'appType': 1,
            'curr': 'rub',
            'dest': -364763,
            'lang': 'ru',
            'page': page,
            'query': f'{{{query}}}',  # Wrap the query in curly braces
            'resultset': 'catalog',
            'sort': 'popular',
            'spp': 30,
            'suppressSpellcheck': 'false',
        }

        if category:
            params['kind'] = category

        # Костыль: сначала формируем базовый URL, затем добавляем hide_dtype
        # Формируем базовый URL
        base_url = f"{self.base_url}?{urlencode(params)}"
        # Вставляем hide_dtype после 4-го параметра
        parts = base_url.split('&', 4)
        url = '&'.join(parts[:4] + ['hide_dtype=13'] + parts[4:])

        self.logger.debug(f"Final URL: {url}")  # Для отладки

        headers = {
            'User-Agent': self.settings.get('USER_AGENT'),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Origin': 'https://www.wildberries.ru',
            'Referer': 'https://www.wildberries.ru/',
        }

        return scrapy.Request(
            url=url,
            method='GET',
            headers=headers,
            callback=self.parse_api_response,
            errback=self.handle_error,
            meta={'query': query, 'category': category, 'page': page},
            dont_filter=True
        )

    def parse_api_response(self, response):
        try:
            data = response.json()
            # self.logger.debug(f"API Response: {data}")

            if not data.get('data', {}).get('products'):
                self.logger.warning(f"No products found for query: {response.meta['query']}")
                return

            for product in data['data']['products'][:self.limit]:
                yield self.extract_product_data(product, response.meta['query'], response.meta.get('category'))

        except ValueError as e:
            self.logger.error(f"Invalid JSON: {e}. Response: {response.text[:200]}")

    def extract_product_data(self, product_data, query, category=None):
        # Get the first size option (assuming there's at least one)
        size_data = product_data.get('sizes', [{}])[0]
        price_data = size_data.get('price', {})

        return WildberriesProductItem(
            product_id=product_data.get('id'),
            name=product_data.get('name'),
            brand=product_data.get('brand'),
            # Using 'basic' as regular price and 'product' as sale price
            price=float(price_data.get('product', 0)) / 100 if price_data.get('product') else None,
            sale_price=float(price_data.get('basic', 0)) / 100,
            rating=product_data.get('reviewRating', 0),
            reviews_count=product_data.get('feedbacks', 0),
            query=query,
            category=product_data.get('entity'),
            seller_id=product_data.get('supplierId'),
            # Using totalQuantity for stock availability
            in_stock=product_data.get('totalQuantity', 0) > 0,
            url=f"https://www.wildberries.ru/catalog/{product_data['id']}/detail.aspx"
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        self.logger.info(f"Spider closed. Queries: {self.queries}")