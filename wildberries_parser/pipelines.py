import logging
from datetime import datetime
from pathlib import Path
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from itemadapter import ItemAdapter

class WildberriesPipeline:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # def process_item(self, item, spider):
    #     item['timestamp'] = datetime.utcnow().isoformat()
    #     return item

class WildberriesPhotosPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if 'image_url' in item:
            yield Request(item['image_url'], meta={'product_id': item['product_id']})

    def file_path(self, request, response=None, info=None, *, item=None):
        product_id = request.meta['product_id']
        image_name = request.url.split('/')[-1]
        return f'{product_id}/{image_name}'


