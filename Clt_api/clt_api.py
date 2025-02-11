import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import csv
from typing import List, Dict


class IntelparkParser:
    def __init__(self, verbose: bool = True):
        self.session = requests.Session()
        self.base_url = "https://client.intelpark.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        self.verbose = verbose
        self.request_delay = 1

    def log(self, message: str, status: str = 'info') -> None:
        """Форматированное логирование"""
        timestamp = time.strftime("%H:%M:%S")
        icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        print(f"[{timestamp}] {icons.get(status, 'ℹ️')} {message}")

    def login(self, username: str, password: str) -> bool:
        """Авторизация на сайте"""
        try:
            self.log("Получаю страницу авторизации...")
            login_url = urljoin(self.base_url, "/login?r=%2F")
            response = self.session.get(login_url, headers=self.headers)
            response.raise_for_status()

            self.log("Отправляю данные для входа...")
            data = {
                'login': username,
                'password': password
            }

            time.sleep(self.request_delay)
            response = self.session.post(
                login_url,
                data=data,
                headers=self.headers,
                allow_redirects=False
            )

            if response.status_code == 302 and response.headers.get('Location') == '/':
                self.log("Авторизация успешна!", 'success')
                return True

            self.log(f"Ошибка авторизации. Код: {response.status_code}", 'error')
            return False

        except Exception as e:
            self.log(f"Ошибка при авторизации: {str(e)}", 'error')
            return False

    def get_all_users(self, oid: int = 736) -> List[Dict]:
        """Получение всех пользователей с пагинацией"""
        all_users = []
        page = 1

        while True:
            try:
                users, has_next = self.get_users_page(oid, page)
                all_users.extend(users)
                self.log(f"Страница {page}: получено {len(users)} пользователей")

                if not has_next:
                    break

                page += 1
                time.sleep(self.request_delay)

            except Exception as e:
                self.log(f"Ошибка при обработке страницы {page}: {str(e)}", 'error')
                break

        self.log(f"Всего получено пользователей: {len(all_users)}", 'success')
        return all_users

    def get_users_page(self, oid: int, page: int) -> (List[Dict], bool):
        """Получение одной страницы с пользователями"""
        params = {
            'oid': oid,
            'page': page,
            'limit': 100,
            'sort': 'default'
        }

        url = urljoin(self.base_url, "/persons")
        response = self.session.get(url, params=params, headers=self.headers)
        response.raise_for_status()

        return self.parse_users(response.text)

    def parse_users(self, html: str) -> (List[Dict], bool):
        """Парсинг страницы с пользователями"""
        soup = BeautifulSoup(html, 'html.parser')
        users = []

        table = soup.find('table', {'class': 'personsList'})
        if not table:
            self.log("Таблица пользователей не найдена", 'warning')
            return [], False

        rows = table.tbody.find_all('tr') if table.tbody else []
        for row in rows:
            try:
                user = self.parse_user_row(row)
                if user:
                    users.append(user)
            except Exception as e:
                self.log(f"Ошибка обработки строки: {str(e)}", 'warning')

        has_next = self.check_pagination(soup)
        return users, has_next

    def parse_user_row(self, row) -> Dict:
        """Парсинг одной строки с пользователем"""
        cells = row.find_all('td')
        if len(cells) < 6:
            return None

        return {
            'id': self.safe_extract_id(cells[0]),
            'name': self.safe_get_text(cells[0]),
            'address': self.safe_get_text(cells[1]),
            'phones': self.safe_get_phones(cells[2]),
            'apartment': self.safe_get_text(cells[3]),
            'access': self.parse_access(cells[4]),
            'edit_link': self.safe_extract_link(cells[5], 1),
            'delete_link': self.safe_extract_delete_link(cells[5])
        }

    def check_pagination(self, soup) -> bool:
        """Проверка наличия следующей страницы (исправлено предупреждение)"""
        pagination = soup.find('ul', {'class': 'pagination'})
        if not pagination:
            return False

        # Используем string вместо text для BeautifulSoup 4.4.0+
        next_btn = pagination.find('a', string='»')
        return next_btn is not None and 'disabled' not in next_btn.parent.get('class', [])

    # Вспомогательные методы
    def safe_get_text(self, cell) -> str:
        return cell.get_text(strip=True) if cell else ''

    def safe_extract_id(self, cell) -> str:
        try:
            link = cell.find('a')
            return link['href'].split('id=')[1] if link else None
        except:
            return None

    def safe_get_phones(self, cell) -> str:
        phones = [a.get_text(strip=True) for a in cell.find_all('a')] if cell else []
        return ', '.join(phones)

    def parse_access(self, cell) -> str:
        icons = cell.find_all('div', recursive=False) if cell else []
        access_types = [
            'Телефон' if self.check_icon(icons, 0) else '',
            'Приложение' if self.check_icon(icons, 1) else '',
            'Алиса' if self.check_icon(icons, 2) else '',
            'Пропуск' if self.check_icon(icons, 3) else '',
            'Ключ' if self.check_icon(icons, 4) else '',
            'Авто' if self.check_icon(icons, 5) else ''
        ]
        return ', '.join(filter(None, access_types))

    def check_icon(self, icons: List, index: int) -> bool:
        try:
            return 'green' in icons[index].get('style', '')
        except IndexError:
            return False

    def safe_extract_link(self, cell, index: int) -> str:
        links = cell.find_all('a') if cell else []
        return links[index]['href'] if len(links) > index else ''

    def safe_extract_delete_link(self, cell) -> str:
        link = cell.find('a', {'class': 'trash'})
        return link['href'] if link else ''

    def export_to_csv(self, users: List[Dict], filename: str = 'users.csv') -> None:
        """Экспорт данных в CSV файл"""
        if not users:
            self.log("Нет данных для экспорта", 'warning')
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ID', 'ФИО', 'Адрес', 'Квартира', 'Телефоны', 'Доступ', 'Ссылка редактирования',
                              'Ссылка удаления']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for user in users:
                    writer.writerow({
                        'ID': user.get('id', ''),
                        'ФИО': user.get('name', ''),
                        'Адрес': user.get('address', ''),
                        'Квартира': user.get('apartment', ''),
                        'Телефоны': user.get('phones', ''),
                        'Доступ': user.get('access', ''),
                        'Ссылка редактирования': user.get('edit_link', ''),
                        'Ссылка удаления': user.get('delete_link', '')
                    })
                self.log(f"Данные успешно экспортированы в {filename}", 'success')

        except Exception as e:
            self.log(f"Ошибка при экспорте в CSV: {str(e)}", 'error')


if __name__ == "__main__":
    parser = IntelparkParser(verbose=True)

    if parser.login(
            username="",
            password=""
    ):
        users = parser.get_all_users()
        parser.export_to_csv(users)

        # Пример вывода первых 3 записей
        print("\nПервые 3 пользователя:")
        for user in users[:3]:
            print(f"\nID: {user['id']}")
            print(f"ФИО: {user['name']}")
            print(f"Телефоны: {user['phones']}")
            print(f"Доступ: {user['access']}")
    else:
        print("Не удалось авторизоваться")