from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from wildberries_parser.spiders.wildberries_spider import WildberriesSpider


def run_spider(queries="ноутбук", categories=None, pages=2, limit=50):
    process = CrawlerProcess(get_project_settings())

    process.crawl(
        WildberriesSpider,
        queries=queries,
        categories=categories,
        pages=pages,
        limit=limit
    )

    process.start()


if __name__ == "__main__":
    # Пример запуска:
    # Парсинг ноутбуков и телефонов, по 2 страницы для каждого
    run_spider(queries="ноутбук, смартфон", pages=2)