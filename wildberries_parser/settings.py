from pathlib import Path

# Получаем абсолютный путь к корню проекта (WB_V1)
PROJECT_ROOT = Path(__file__).parent.parent
PHOTOS_DIR = PROJECT_ROOT / 'scrapy_data' / 'photos'
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

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

# Новый формат настроек экспорта
FEEDS = {
        'scrapy_data/photos/photos_%(product_id)s.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'fields': ['product_id', 'image_url', 'image_num', 'basket_num'],
        'overwrite': True
    }
}

# Настройки кеширования
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
    'wildberries_parser.pipelines.WildberriesPhotosPipeline': 400,
}

# Настройки для изображений
IMAGES_STORE = str(PROJECT_ROOT / 'scrapy_data' / 'photos')
IMAGES_THUMBS = {
    'small': (246, 328),
    'medium': (516, 688),
    'large': (800, 1066),
}

# Создаем директории при загрузке настроек
(PROJECT_ROOT / 'scrapy_data').mkdir(exist_ok=True)
(PROJECT_ROOT / 'scrapy_data' / 'photos').mkdir(exist_ok=True)
