import scrapy
from scrapy import Request


class WildberriesProductPhotosSpider(scrapy.Spider):
    name = 'wb_product_photos'
    custom_settings = {
        'FEEDS': {
            'scrapy_data/photos/photos_%(product_id)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'store_empty': False,
                'fields': ['product_id', 'image_url', 'image_num', 'basket_num'],
                'overwrite': True,
                'indent': 2,
                'ensure_ascii': False
            }
        },
        'ITEM_PIPELINES': {
            'wildberries_parser.pipelines.WildberriesPipeline': 300,
        },
        'CONCURRENT_REQUESTS': 30,  # Оптимальное количество параллельных запросов
        'DOWNLOAD_DELAY': 0.1,  # Небольшая задержка между запросами
    }

    def __init__(self, product_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product_id = str(product_id).strip()
        self.image_sizes = ['c516x688']
        self.photo_count = 0
        self.active_basket = None  # Текущая активная корзина с найденными фото

    def start_requests(self):
        # Сначала проверяем первые фото во всех корзинах
        for basket_num in range(1, 30):
            base_url = self._generate_base_url(basket_num)
            url = f"{base_url}/{self.image_sizes[0]}/1.webp"
            yield Request(
                url=url,
                callback=self.parse_first_photo,
                meta={'basket_num': basket_num, 'base_url': base_url},
                dont_filter=True
            )

    def _generate_base_url(self, basket_num):
        return f"https://basket-{basket_num:02d}.wbbasket.ru/vol{self.product_id[:4]}/part{self.product_id[:6]}/{self.product_id}/images"

    def parse_first_photo(self, response):
        if response.status != 200:
            self.logger.debug(f"First photo not found in basket {response.meta['basket_num']}")
            return

        basket_num = response.meta['basket_num']
        base_url = response.meta['base_url']

        # Запоминаем активную корзину
        self.active_basket = basket_num
        self.logger.info(f"Found active basket: {basket_num}")

        # Обрабатываем найденное первое фото
        yield self._create_photo_item(response.url, 1, basket_num)

        # Запускаем проверку следующих фото в этой корзине
        for img_num in range(2, 11):  # Проверяем фото с 2 по 10
            next_url = f"{base_url}/{self.image_sizes[0]}/{img_num}.webp"
            yield Request(
                url=next_url,
                callback=self.parse_subsequent_photo,
                meta={'img_num': img_num, 'basket_num': basket_num},
                dont_filter=True
            )

    def parse_subsequent_photo(self, response):
        if response.status != 200:
            self.logger.debug(f"Photo {response.meta['img_num']} not found in basket {response.meta['basket_num']}")
            return

        yield self._create_photo_item(response.url, response.meta['img_num'], response.meta['basket_num'])

    def _create_photo_item(self, url, img_num, basket_num):
        self.photo_count += 1
        return {
            'product_id': self.product_id,
            'image_url': url,
            'image_num': img_num,
            'basket_num': basket_num
        }

    def closed(self, reason):
        if reason == 'finished':
            self.logger.info(f"Found {self.photo_count} photos for product {self.product_id}")