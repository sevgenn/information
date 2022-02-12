import json
import re
import time
from typing import List

import requests
from bs4 import BeautifulSoup
from pprint import pprint

# vacancy_name
# salary: min, max, currency
# vacancy_link
# site_link


def scrap_page(base_url: str, params: dict, headers: dict) -> bytes:
    response = requests.get(base_url, params=params, headers=headers, stream=True)
    response.encoding = 'utf-8'
    if response.ok:
        return response.content
    else:
        raise Exception(f'Something is wrong with scrapping of {base_url}')

def parse_page(html: bytes, vacancy_selector):
    soup = BeautifulSoup(html, 'html.parser')
    return soup.select(vacancy_selector)


VACANCY_NAME = 'Python'
PAGE = 0


def main_hh(vacancy_name: str, start_page: int=1) -> List[dict]:
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
        'items_on_page': 100,
    }
    base_selector = 'div.vacancy-serp-item'

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
            # Title & link:
            data = vacancy.find('a', {'data-qa': 'vacancy-serp__vacancy-title'})
            vacancy_title = data.getText()
            link = data['href'].split('?')
            vacancy_link = link[0]

            # Date:
            try:
                date = vacancy.find('span', {'data-qa': 'vacancy-serp__vacancy-date'})
                vacancy_date = date.getText()
            except Exception:
                print(f'Attention. Page {PAGE} - no date')
                vacancy_date = None

            # Salary:
            salary = vacancy.find('span', {'data-qa': 'vacancy-serp__vacancy-compensation'})
            try:
                salary_str = salary.getText()
                salary_list = salary_str.split(' ')
                regex = r'[\D+\\.]?$'
                if re.search(regex, salary_str):
                    salary_currency = salary_list[-1]
                else:
                    salary_currency = None
                if salary_str.startswith('от'):
                    min_salary = salary_list[1].replace('\u202f', ' ')
                    max_salary =None
                elif salary_str.startswith('до'):
                    min_salary = None
                    max_salary = salary_list[1].replace('\u202f', ' ')
                else:
                    min_salary = salary_list[0].replace('\u202f', ' ')
                    max_salary = salary_list[2].replace('\u202f', ' ')
            except Exception:
                min_salary = None
                max_salary = None
                salary_currency = None

            # salary_data = {}
            # salary_data['min'] = min_salary
            # salary_data['max'] = max_salary
            # salary_data['currency'] = salary_currency

            vacancy_data['vacancy'] = vacancy_title
            # vacancy_data['salary'] = salary_data
            vacancy_data['min_salary'] = min_salary
            vacancy_data['max_salary'] = max_salary
            vacancy_data['currency'] = salary_currency
            vacancy_data['link'] = vacancy_link
            vacancy_data['date'] = vacancy_date
            vacancy_data['source_site'] = base_url
            vacancies_list.append(vacancy_data)

        flag = vacancy.parent.parent.find('span', text='дальше')
        params['page'] += 1
    return vacancies_list


if __name__ == '__main__':
    vacancies = main_hh('Python', start_page=1)

    with open('hh.json', 'w') as file:
        json.dump(vacancies, file, indent=2, ensure_ascii=False)
