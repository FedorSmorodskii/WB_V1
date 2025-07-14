import scrapy

class WildberriesProductItem(scrapy.Item):
    product_id = scrapy.Field()
    name = scrapy.Field()
    brand = scrapy.Field()
    price = scrapy.Field()
    sale_price = scrapy.Field()
    rating = scrapy.Field()
    reviews_count = scrapy.Field()
    query = scrapy.Field()
    category = scrapy.Field()
    timestamp = scrapy.Field()
    seller_id = scrapy.Field()
    seller_name = scrapy.Field()
    in_stock = scrapy.Field()
    url = scrapy.Field()

class WildberriesProductDetailsItem(scrapy.Item):
    product_id = scrapy.Field()
    imt_id = scrapy.Field()
    nm_id = scrapy.Field()
    imt_name = scrapy.Field()
    slug = scrapy.Field()
    subj_name = scrapy.Field()
    subj_root_name = scrapy.Field()
    vendor_code = scrapy.Field()
    description = scrapy.Field()
    options = scrapy.Field()
    nm_colors_names = scrapy.Field()
    colors = scrapy.Field()
    contents = scrapy.Field()
    full_colors = scrapy.Field()
    selling = scrapy.Field()



class WildberriesProductPhotosItem(scrapy.Item):
    product_id = scrapy.Field()
    image_url = scrapy.Field()
    image_num = scrapy.Field()
    basket_num = scrapy.Field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Удаляем timestamp, чтобы он не попадал в вывод
        if 'timestamp' in self:
            del self['timestamp']