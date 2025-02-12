import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import csv
from typing import List, Dict


class IntelparkManager:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://client.intelpark.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        self.current_oid = 736  # Текущий объект по умолчанию

    def print_menu(self):
        """Вывод основного меню"""
        print("\n" + "=" * 30)
        print("Меню управления Интеллект-Парк")
        print("1. Парсинг пользователей")
        print("2. Добавить нового пользователя")
        print("3. Изменить данные пользователя")
        print("4. Экспорт в CSV")
        print("5. Выход")
        print("=" * 30)

    def run(self):
        """Основной цикл программы"""
        if not self.login():
            return

        while True:
            self.print_menu()
            choice = input("Выберите действие: ")

            if choice == '1':
                self.parse_users_menu()
            elif choice == '2':
                self.add_user_menu()
            elif choice == '3':
                self.modify_user_menu()
            elif choice == '4':
                self.export_menu()
            elif choice == '5':
                print("Выход из программы...")
                break
            else:
                print("Неверный выбор, попробуйте снова")

    def login(self):
        """Авторизация на сайте"""
        print("\n" + "=" * 30)
        print("Авторизация в системе")
        username = input("Введите email: ")
        password = input("Введите пароль: ")

        try:
            login_url = urljoin(self.base_url, "/login?r=%2F")
            response = self.session.get(login_url, headers=self.headers)
            response.raise_for_status()

            data = {
                'login': username,
                'password': password
            }

            response = self.session.post(
                login_url,
                data=data,
                headers=self.headers,
                allow_redirects=False
            )

            if response.status_code == 302:
                print("✅ Авторизация успешна!")
                return True

            print("❌ Ошибка авторизации")
            return False

        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            return False

    def parse_users_menu(self):
        """Меню парсинга пользователей"""
        print("\n" + "=" * 30)
        print("Парсинг пользователей")
        print(f"Текущий объект (oid: {self.current_oid})")
        print("1. Запустить парсинг")
        print("2. Изменить объект")
        print("3. Вернуться в меню")

        choice = input("Выберите действие: ")

        if choice == '1':
            users = self.get_all_users()
            self.last_users = users
            print(f"\nНайдено пользователей: {len(users)}")
        elif choice == '2':
            self.current_oid = int(input("Введите новый oid: "))
            print("Объект изменен!")
        elif choice == '3':
            return
        else:
            print("Неверный выбор")

    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        all_users = []
        page = 1

        while True:
            try:
                users, has_next = self.get_users_page(page)
                all_users.extend(users)
                print(f"Страница {page}: получено {len(users)} пользователей")

                if not has_next:
                    break

                page += 1
                time.sleep(1)

            except Exception as e:
                print(f"❌ Ошибка: {str(e)}")
                break

        print(f"Всего получено пользователей: {len(all_users)}")
        return all_users

    def get_users_page(self, page: int) -> (List[Dict], bool):
        """Получение страницы с пользователями"""
        params = {
            'oid': self.current_oid,
            'page': page,
            'limit': 100,
            'sort': 'default'
        }

        response = self.session.get(
            urljoin(self.base_url, "/persons"),
            params=params,
            headers=self.headers
        )
        response.raise_for_status()

        return self.parse_users(response.text)

    def parse_users(self, html: str) -> (List[Dict], bool):
        """Парсинг HTML страницы"""
        soup = BeautifulSoup(html, 'html.parser')
        users = []

        table = soup.find('table', {'class': 'personsList'})
        if not table:
            return [], False

        for row in table.tbody.find_all('tr'):
            try:
                users.append(self.parse_user_row(row))
            except Exception as e:
                print(f"Ошибка обработки строки: {str(e)}")

        has_next = self.check_pagination(soup)
        return users, has_next

    def parse_user_row(self, row) -> Dict:
        """Парсинг строки пользователя"""
        cells = row.find_all('td')
        return {
            'id': self.get_user_id(cells[0]),
            'name': cells[0].get_text(strip=True),
            'address': cells[1].get_text(strip=True),
            'phones': ', '.join([a.get_text() for a in cells[2].find_all('a')]),
            'apartment': cells[3].get_text(strip=True),
            'edit_link': cells[5].find_all('a')[1]['href'] if len(cells[5].find_all('a')) > 1 else ''
        }

    def check_pagination(self, soup) -> bool:
        """Проверка пагинации"""
        next_link = soup.find('a', string='»')

        if not next_link:
            return False

        # Проверяем, не заблокирована ли кнопка
        if 'disabled' in next_link.parent.get('class', []):
            return False

        return True

    def add_user_menu(self):
        """Меню добавления пользователя"""
        print("\n" + "=" * 30)
        print("Добавление нового пользователя")
        user_data = {
            'name': input("ФИО: "),
            'phone': input("Телефон: "),
            'address': input("Адрес: "),
            'apartment': input("Квартира/помещение: "),
            'car_number': input("Гос. номер (если есть): ")
        }

        if self.add_user(user_data):
            print("✅ Пользователь успешно добавлен!")
        else:
            print("❌ Ошибка при добавлении пользователя")

    def add_user(self, user_data: Dict) -> bool:
        """Добавление нового пользователя"""
        try:
            edit_url = urljoin(self.base_url, f"/person/edit?oid={self.current_oid}")
            response = self.session.get(edit_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            csrf_token = soup.find('input', {'name': '_csrf'})['value']

            data = {
                '_csrf': csrf_token,
                'Person[nsp]': user_data['name'],
                'Person[address]': user_data['address'],
                'Person[apartment]': user_data['apartment'],
                'Person[phone]': user_data['phone'],
                'Person[car_number]': user_data['car_number'],
                'save-button': 'Сохранить'
            }

            response = self.session.post(edit_url, data=data)
            return response.status_code == 200

        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            return False

    def modify_user_menu(self):
        """Меню изменения пользователя"""
        print("\n" + "=" * 30)
        user_id = input("Введите ID пользователя для изменения: ")
        print("Введите новые данные (оставьте пустым для сохранения текущего значения):")

        new_data = {
            'name': input("Новое ФИО: "),
            'phone': input("Новый телефон: "),
            'address': input("Новый адрес: "),
            'apartment': input("Новая квартира: "),
            'car_number': input("Новый гос. номер: ")
        }

        if self.modify_user(user_id, new_data):
            print("✅ Данные пользователя обновлены!")
        else:
            print("❌ Ошибка при изменении данных")

    def modify_user(self, user_id: str, new_data: Dict) -> bool:
        """Изменение данных пользователя"""
        try:
            edit_url = urljoin(self.base_url, f"/person/edit?id={user_id}")
            response = self.session.get(edit_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            csrf_token = soup.find('input', {'name': '_csrf'})['value']
            form_data = self.prepare_form_data(soup, new_data)
            form_data['_csrf'] = csrf_token

            response = self.session.post(edit_url, data=form_data)
            return response.status_code == 200

        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            return False

    def prepare_form_data(self, soup, new_data: Dict) -> Dict:
        """Подготовка данных формы для изменения"""
        inputs = soup.find_all('input')
        selects = soup.find_all('select')

        form_data = {}

        # Собираем текущие значения
        for inp in inputs:
            if inp.get('name') and inp.get('name') != '_csrf':
                form_data[inp['name']] = inp.get('value', '')

        for select in selects:
            if select.get('name'):
                selected = select.find('option', selected=True)
                form_data[select['name']] = selected['value'] if selected else ''

        # Обновляем измененные поля
        if new_data['name']: form_data['Person[nsp]'] = new_data['name']
        if new_data['phone']: form_data['Person[phone]'] = new_data['phone']
        if new_data['address']: form_data['Person[address]'] = new_data['address']
        if new_data['apartment']: form_data['Person[apartment]'] = new_data['apartment']
        if new_data['car_number']: form_data['Person[car_number]'] = new_data['car_number']

        return form_data

    def export_menu(self):
        """Меню экспорта данных"""
        if not hasattr(self, 'last_users') or not self.last_users:
            print("❌ Нет данных для экспорта")
            return

        filename = input("Введите имя файла (по умолчанию users.csv): ") or "users.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ID', 'ФИО', 'Адрес', 'Квартира', 'Телефоны', 'Ссылка'])

                for user in self.last_users:
                    writer.writerow([
                        user['id'],
                        user['name'],
                        user['address'],
                        user['apartment'],
                        user['phones'],
                        urljoin(self.base_url, user['edit_link'])
                    ])
                print(f"✅ Данные экспортированы в {filename}")

        except Exception as e:
            print(f"❌ Ошибка экспорта: {str(e)}")

    def get_user_id(self, cell) -> str:
        """Извлечение ID пользователя"""
        try:
            return cell.find('a')['href'].split('id=')[1]
        except:
            return ''


if __name__ == "__main__":
    manager = IntelparkManager()
    manager.run()