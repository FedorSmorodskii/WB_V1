from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from wildberries_parser.spiders.wildberries_spider import WildberriesSpider


def run_spider(queries="ноутбук", categories=None, pages=2, limit=50,
               min_price=None, max_price=None):
    """
    Запуск парсера Wildberries с указанными параметрами

    :param queries: Список запросов через запятую (например: "ноутбук, смартфон")
    :param categories: Категории товаров (опционально)
    :param pages: Количество страниц для парсинга (по умолчанию 2)
    :param limit: Максимальное количество товаров на странице (по умолчанию 50)
    :param min_price: Минимальная цена в рублях (опционально)
    :param max_price: Максимальная цена в рублях (опционально)
    """
    process = CrawlerProcess(get_project_settings())

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
    # Пример 1: Парсинг ноутбуков и телефонов в ценовом диапазоне 20,000-100,000 руб
    run_spider(
        queries="ноутбук, смартфон",
        pages=3,
        min_price=20000,
        max_price=100000
    )

    # Пример 2: Парсинг только дорогих ноутбуков (от 80,000 руб)
    # run_spider(
    #     queries="ноутбук игровой",
    #     pages=2,
    #     min_price=80000
    # )

    # Пример 3: Парсинг дешевых товаров (до 5,000 руб) в категории электроника
    # run_spider(
    #     queries="наушники",
    #     categories="elektronika",
    #     max_price=5000
    # )