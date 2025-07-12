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


class WildberriesProductDetailsItem(scrapy.Item):
    product_id = scrapy.Field()  # ID товара (артикул)
    imt_id = scrapy.Field()
    nm_id = scrapy.Field()
    imt_name = scrapy.Field()
    slug = scrapy.Field()
    subj_name = scrapy.Field()
    subj_root_name = scrapy.Field()
    vendor_code = scrapy.Field()
    description = scrapy.Field()
    options = scrapy.Field()  # Все характеристики товара
    nm_colors_names = scrapy.Field()
    colors = scrapy.Field()
    contents = scrapy.Field()
    full_colors = scrapy.Field()
    selling = scrapy.Field()  # Информация о продавце
    media = scrapy.Field()  # Медиа контент
    data = scrapy.Field()  # Дополнительные данные
    grouped_options = scrapy.Field()  # Сгруппированные характеристики
    timestamp = scrapy.Field()  # Время парсинга

