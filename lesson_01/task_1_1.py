import requests
import json


def scrap(url: str) -> None:
    response = requests.get(url)
    if response.status_code == 200:
        with open('github.json', 'w') as file:
            json.dump(json.loads(response.text), file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    user_name = 'sevgenn'
    # Список репозиториев:
    url = f'https://api.github.com/users/{user_name}/repos'

    scrap(url)

"""Во втором задании получены данные с vk о станциях московского метро (vk.json)."""
