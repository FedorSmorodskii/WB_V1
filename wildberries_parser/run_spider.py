import os
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from wildberries_parser.spiders.wildberries_spider import WildberriesSpider
from wildberries_parser.spiders.product_details_spider import WildberriesProductDetailsSpider
from wildberries_parser.spiders.wildberries_photos_spider import WildberriesProductPhotosSpider

def run_spider(queries="ноутбук", categories=None, pages=2, limit=50,
               min_price=None, max_price=None, product_ids=None, download_photos=False):
    os.chdir(Path(__file__).parent.parent)
    process = CrawlerProcess(get_project_settings())

    if download_photos and product_ids:
        # Берем первый ID из списка для примера
        product_id = product_ids.split(',')[0].strip()
        process.crawl(
            WildberriesProductPhotosSpider,
            product_id=product_id
        )
    elif product_ids:
        process.crawl(
            WildberriesProductDetailsSpider,
            product_ids=product_ids
        )
    else:
        process.crawl(
            WildberriesSpider,
            queries=queries,
            categories=categories,
            pages=pages,
            limit=limit,
            min_price=min_price,
            max_price=max_price
        )

    process.start()

if __name__ == "__main__":
    run_spider(
        product_ids="251049101",
        download_photos=True
    )
