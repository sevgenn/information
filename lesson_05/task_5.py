"""Вариант I
Написать программу, которая собирает входящие письма из своего или тестового почтового ящика и сложить данные о письмах
в базу данных (от кого, дата отправки, тема письма, текст письма полный)
Логин тестового ящика: study.ai_172@mail.ru
Пароль тестового ящика: NextPassword172#"""

import time
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pymongo
from pymongo.errors import DuplicateKeyError as dke


def init_driver(driver_path):
    """Запускает webdriver."""
    service = Service(driver_path)
    return webdriver.Chrome(service=service)


def init_collection(db_name, collection_name):
    """Создает коллекцию mongodb."""
    client = pymongo.MongoClient('localhost', 27017)
    db =  client[db_name]
    return db[collection_name]


def get_another_date(days_quantity: int):
    """Возвращает дату, измененную на указанное количество дней."""
    today = date.today()
    another_date = today + timedelta(days=days_quantity)
    return another_date


def process_mail_ru(browser, collection, username, password):
    """Обрабатывает сообщения, сравнивая url текущей страницы с url предыдущей."""
    browser.find_element(By.XPATH, '//div[@id="mailbox"]//button').click()

    iframe = browser.find_element(By.CSS_SELECTOR, 'iframe[src*="https"')
    browser.switch_to.frame(iframe)

    WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.NAME, 'username')))
    username_input = browser.find_element(By.CSS_SELECTOR, 'input[name="username"]')
    username_input.send_keys(username)
    browser.find_element(By.CSS_SELECTOR, 'div[class="save-auth-field-wrap"]').click()
    browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

    WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.NAME, 'password')))
    password_input = browser.find_element(By.CSS_SELECTOR, 'input[name="password"]')
    browser.implicitly_wait(5)
    password_input.send_keys(password)
    browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

    browser.switch_to.default_content()

    WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.application')))
    # url для сравнения с последующим:
    last_url = None
    while True:
        time.sleep(2)
        browser.implicitly_wait(2)
        action = ActionChains(browser)
        action.send_keys(Keys.ARROW_DOWN)
        action.perform()
        browser.implicitly_wait(2)
        action.send_keys(Keys.ENTER)
        action.perform()
        browser.implicitly_wait(2)

        # Title:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.thread-subject')))
        current_url = browser.current_url
        print(current_url)
        title = browser.find_element(By.CSS_SELECTOR, 'h2.thread-subject').text
        # Date:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.letter__date')))
        date_of_post = browser.find_element(By.CSS_SELECTOR, 'div.letter__date').text
        print(date_of_post)
        print(type(date_of_post))
        if "сегодня" in date_of_post.lower():
            received_at = str(get_another_date(0)) + ', ' + date_of_post.split(',')[-1]
        elif "вчера" in date_of_post.lower():
            received_at = str(get_another_date(-1)) + ', ' + date_of_post.split(',')[-1]
        else:
            received_at = date_of_post
        # Sender:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.letter-contact')))
        sender_block = browser.find_element(By.CSS_SELECTOR, 'span.letter-contact')
        sender = sender_block.get_attribute('title')
        # Body:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.letter-body')))
        body = browser.find_element(By.CSS_SELECTOR, 'div.letter-body').text

        document = {
            'title': title,
            'sender': sender,
            'received_at': received_at,
            'post_body': body
        }
        try:
            collection.insert_one(document)
        except dke:
            print('Duplicate key error collection')

        if current_url == last_url:
            break
        last_url = current_url
        browser.back()


def main(driver_path, target_url, login, password):
    """Основной запуск обработки."""
    # Инициализация коллекции БД:
    collection = init_collection('posts', 'mail_ru')

    # Инициализация драйвера:
    browser = init_driver(driver_path=driver_path)
    browser.maximize_window()
    browser.get(target_url)

    process_mail_ru(browser=browser, collection=collection, username=login, password=password)
    browser.implicitly_wait(2)
    browser.quit()


if __name__ == '__main__':
    driver = './drivers/chromedriver'
    url = 'https://mail.ru'
    login = 'study.ai_172'
    password = 'NextPassword172#'

    main(driver_path=driver, target_url=url, login=login, password=password)
