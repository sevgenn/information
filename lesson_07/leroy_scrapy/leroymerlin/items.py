# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import MapCompose, TakeFirst, Compose


def process_price(raw_price: list) -> float|list:
    """Преобразует цену во float."""
    try:
        price = '.'.join(raw_price).replace(' ', '')
        return float(price)
    except Exception:
        return raw_price


def process_currency(raw_currency: list):
    """Обрабатывает валюту."""
    if '₽' in raw_currency:
        return raw_currency[0].replace('₽', 'руб')
    return raw_currency


def process_characteristics(raw_dict: dict) -> dict:
    """Обрабатывает характеристики."""
    char_dict = raw_dict[0]
    try:
        for k, v in char_dict.items():
            v = v.replace('\n', '').strip()
            char_dict[k] = v
    except Exception:
        pass
    return char_dict


class LeroymerlinItem(scrapy.Item):
    # define the fields for your item here like:
    _id = scrapy.Field()
    name = scrapy.Field(output_processor=TakeFirst())
    photos = scrapy.Field()
    link = scrapy.Field(output_processor=TakeFirst())
    price = scrapy.Field(input_processor=Compose(process_price), output_processor=TakeFirst())
    currency = scrapy.Field(input_processor=Compose(process_currency), output_processor=TakeFirst())
    characteristics = scrapy.Field(input_processor=Compose(process_characteristics), output_processor=TakeFirst())
