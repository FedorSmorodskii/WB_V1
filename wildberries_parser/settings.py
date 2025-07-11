# Добавьте/измените в settings.py
BOT_NAME = 'wildberries_parser'

SPIDER_MODULES = ['wildberries_parser.spiders']
NEWSPIDER_MODULE = 'wildberries_parser.spiders'

# Настройки для обхода блокировок
ROBOTSTXT_OBEY = False
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Настройки запросов
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1
DOWNLOAD_TIMEOUT = 30

FEED_FORMAT = 'json'
FEED_URI = '/home/fedor/PycharmProjects/WB_V1/scrapy_data/data.json'
FEED_EXPORT_ENCODING = 'utf-8'

# Настройки кеширования (отключено для отладки)
HTTPCACHE_ENABLED = False

# Настройки логирования
LOG_LEVEL = 'DEBUG'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
    'wildberries_parser.middlewares.CustomRetryMiddleware': 550,
    'wildberries_parser.middlewares.WildberriesParserDownloaderMiddleware': 543,
}

# Pipelines
ITEM_PIPELINES = {
    'wildberries_parser.pipelines.WildberriesPipeline': 300,
}