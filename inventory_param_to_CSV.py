import requests
import csv
import json
import getpass  # Для безопасного ввода пароля

# Настройки подключения к Zabbix API
ZABBIX_URL = 'https://zbx.ors-aero.ru/api_jsonrpc.php'
ZABBIX_USER = 'zbx_api'
ZABBIX_PASSWORD = None  # Пароль будет запрошен при запуске

# Название поля инвентаря (можно легко изменить)
INVENTORY_FIELD = 'software_app_a'  # Здесь можно указать любое другое поле инвентаря

# Функция для выполнения запросов к Zabbix API
def zabbix_api_request(method, params, auth_token=None):
    headers = {'Content-Type': 'application/json-rpc'}
    
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
        "auth": auth_token  # Передаем токен аутентификации, если он есть
    }

    if method == 'user.login':  # Для user.login не нужен токен
        del payload['auth']

    response = requests.post(ZABBIX_URL, data=json.dumps(payload), headers=headers)
    result = response.json()

    if 'result' in result:
        return result['result']
    else:
        print(f"Error: {result['error']}")
        return None

# Получение списка хостов из группы "Linux servers" с их инвентарем
def get_linux_servers_with_inventory(auth_token):
    group_id = zabbix_api_request('hostgroup.get', {
        'filter': {'name': ['Linux servers']},  # Исправлено название группы
        'output': ['groupid']
    }, auth_token)

    if not group_id:
        print("Группа 'Linux servers' не найдена.")  # Исправлено название группы
        return []

    hosts = zabbix_api_request('host.get', {
        'groupids': group_id[0]['groupid'],
        'output': ['hostid', 'name'],
        'selectInventory': [INVENTORY_FIELD]  # Используем переменную INVENTORY_FIELD
    }, auth_token)

    return hosts

# Извлечение значений указанного поля инвентаря
def extract_inventory_field(hosts, field_name):
    inventory_values = []
    for host in hosts:
        inventory = host.get('inventory', [])
        
        # Если inventory является списком, берем первый элемент
        if isinstance(inventory, list) and inventory:
            inventory = inventory[0]
        elif not isinstance(inventory, dict):
            inventory = {}

        value = inventory.get(field_name, '')  # Извлекаем значение по имени поля
        if value:
            inventory_values.append({
                'hostname': host['name'],
                field_name: value  # Сохраняем имя поля и его значение
            })
    return inventory_values

# Сохранение данных в CSV файл
def save_to_csv(data, filename='inventory_data.csv'):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['hostname', INVENTORY_FIELD])
        writer.writeheader()
        writer.writerows(data)
    print(f"Данные сохранены в файл: {filename}")

# Основная функция
if __name__ == '__main__':
    # Запрос пароля у пользователя
    if not ZABBIX_PASSWORD:
        ZABBIX_PASSWORD = getpass.getpass(prompt=f"Введите пароль для пользователя '{ZABBIX_USER}': ")

    # Аутентификация и получение токена
    auth_token = zabbix_api_request('user.login', {'username': ZABBIX_USER, 'password': ZABBIX_PASSWORD})
    if not auth_token:
        print("Не удалось аутентифицироваться в Zabbix.")
        exit(1)

    # Получение списка хостов с инвентарем
    hosts = get_linux_servers_with_inventory(auth_token)
    if not hosts:
        print(f"Нет хостов в группе 'Linux servers' с полем инвентаря '{INVENTORY_FIELD}'.")
        exit(1)

    # Извлечение значений указанного поля инвентаря
    inventory_values = extract_inventory_field(hosts, INVENTORY_FIELD)

    # Сохранение результатов в CSV
    save_to_csv(inventory_values)