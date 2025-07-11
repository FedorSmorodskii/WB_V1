import scrapy
from urllib.parse import quote, urlencode
from wildberries_parser.items import WildberriesProductItem


class BaseSpider(scrapy.Spider):
    name = 'wb_spider'
    allowed_domains = ['search.wb.ru']
    custom_settings = {
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DOWNLOAD_TIMEOUT': 15,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    def __init__(self, queries=None, min_price=None, max_price=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://search.wb.ru/exactmatch/ru/common/v13/search"
        self.queries = [q.strip() for q in queries.split(',')] if queries else []

        # Преобразуем рубли в копейки и формируем priceU
        if min_price is not None and max_price is not None:
            self.price_range = f"{int(float(min_price) * 100)};{int(float(max_price) * 100)}"
        else:
            self.price_range = None

    def start_requests(self):
        for query in self.queries:
            url = self.build_search_url(query)
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'query': query},
                headers=self.get_headers()
            )

    def build_search_url(self, query, page=1):
        params = {
            'TestGroup': 'no_test',
            'TestID': 'no_test',
            'appType': 1,
            'curr': 'rub',
            'dest': -1257786,
            'filters': 'xsubject',
            'lang': 'ru',
            'locale': 'ru',
            'page': page,
            'query': f'{{{query}}}',
            'resultset': 'catalog',
            'sort': 'popular',
            'spp': 30,
            'suppressSpellcheck': 'false',
        }

        if self.price_range:
            params['priceU'] = self.price_range

        base_url = f"{self.base_url}?{urlencode(params)}"
        parts = base_url.split('&', 4)
        return '&'.join(parts[:4] + ['hide_dtype=13'] + parts[4:])

    def get_headers(self):
        return {
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9',
            'Referer': 'https://www.wildberries.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }

    def parse(self, response):
        data = response.json()
        products = data.get('data', {}).get('products', [])

        if not products:
            self.logger.warning(f"No products found for query: {response.meta['query']}")
            return

        for product in products:
            yield self.extract_product(product, response.meta['query'])

    def extract_product(self, product_data, query):
        return WildberriesProductItem(
            product_id=product_data.get('id'),
            name=product_data.get('name'),
            brand=product_data.get('brand'),
            price=product_data.get('salePriceU', 0) / 100,
            sale_price=product_data.get('priceU', 0) / 100,
            rating=product_data.get('reviewRating'),
            reviews_count=product_data.get('feedbacks'),
            query=query,
            url=f"https://www.wildberries.ru/catalog/{product_data.get('id')}/detail.aspx"
        )