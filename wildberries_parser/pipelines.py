import logging
from datetime import datetime

from itemadapter import ItemAdapter

from wildberries_parser.items import WildberriesProductDetailsItem


class WildberriesPipeline:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'processed': 0,
            'failed': 0,
            'processed_details': 0
        }

    def process_item(self, item, spider):
        try:
            # Добавляем timestamp
            item['timestamp'] = datetime.utcnow().isoformat()

            # Если есть ошибка, логируем но пропускаем item
            if 'error' in item:
                spider.logger.warning(f"Item with error: {item['error']}")
                return item

            # Проверяем минимально необходимые поля
            if not item.get('product_id'):
                raise ValueError("Missing product_id")

            return item

        except Exception as e:
            spider.logger.error(f"Pipeline error: {str(e)}")
            item['error'] = str(e)
            return item


    def close_spider(self, spider):
        """Действия при закрытии паука"""
        spider.logger.info(
            f"Pipeline stats - Products: {self.stats['processed']}, "
            f"Product details: {self.stats['processed_details']}, "
            f"Failed: {self.stats['failed']}"
        )