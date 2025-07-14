import scrapy
from urllib.parse import urljoin
from wildberries_parser.items import WildberriesProductDetailsItem


class WildberriesProductDetailsSpider(scrapy.Spider):
    name = 'wb_product_details'
    custom_settings = {
        'ITEM_PIPELINES': {
            'wildberries_parser.pipelines.WildberriesPipeline': 300,
        },
        'DOWNLOAD_TIMEOUT': 30,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 404],
        'CONCURRENT_REQUESTS': 16,  # Оптимальное количество параллельных запросов
        'DOWNLOAD_DELAY': 0.1,  # Небольшая задержка между запросами
    }

    def __init__(self, product_ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_ids = self._parse_product_ids(product_ids)

    def _parse_product_ids(self, product_ids):
        if not product_ids:
            return []
        return [pid.strip() for pid in product_ids.split(',') if pid.strip()]

    def start_requests(self):
        for product_id in self.product_ids:
            # Пробуем несколько basket-серверов
            for basket_num in range(1, 11):
                url = self._build_details_url(product_id, basket_num)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_details,
                    errback=self.errback,
                    meta={
                        'product_id': product_id,
                        'basket_num': basket_num,
                        'retry_times': 0,
                        'handle_httpstatus_list': [404]
                    },
                    dont_filter=True
                )

    def _build_details_url(self, product_id, basket_num):
        return f"https://basket-{basket_num:02d}.wbbasket.ru/vol{product_id[:4]}/part{product_id[:6]}/{product_id}/info/ru/card.json"

    def parse_details(self, response):
        product_id = response.meta['product_id']
        if response.status == 404:
            self.logger.warning(f"Product {product_id} not found on basket-{response.meta['basket_num']}")
            return

        try:
            data = response.json()
            if not data:
                raise ValueError("Empty response data")

            item = self._create_item(product_id, data)
            yield item

        except Exception as e:
            self.logger.error(f"Failed to parse details for {product_id}: {str(e)}")

    def _create_item(self, product_id, data):
        item = WildberriesProductDetailsItem()
        item['product_id'] = product_id

        # Основные поля
        fields = ['imt_id', 'nm_id', 'imt_name', 'slug', 'subj_name',
                  'subj_root_name', 'vendor_code', 'description']
        for field in fields:
            if field in data:
                item[field] = data[field]

        # Если нет imt_id, создаем временный
        if 'imt_id' not in item:
            item['imt_id'] = f"temp_{product_id}"

        return item
