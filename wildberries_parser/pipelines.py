import logging
from itemadapter import ItemAdapter
from datetime import datetime


class WildberriesPipeline:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'processed': 0,
            'failed': 0,
        }

    def process_item(self, item, spider):
        """Обработка каждого item"""
        try:
            adapter = ItemAdapter(item)

            # Добавляем timestamp
            adapter['timestamp'] = datetime.utcnow().isoformat()

            # Валидация обязательных полей
            if not adapter.get('product_id'):
                raise ValueError("Missing product_id")

            if not adapter.get('name'):
                raise ValueError("Missing product name")

            # Логирование успешной обработки
            self.stats['processed'] += 1
            if self.stats['processed'] % 100 == 0:
                spider.logger.info(f"Processed {self.stats['processed']} items")

            return item

        except Exception as e:
            self.stats['failed'] += 1
            spider.logger.error(f"Failed to process item: {e}", exc_info=True)
            raise

    def close_spider(self, spider):
        """Действия при закрытии паука"""
        spider.logger.info(
            f"Pipeline stats - Processed: {self.stats['processed']}, "
            f"Failed: {self.stats['failed']}"
        )