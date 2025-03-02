import socket
import requests

# Список доменов
domains = [
    "digiway.kg",
    "itgelectronics.ae",
    "terrabyteglb.bh",
    "electropolistrading.om",
    "vimanna.cn",
    "megacomputers.ae",
    "apiline.ae",
    "compuline.hk",
    "alpenglowm.com",
    "saldorc.com",
    "tidewill.com",
    "quantumttrdng.ae",
    "mykenes.com",
    "quanticoelectronics.ae",
    "dorlum.com",
    "ml-forwarding.com",
    "przlog.com",
    "sll-logistics.com",
    "techoasisfzco.ae",
    "lamatrade.id",
    "salviaoriental.bh",
    "xantinatrading.qa"
]

# Функция для получения IP-адреса по доменному имени
def get_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None

# Функция для получения страны по IP-адресу через API ipinfo.io
def get_country_by_ip(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        data = response.json()
        return data.get("country", "Unknown")
    except requests.RequestException:
        return "Unknown"

# Основной код
for domain in domains:
    ip = get_ip(domain)
    if ip:
        country = get_country_by_ip(ip)
        print(f"Домен: {domain}, IP: {ip}, Страна: {country}")
    else:
        print(f"Домен: {domain}, IP: Не удалось разрешить")