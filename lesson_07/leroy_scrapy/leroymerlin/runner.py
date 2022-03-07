from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from leroymerlin import settings
from leroymerlin.spiders.leroy import LeroySpider


if __name__ == '__main__':
    crawler_settings = Settings()
    crawler_settings.setmodule(settings)

    process = CrawlerProcess(settings=crawler_settings)
    search = 'ковер'
    process.crawl(LeroySpider, search=search)
    process.start()
