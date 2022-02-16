"""HH.ru"""

import re
import time
from pprint import pprint

import requests
from bs4 import BeautifulSoup
import pymongo
from pymongo.errors import DuplicateKeyError as dke

# vacancy_name
# salary: min, max, currency
# vacancy_link
# vacancy_date
# employer
# site_link


def scrap_page(base_url: str, params: dict, headers: dict) -> bytes:
    response = requests.get(base_url, params=params, headers=headers, stream=True)
    response.encoding = 'utf-8'
    if response.ok:
        return response.content
    else:
        raise Exception(f'Something is wrong with scrapping of {base_url}')


def parse_page(html: bytes, selector: str):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.select(selector)


def get_salary_hh(salary_str: str, salary_list: list) -> tuple:
    """Парсит минимальную и максимальную з/п в строке и преобразует в кортеж чисел."""
    if salary_str.startswith('от'):
        min_salary = int(salary_list[1].replace('\u202f', ''))
        max_salary = None
    elif salary_str.startswith('до'):
        min_salary = None
        max_salary = int(salary_list[1].replace('\u202f', ''))
    else:
        min_salary = int(salary_list[0].replace('\u202f', ''))
        max_salary = int(salary_list[2].replace('\u202f', ''))
    return min_salary, max_salary


def get_currency_hh(salary_str: str, salary_list: list) -> [str, None]:
    """Извлекает наименование валюты."""
    regex = r'[\D+\\.?]$'
    if re.search(regex, salary_str):
        salary_currency = salary_list[-1]
    else:
        salary_currency = None
    return salary_currency


def main_hh(vacancy_name: str, db, start_page: int=0) -> None:
    """Основной обработчик."""
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36'}
    base_url = 'https://hh.ru'
    search_url = base_url + '/search/vacancy'
    params = {
        'text': vacancy_name,
        'search_field': 'name',
        'area': 1,  # city code
        'page': start_page,
        'items_on_page': 20,
    }
    base_selector = 'div.vacancy-serp-item'

    collection = db[vacancy_name]
    collection.create_index([('vacancy', pymongo.ASCENDING),
                             ('employer', pymongo.ASCENDING),
                             ('date', pymongo.ASCENDING)], unique=True)

    flag = True
    while flag:
        response = None
        for i in range(1, 4):
            try:
                response = scrap_page(search_url, params=params, headers=headers)
                break
            except Exception:
                print(f'<Attempt {i} failed>')
                time.sleep(3)
        if not response:
            print('Try again!')
            break

        time.sleep(3)
        vacancies_block = parse_page(response, base_selector)
        for vacancy in vacancies_block:
            # Title & link:
            data = vacancy.find('a', {'data-qa': 'vacancy-serp__vacancy-title'})
            vacancy_title = data.getText()
            link = data['href'].split('?')
            vacancy_link = link[0]

            # Date:
            try:
                date = vacancy.find('span', {'data-qa': 'vacancy-serp__vacancy-date'})
                vacancy_date = date.getText().replace(' ', ' ')
            except Exception:
                print(f"Attention. For {vacancy_title} - no date")
                vacancy_date = None

            # Salary:
            salary = vacancy.find('span', {'data-qa': 'vacancy-serp__vacancy-compensation'})
            try:
                salary_str = salary.getText()
                salary_list = salary_str.split(' ')
                salary_currency = get_currency_hh(salary_str, salary_list)

                salary_fork = get_salary_hh(salary_str, salary_list)
                min_salary = salary_fork[0]
                max_salary = salary_fork[1]
            except Exception:
                min_salary = None
                max_salary = None
                salary_currency = None

            # Employer:
            employer_data = vacancy.find('a', {'data-qa': 'vacancy-serp__vacancy-employer'})
            try:
                employer = employer_data.getText().replace(' ', ' ')
            except Exception:
                employer = None

            document = {
                "vacancy": vacancy_title,
                "min_salary": min_salary,
                "max_salary": max_salary,
                "currency": salary_currency,
                "link": vacancy_link,
                "date": vacancy_date,
                "employer": employer,
                "source_site": base_url
            }

            try:
                collection.update_one(document, {'$set': document}, upsert=True)
            except dke:
                print('Duplicate key error collection')

        flag = vacancy.parent.parent.find('span', text='дальше')
        params['page'] += 1
    print('<DONE>')


def find_by_salary(collection, minimum: int):
    """Возвращает список с з/п больше указанной."""
    rates = get_rate()
    euro_rate = rates['euro']
    usd_rate = rates['dollar']

    statement = {'$gt': minimum}
    statement_dollar = {'$gt': minimum / usd_rate}
    statement_euro = {'$gt': minimum / euro_rate}
    return collection.find({'$or':
                    [
                    {'currency': 'руб.', '$or': [{'min_salary': statement}, {'max_salary': statement}]},
                    {'currency': 'USD', '$or': [{'min_salary': statement_dollar}, {'max_salary': statement_dollar}]},
                    {'currency': 'EUR', '$or': [{'min_salary': statement_euro}, {'max_salary': statement_euro}]}
                     ]
                })


def get_rate() -> dict:
    """Возвращает курсы EUR, USD с сайта ЦБ."""
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36',
               'x-aspnet-version': '4.0.30319',
               'x-aspnetmvc-version': '5.2',
               'x-frame-options': 'SAMEORIGIN',
               'x-powered-by': 'ASP.NET'}

    response = scrap_page('https://www.cbr.ru/currency_base/daily/', params={}, headers=headers)
    time.sleep(3)
    soup = BeautifulSoup(response, 'html.parser')
    currencies_block = soup.find('table', {'class': 'data'})
    # EURO
    euro_block = currencies_block.find('td', text='EUR')
    euro_parent = euro_block.parent
    euro = float(euro_parent.findChildren(recursive=False)[-1].getText().replace(',', '.'))
    # USD
    dollar_block = currencies_block.find('td', text='USD')
    dollar_parent = dollar_block.parent
    dollar = float(dollar_parent.findChildren(recursive=False)[-1].getText().replace(',', '.'))

    return {'euro': euro, 'dollar': dollar}


if __name__ == '__main__':
    client = pymongo.MongoClient('localhost', 27017)
    db = client['vacancies_hh']
    VACANCY_NAME = 'Python'
    START_PAGE = 0

    # Сбор вакансий:
    vacancies = main_hh(vacancy_name=VACANCY_NAME, db=db, start_page=START_PAGE)
    print('Documents in collection: ', db.Python.count_documents({}))

    # Вывод вакансий по условию:
    MIN_LIMIT = 500000
    result = find_by_salary(db.Python, minimum=MIN_LIMIT)
    for doc in result:
        pprint(doc)

    # Очистка коллекции:
    # db.Python.delete_many({})
