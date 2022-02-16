"""SuperJob"""
"""insert_one(). Контроль ключей через pymongo.errors"""

import re
import time
from datetime import date, timedelta
from pprint import pprint

import requests
from bs4 import BeautifulSoup
import pymongo
from pymongo.errors import DuplicateKeyError as dke


def scrap_page(url: str, params: dict, headers: dict) -> bytes:
    """Базовый скраппер."""
    response = requests.get(url, params=params, headers=headers, stream=True)
    response.encoding = 'utf-8'
    if response.ok:
        return response.content
    else:
        raise Exception(f'Something is wrong with scrapping of {url}')


def parse_page(html: bytes, vacancy_selector):
    """Базовый парсер."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.select(vacancy_selector)


def get_another_date(days_quantity: int):
    """Возвращает дату, измененную на указанное количество дней."""
    today = date.today()
    another_date = today + timedelta(days=days_quantity)
    return another_date


def main_sj(vacancy_name: str, db, start_page: int=1) -> None:
    """Основной обработчик, возвращающий список словарей."""
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36'}
    base_url = 'https://www.superjob.ru'
    search_url = base_url + '/vacancy/search'
    params = {
        'keywords': vacancy_name,
        'page': start_page
    }
    base_selector = 'div.f-test-search-result-item'
    collection = db[vacancy_name]

    flag = True
    while flag:
        try:
            response = scrap_page(search_url, params=params, headers=headers)
        except Exception:
            print('Try again')
            break
        time.sleep(3)
        vacancies_block = parse_page(response, base_selector)

        for vacancy in vacancies_block:
            # Невалидные тэги:
            exceptions = vacancy.find_all('div', {'class': ['f-test-vacancy-subscription-card', 'swiper-container']})
            if exceptions:
                continue

            # Date:
            temp = vacancy.find('span', text=' • ')
            if temp:
                vacancy_date = temp.previous_sibling.getText()
                if vacancy_date == 'Вчера':
                    yesterday = get_another_date(-1)
                    vacancy_date = f'{yesterday:%d %B %Y}'
                elif ':' in vacancy_date:
                    vacancy_date = f'{date.today():%d %B %Y}'
            else:
                vacancy_date = None

            # Title & link
            a_children = vacancy.find_all('a')
            if not a_children:
                continue

            temp_data = a_children[0]
            if temp_data == '':
                continue
            vacancy_link = base_url + temp_data['href']
            vacancy_title = temp_data.getText()

            # Salary & currency:
            base_span = temp_data.parent
            salary_span = base_span.next_sibling.next
            salary_str = salary_span.getText()
            salary_list = salary_str.split('\xa0')

            min_salary = None
            max_salary = None
            salary_currency = None
            # Salary:
            non_salary = False
            if '—' in salary_str:
                ind = salary_list.index('—')
                min_salary = int(''.join(salary_list[:ind]))
                max_salary = int(''.join(salary_list[ind+1:-1]))
            elif salary_str.startswith('от'):
                min_salary = int(''.join(salary_list[1:-1]))
            elif salary_str.startswith('до'):
                max_salary = int(''.join(salary_list[1:-1]))
            else:
                non_salary = True

            # Currency:
            regex = r'[\D+\\.]?$'
            if not non_salary and re.search(regex, salary_str):
                salary_currency = salary_list[-1]

            # Employer:
            employer = vacancy.find('span', {'class': 'f-test-text-vacancy-item-company-name'})
            try:
                employer_title = employer.getText()
            except Exception:
                employer_title = None

            document = {
                "vacancy": vacancy_title,
                "min_salary": min_salary,
                "max_salary": max_salary,
                "currency": salary_currency,
                "link": vacancy_link,
                "date": vacancy_date,
                "employer": employer_title,
                "source_site": base_url
            }

            try:
                collection.insert_one(document)
            except dke:
                print('Duplicate key error collection')
            except Exception:
                print('Something else...')

        flag = vacancy.parent.parent.parent.parent.parent.parent.parent.parent.find('span', text='Дальше')
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
    db = client['vacancies_sj']
    VACANCY_NAME = 'Python'
    START_PAGE = 1

    # Сбор вакансий:
    vacancies = main_sj(vacancy_name=VACANCY_NAME, db=db, start_page=START_PAGE)
    print('Documents in collection: ', db.Python.count_documents({}))

    # Вывод вакансий по условию:
    MIN_LIMIT = 150000
    result = find_by_salary(db.Python, minimum=MIN_LIMIT)
    for doc in result:
        pprint(doc)

    # Очистка коллекции:
    # db.Python.drop()
