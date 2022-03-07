import scrapy
from scrapy.http import HtmlResponse
from scrapy.loader import ItemLoader

from leroymerlin.items import LeroymerlinItem


class LeroySpider(scrapy.Spider):
    name = 'leroy'
    allowed_domains = ['leroymerlin.ru']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [f'https://leroymerlin.ru/search/?q={kwargs.get("search")}/']

    def parse(self, response: HtmlResponse):
        page = response.xpath('//a[@data-qa-pagination-item="right"]/@href').get()
        if page:
            yield response.follow(page, callback=self.parse)
        links = response.xpath('//a[@data-qa="product-image"]')
        for link in links:
            yield response.follow(link, callback=self.parse_ads)

    def parse_ads(self, response: HtmlResponse):
        loader = ItemLoader(item=LeroymerlinItem(), response=response)
        loader.add_xpath('name', '//h1[@slot="title"]/text()')
        loader.add_xpath('price',
                         '//*[@slot="primary-price"]/span[@slot="price"]/text() | '
                         '//*[@slot="primary-price"]/span[@slot="fract"]/text()')
        loader.add_xpath('currency', '//span[@slot="currency"]/text()')
        loader.add_value('link', response.url)
        loader.add_xpath('photos', '//picture[@slot="pictures"]/source[1]/@data-origin')

        character_key = response.xpath('//dt/text()').getall()
        character_value = response.xpath('//dd/text()').getall()
        characteristics = dict(zip(character_key, character_value))
        loader.add_value('characteristics', characteristics)

        yield loader.load_item()
