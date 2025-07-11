from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import time
import random

class CustomRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if response.status in [429, 403]:
            retry_after = random.randint(5, 15)
            spider.logger.warning(f"Rate limited or forbidden. Waiting {retry_after} seconds.")
            time.sleep(retry_after)
            return self._retry(request, response.status, spider) or response
        return super().process_response(request, response, spider)

class WildberriesParserDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request, spider):
        if 'search.wb.ru' in request.url:
            request.headers.update({
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Origin': 'https://www.wildberries.ru',
                'Referer': 'https://www.wildberries.ru/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
            })
        return None

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)