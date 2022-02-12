import json
import re
import time
from datetime import date, timedelta
from pprint import pprint
from typing import List
import requests
from bs4 import BeautifulSoup


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


def main_sj(vacancy_name: str, start_page: int=1) -> List[dict]:
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

    vacancies_list = []
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
            vacancy_data = {}
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
            a_children = vacancy.find_all('a')
            if not a_children:
                continue

            # Title & link
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
                min_salary = ''.join(salary_list[:ind])
                max_salary = ''.join(salary_list[ind+1:-1])
            elif salary_str.startswith('от'):
                min_salary = ''.join(salary_list[1:-1])
            elif salary_str.startswith('до'):
                max_salary = ''.join(salary_list[1:-1])
            else:
                non_salary = True

            # Currency:
            regex = r'[\D+\\.]?$'
            if not non_salary and re.search(regex, salary_str):
                salary_currency = salary_list[-1]

            vacancy_data['vacancy'] = vacancy_title
            vacancy_data['min_salary'] = min_salary
            vacancy_data['max_salary'] = max_salary
            vacancy_data['currency'] = salary_currency
            vacancy_data['link'] = vacancy_link
            vacancy_data['date'] = vacancy_date
            vacancy_data['source_site'] = base_url
            vacancies_list.append(vacancy_data)

        flag = vacancy.parent.parent.parent.parent.parent.parent.parent.parent.find('span', text='Дальше')
        params['page'] += 1
    return vacancies_list


if __name__ == '__main__':
    vacancies = main_sj('Python', start_page=1)

    with open('sj.json', 'w') as f:
        json.dump(vacancies, f, indent=2, ensure_ascii=False)
