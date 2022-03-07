# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import hashlib

from itemadapter import ItemAdapter
import scrapy
from scrapy.pipelines.images import ImagesPipeline
import pymongo
from scrapy.utils.python import to_bytes
from pprint import pprint


class LeroymerlinPipeline:
    def __init__(self):
        client = pymongo.MongoClient('localhost', 27017)
        self.db = client.photos

    def process_item(self, item, spider):
        collection = self.db[spider.name]
        collection.insert_one(item)
        return item


class LeroymerlinPhotosPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if item['photos']:
            for photo in item['photos']:
                try:
                    yield scrapy.Request(photo)
                except Exception as err:
                    print(err)

    def item_completed(self, results, item, info):
        item['photos'] = [el[1] for el in results if el[0]]
        return item

    def file_path(self, request, response=None, info=None, *, item=None):
        sub_dir = item['name'].replace('/', '_')
        image_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
        return f'full/{sub_dir}/{image_guid}.jpeg'
