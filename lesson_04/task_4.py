"""Получение топ-новостей с yandex."""
"""Выбирается блок по id=top-heading. внутри него 10 тэгов <a> (по 2 на новость). Первый отдает
название и ссылку, второй - время и источник."""

from datetime import date, timedelta
import time
from pprint import pprint
import requests
from lxml import html
import pymongo


def scrap_page(url: str, params: dict, headers: dict) -> str:
    """Базовый скраппер."""
    response = requests.get(url, params=params, headers=headers, stream=True)
    response.encoding = 'utf-8'
    if response.ok:
        return response.text
    else:
        raise Exception(f'Something is wrong with scrapping of {url}')

def get_another_date(days_quantity: int):
    """Возвращает дату, измененную на указанное количество дней."""
    today = date.today()
    another_date = today + timedelta(days=days_quantity)
    return another_date


def get_yavdex_news(db):
    url = 'https://yandex.ru/news/'
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) \
                              AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36'}

    params = {
        'x-consumed-content-encoding': 'gzip',
        'x-content-type-options': 'nosniff',
        'x-frame-options': 'DENY',
        'x-xss-protection': '1; mode=block'
    }

    collection = db.yandex_news
    collection.create_index([('link', pymongo.ASCENDING), ], unique=True)

    response = scrap_page(url=url, params=params, headers=headers)
    time.sleep(3)

    dom = html.fromstring(response)
    block = dom.xpath('//*[@id="top-heading"]/following-sibling::div/descendant::a')

    for i in range(len(block)):
        if i % 2 == 0:
            # Title & Link:
            print('0')
            title = block[i].xpath('./text()')[0]
            title = title.replace("\xa0", " ")
            link = block[i].xpath('./@href')[0]
            continue
        else:
            # Source & Date:
            source = block[i].xpath('./text()')[0]
            date_raw = block[i].xpath('./../following-sibling::span/text()')[0]
            date_str = str(date_raw)
            if 'вчера' in date_str.lower():
                publication = str(get_another_date(-1)) + ' ' + date_str
            else:
                publication = str(date.today()) + ' ' +  date_str

        # DB:
        document = {
            'title': title,
            'link': link,
            'source': source,
            'date': publication
        }
        collection.update_one(document, {'$set': document}, upsert=True)


if __name__ == '__main__':
    client = pymongo.MongoClient('localhost', 27017)
    db = client.news

    get_yavdex_news(db)
    print('Documents in collection: ', db.yandex_news.count_documents({}))

    result = db.yandex_news.find({})
    for doc in result:
        pprint(doc)

    # Удаление БД:
    # client.drop_database('news')
