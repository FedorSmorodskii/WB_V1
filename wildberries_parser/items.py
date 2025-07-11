import scrapy


class WildberriesProductItem(scrapy.Item):
    # Основные поля товара
    product_id = scrapy.Field()  # ID товара
    name = scrapy.Field()  # Название товара
    brand = scrapy.Field()  # Бренд
    price = scrapy.Field()  # Текущая цена
    sale_price = scrapy.Field()  # Цена без скидки (если есть)
    rating = scrapy.Field()  # Рейтинг товара
    reviews_count = scrapy.Field()  # Количество отзывов
    query = scrapy.Field()  # Поисковый запрос
    category = scrapy.Field()  # Категория товара
    timestamp = scrapy.Field()  # Время парсинга

    # Дополнительные поля
    seller_id = scrapy.Field()  # ID продавца
    seller_name = scrapy.Field()  # Название продавца
    in_stock = scrapy.Field()  # Наличие товара
    url = scrapy.Field()  # URL товара
