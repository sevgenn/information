# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymongo
import re


class JobparserPipeline:
    def __init__(self):
        client = pymongo.MongoClient('localhost', 27017)
        self.db = client.vacancies

    def process_item(self, item, spider):
        """Обрабатывает объект и сохраняет в базу."""
        if spider.name == 'hhru':
            item['min_salary'], item['max_salary'] = self.process_salary_hh(item['salary'])
            item['currency'] = self.process_currency_hh(item['salary'])
            del item['salary']
        if spider.name == 'sjru':
            item['min_salary'], item['max_salary'] = self.process_salary_sj(item['salary'])
            item['currency'] = self.process_currency_sj(item['salary'])
            del item['salary']
        collection = self.db[spider.name]
        collection.insert_one(item)
        return item

    def process_salary_hh(self, salary: list) -> tuple:
        """Преобразует з/п в кортеж чисел."""
        min_salary = None
        max_salary = None
        if len(salary) > 5:
            min_salary = int(salary[1].replace('\xa0', ''))
            max_salary = int(salary[3].replace('\xa0', ''))
        elif 1 < len(salary) <= 5:
            if salary[0] == 'от ':
                min_salary = int(salary[1].replace('\xa0', ''))
            elif salary[0] == 'до ':
                max_salary = int(salary[1].replace('\xa0', ''))

        return min_salary, max_salary

    def process_currency_hh(self, salary: list) -> [str, None]:
        """Извлекает наименование валюты."""
        regex = r'[\D+\\.?]$'
        salary_currency = None
        if len(salary) > 1 and re.search(regex, salary[-2]):
            salary_currency = salary[-2]
        return salary_currency

    def process_salary_sj(self, salary):
        """Преобразует з/п в кортеж чисел."""
        min_salary = None
        max_salary = None
        if len(salary) >= 4:
            min_salary = int(salary[0].replace('\xa0', ''))
            max_salary = int(salary[1].replace('\xa0', ''))
        elif salary[0].startswith('от'):
            raw_data = re.sub(r'[^\d]', '', salary[2])
            min_salary = int(raw_data)
        elif salary[0].startswith('до'):
            raw_data = re.sub(r'[^\d]', '', salary[2])
            max_salary = int(raw_data)
        return min_salary, max_salary

    def process_currency_sj(self, salary):
        """Извлекает наименование валюты."""
        regex = r'[\D+\\.]?$'
        salary_currency = None
        if len(salary) > 1 and re.search(regex, salary[-1]):
            salary_currency = salary[-1]
        return salary_currency
