import asyncio
import random
from telethon import TelegramClient, types, functions, errors
import uuid
import json
from datetime import datetime
import logging
import os
import requests
from telethon.tl.custom import Conversation
import signal
import sys
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError

KEYS_FILE = 'bot_keys.json'


def verify_key(key, device_id):
    """
    Проверка и активация ключа
    """
    url = 'http://38.180.254.132:8000/keys'
    data = {'keys': key, 'device': device_id}

    response = requests.post(url, data=json.dumps(data))
    print(response.json())
    if response.json()['status'] != 'success':
        return False, 'Ключ неверный либо был активирован ранее'

    # Активация ключа
    '''if not key_data['activated']:
        key_data['activated'] = True
        key_data['device_id'] = device_id
        key_data['activation_time'] = datetime.now().isoformat()

        with open(KEYS_FILE, 'w') as f:
            json.dump(keys, f, indent=4)'''

    return True, "Ключ успешно активирован"


def check_subscription(key):
    """
    Проверка статуса подписки
    """
    if key == True:
        return True
    return False


def get_or_create_device_id():
    """
    Получение существующего или создание нового device_id
    """
    DEVICE_ID_FILE = 'device_id.json'

    # Проверяем существование файла
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, 'r') as f:
            data = json.load(f)
            return data.get('device_id')

    # Если файла нет - генерируем новый UUID
    device_id = str(uuid.uuid4())

    # Сохраняем device_id в файл
    with open(DEVICE_ID_FILE, 'w') as f:
        json.dump({'device_id': device_id}, f)

    return device_id


def get_int_input(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Пожалуйста, введите целое число.")


def save_api_params(accounts):
    """
    Сохраняет API параметры в файл
    """
    api_data = []
    for pair in accounts:
        pair_data = {
            'first_account': {
                'api_id': pair['first_account']['api_id'],
                'api_hash': pair['first_account']['api_hash'],
                'phone_number': pair['first_account']['phone_number'],
                'username': pair['first_account']['username']
            },
            'second_account': {
                'api_id': pair['second_account']['api_id'],
                'api_hash': pair['second_account']['api_hash'],
                'phone_number': pair['second_account']['phone_number'],
                'username': pair['second_account']['username']
            }
        }
        api_data.append(pair_data)

    try:
        with open('api_params.json', 'w') as f:
            json.dump(api_data, f, indent=4)
        print("✅ API параметры успешно сохранены")
    except Exception as e:
        print(f"❌ Ошибка при сохранении API параметров: {str(e)}")


def load_api_params():
    """
    Загружает сохраненные API параметры
    """
    try:
        if os.path.exists('api_params.json'):
            with open('api_params.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка при загрузке API параметров: {str(e)}")
    return None


def get_leverage_mode():
    """
    Позволяет пользователю выбрать режим работы с плечом
    """
    while True:
        print("\n📈 Выберите режим работы с плечом:")
        print("1. Агрессивный режим:")
        print("   - Всегда выбирает максимальное доступное плечо")
        print("   - Подходит для более рискованной торговли")
        print("   - Потенциально высокая прибыль/убыток")
        print("\n2. Консервативный режим:")
        print("   - Выбирает 3-е плечо от начала списка")
        print("   - Более безопасный вариант торговли")
        print("   - Меньший риск ликвидации")

        try:
            mode = int(input("Введите номер режима (1 или 2): "))
            if mode in [1, 2]:
                return mode
            print("❌ Пожалуйста, введите 1 или 2")
        except ValueError:
            print("❌ Пожалуйста, введите число")


def select_leverage(available_leverages, mode):
    """
    Выбирает плечо согласно выбранному режиму

    Args:
        available_leverages (list): Список доступных значений плеча
        mode (int): Режим работы (1 - агрессивный, 2 - консервативный)

    Returns:
        int: Выбранное значение плеча
    """
    if not available_leverages:
        return None

    if mode == 1:  # Агрессивный режим
        return max(available_leverages)
    else:  # Консервативный режим
        if len(available_leverages) >= 3:
            return available_leverages[2]  # Третье плечо от начала
        return available_leverages[0]  # Если меньше 3 плеч, берем первое


def input_account_details():
    """
    Интерактивный ввод данных аккаунтов с возможностью использования сохраненных данных
    """
    # Пытаемся загрузить сохраненные параметры
    saved_params = load_api_params()
    if saved_params:
        print("\n💾 Найдены сохраненные API параметры")
        print(f"Количество сохраненных пар: {len(saved_params)}")
        for i, pair in enumerate(saved_params):
            print(f"\nПара #{i + 1}:")
            print(f"Первый аккаунт: {pair['first_account']['phone_number']} ({pair['first_account']['username']})")
            print(f"Второй аккаунт: {pair['second_account']['phone_number']} ({pair['second_account']['username']})")

        use_saved = input("\nИспользовать сохраненные параметры? (y/n): ").lower() == 'y'
        if use_saved:
            # Запрашиваем только токены для каждой пары
            tokens = []
            for i in range(len(saved_params)):
                print(f"\n💎 Введите токены для пары #{i + 1} (нажмите Enter дважды для завершения):")
                pair_tokens = []
                while True:
                    token = input("Токен: ").strip()
                    if not token:
                        if pair_tokens:
                            break
                        print("❌ Нужен хотя бы один токен")
                        continue
                    pair_tokens.append(token)
                tokens.append(pair_tokens)
            return saved_params, tokens

    accounts = []
    tokens = []

    # Получаем количество пар аккаунтов
    while True:
        try:
            num_pairs = int(input("\n📱 Введите количество пар аккаунтов: "))
            if num_pairs > 0:
                break
            print("❌ Количество пар должно быть больше 0")
        except ValueError:
            print("❌ Пожалуйста, введите число")

    # Для каждой пары аккаунтов
    for pair_num in range(num_pairs):
        print(f"\n🔄 Настройка пары аккаунтов #{pair_num + 1}")

        # Список токенов для этой пары
        print("\n�� Введите токены для торговли (нажмите Enter дважды для завершения):")
        pair_tokens = []
        while True:
            token = input("Токен: ").strip()
            if not token:
                if pair_tokens:  # Если уже есть хотя бы один токен
                    break
                print("❌ Нужен хотя бы один токен")
                continue
            pair_tokens.append(token)
        tokens.append(pair_tokens)

        # Данные первого аккаунта
        print(f"\n👤 Первый аккаунт пары #{pair_num + 1}")
        first_account = {
            'api_id': input("API ID: ").strip(),
            'api_hash': input("API Hash: ").strip(),
            'phone_number': input("Номер телефона: ").strip(),
            'username': input("Username бота: ").strip()
        }

        # Данные второго аккаунта
        print(f"\n👤 Второй аккаунт пары #{pair_num + 1}")
        second_account = {
            'api_id': input("API ID: ").strip(),
            'api_hash': input("API Hash: ").strip(),
            'phone_number': input("Номер телефона: ").strip(),
            'username': "@pvptrade_bot"
        }

        # Проверка заполнения всех полей
        if all(first_account.values()) and all(second_account.values()):
            accounts.append({
                'first_account': first_account,
                'second_account': second_account
            })
        else:
            print("❌ Все поля должны быть заполнены!")
            return input_account_details()  # Рекурсивный вызов при ошибке

        # Показываем сводку введенных данных
        print(f"\n✅ Пара аккаунтов #{pair_num + 1} настроена:")
        print(f"Первый аккаунт: {first_account['phone_number']} ({first_account['username']})")
        print(f"Второй аккаунт: {second_account['phone_number']} ({second_account['username']})")
        print(f"Токены для торговли: {', '.join(pair_tokens)}")

    # Финальная сводка
    print("\n📋 Итоговая конфигурация:")
    print(f"Настроено пар аккаунтов: {len(accounts)}")
    for i, account_pair in enumerate(accounts):
        print(f"\nПара #{i + 1}:")
        print(f"Аккаунт 1: {account_pair['first_account']['phone_number']}")
        print(f"Аккаунт 2: {account_pair['second_account']['phone_number']}")
        print(f"Токены: {', '.join(tokens[i])}")

    # Подтверждение
    if input("\n✨ Все верно? (y/n): ").lower() != 'y':
        return input_account_details()

    # Сохраняем введенные параметры
    save = input("\nСохранить введенные API параметры для следующего использования? (y/n): ").lower() == 'y'
    if save:
        save_api_params(accounts)

    return accounts, tokens


# Функция логирования сделок
def log_trade(username, token, direction, size, leverage, status):
    trade_info = {
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'token': token,
        'direction': direction,
        'size': size,
        'leverage': leverage,
        'status': status
    }

    logging.info(f"Trade: {json.dumps(trade_info)}")
    print(f"Trade logged: {trade_info}")


class SignalHandler:
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, signum, frame):
        print("\n🛑 Экстренная остановка. Закрываем все позиции...")
        self.shutdown_requested = True


async def emergency_close_positions(client, username, tokens):
    """Автоматическое закрытие позиций с проверкой"""
    print(f"\n🔍 Обработка {username}")
    try:
        # Отправляем команду закрытия
        await client.send_message(username, "/close")
        await asyncio.sleep(3)

        # Проверяем ответ бота
        messages = await client.get_messages(username, limit=5)
        position_found = False
        no_position_phrases = [
            "you have no open perps positions",
            "нет открытых позиций",
            "no positions to close"
        ]

        for msg in messages:
            if msg.text and any(phrase in msg.text.lower() for phrase in no_position_phrases):
                print(f"[{username}] ✅ Нет позиций")
                return
            if msg.reply_markup:
                for row in msg.reply_markup.rows:
                    for btn in row.buttons:
                        if any(token.lower() in btn.text.lower() for token in tokens):
                            position_found = True
                            break

        if not position_found:
            print(f"[{username}] ✅ Нет открытых позиций")
            return

        # Процесс закрытия
        print(f"[{username}] 🟠 Закрываю позиции...")
        for msg in messages:
            if msg.reply_markup:
                for token in tokens:
                    for row in msg.reply_markup.rows:
                        for btn in row.buttons:
                            if token.lower() in btn.text.lower():
                                await msg.click(data=btn.data)
                                print(f"[{username}] ✅ Токен: {token}")
                                await asyncio.sleep(3)
                                
                                # 100% и подтверждение
                                msgs = await client.get_messages(username, limit=3)
                                for m in msgs:
                                    if m.reply_markup:
                                        for r in m.reply_markup.rows:
                                            for b in r.buttons:
                                                if "100" in b.text:
                                                    await m.click(data=b.data)
                                                    await asyncio.sleep(2)
                                                    confirm_msgs = await client.get_messages(username, limit=3)
                                                    for cm in confirm_msgs:
                                                        if cm.reply_markup:
                                                            for rc in cm.reply_markup.rows:
                                                                for bc in rc.buttons:
                                                                    if "confirm" in bc.text.lower():
                                                                        await cm.click(data=bc.data)
                                                                        print(f"[{username}] ✅ Успешно закрыто")
                                                                        return
        print(f"[{username}] ⚠️ Не удалось закрыть позиции")

    except Exception as e:
        print(f"[{username}] ❌ Ошибка: {str(e)}")


async def safe_disconnect(client, account_info, tokens):
    """Безопасное отключение с закрытием позиций"""
    try:
        await emergency_close_positions(client, account_info['username'], tokens)
    finally:
        await client.disconnect()


async def send_message(client, username, message):
    try:
        await client.send_message(username, message)
    except Exception as e:
        print(f"Ошибка отправки сообщения {username}: {str(e)}")


async def click_button_with_condition(client, account_name, entity, condition):
    """
    Улучшенная функция для нажатия кнопок
    """
    MAX_RETRIES = 3

    for attempt in range(MAX_RETRIES):
        try:
            # Получаем последние сообщения
            messages = await client.get_messages(entity=entity, limit=5)

            print(f"[{account_name}] 🔍 Поиск кнопок (попытка {attempt + 1}/{MAX_RETRIES})")

            for message in messages:
                if not message or not message.reply_markup:
                    continue

                print(f"\n[{account_name}] Сообщение: {message.text}")
                print(f"[{account_name}] Доступные кнопки:")

                # Выводим все доступные кнопки для отладки
                found_button = None
                for row in message.reply_markup.rows:
                    for button in row.buttons:
                        print(f" - '{button.text}'")
                        if condition(button.text):
                            found_button = button
                            break
                    if found_button:
                        break

                if found_button:
                    print(f"[{account_name}] 🎯 Найдена подходящая кнопка: {found_button.text}")
                    try:
                        # Нажимаем кнопку
                        await message.click(data=found_button.data)
                        print(f"[{account_name}] ✅ Кнопка успешно нажата")
                        await asyncio.sleep(2)  # Ждем реакции от бота
                        return True

                    except Exception as e:
                        print(f"[{account_name}] ❌ Ошибка при нажатии кнопки: {str(e)}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(2)
                        continue

            print(f"[{account_name}] ⚠️ Подходящая кнопка не найдена")
            if attempt < MAX_RETRIES - 1:
                print(f"[{account_name}] 😴 Ожидание перед следующей попыткой...")
                await asyncio.sleep(3)

        except Exception as e:
            print(f"[{account_name}] ❌ Общая ошибка: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(3)

    print(f"[{account_name}] ❌ Не удалось нажать кнопку после {MAX_RETRIES} попыток")
    return False


def find_max_leverage(buttons):
    """
    Находит кнопку с максимальным значением плеча
    """
    max_leverage = 0
    max_leverage_button = None

    for button in buttons:
        # Извлекаем число из текста кнопки (например, из "10x" получаем 10)
        text = button.text.lower().replace('х', 'x')  # Заменяем русскую х на английскую
        if 'x' in text:
            try:
                leverage = int(text.split('x')[0])
                if leverage > max_leverage:
                    max_leverage = leverage
                    max_leverage_button = button
            except ValueError:
                continue

    return max_leverage_button


def get_opposite_leverage(number: str, leverage: str) -> dict:
    with open('leverage.json', 'r') as file:
        data = json.load(file)
    return data


def save_opposite_leverage(number: str, leverage: str) -> None:
    with open('leverage.json', 'r') as file:
        data = json.load(file)

    data[number] = leverage

    with open('leverage.json', 'w') as filename:
        json.dump(data, filename)


async def account_task(client, username, number, tokens, hold_time, token_queue=None, size_queue=None, delay=0,
                       size_of_trading=15,
                       trade_type=None):
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        try:
            print(f"[{username}] 🚀 Начало торговли")

            # 1. Отправляем команду открытия позиции (/long или /short)
            current_command = trade_type if trade_type else random.choice(['/long', '/short'])
            await send_message(client, username, current_command)
            await asyncio.sleep(3)

            # 2. Отправляем название токена (без /coin)
            if token_queue:
                try:
                    first_token = await asyncio.wait_for(token_queue.get(), timeout=1)
                    available_tokens = [t for t in tokens if t != first_token]
                    token_for_value = available_tokens[0]
                    print(f"[{username}] 💎 Второй аккаунт выбрал токен: {token_for_value}")
                except asyncio.TimeoutError:
                    token_for_value = random.choice(tokens)
                    print(f"[{username}] 💎 Первый аккаунт выбрал токен: {token_for_value}")
                    await token_queue.put(token_for_value)
            else:
                token_for_value = random.choice(tokens)

            # Отправляем только название токена
            await send_message(client, username, token_for_value)
            await asyncio.sleep(3)

            # 3. Выбор плеча через кнопки
            leverage_success = False
            for leverage_attempt in range(3):
                messages = await client.get_messages(username, limit=5)
                for message in messages:
                    if message and message.reply_markup:
                        all_buttons = []
                        for row in message.reply_markup.rows:
                            all_buttons.extend(row.buttons)

                        max_leverage_button = find_max_leverage(all_buttons)
                        save_opposite_leverage(number, max_leverage_button)

                        if max_leverage_button:
                            await message.click(data=max_leverage_button.data)
                            leverage_success = True
                            break
                if leverage_success:
                    break
                await asyncio.sleep(3)

            if not leverage_success:
                print(f"[{username}] ❌ Не удалось выбрать плечо")
                attempts += 1
                continue

            await asyncio.sleep(3)

            # 4. Отправляем размер позиции (просто число, без /size)

            print(f"[{username}] 💰 Устанавливаем размер позиции: {size_of_trading}")
            await send_message(client, username, str(size_of_trading))
            await asyncio.sleep(5)

            # 5. Подтверждаем размер через кнопку (с дополнительными проверками)
            confirm_success = False
            for confirm_attempt in range(3):
                print(f"[{username}] 🔍 Попытка подтверждения размера {confirm_attempt + 1}/3")
                messages = await client.get_messages(username, limit=5)

                for message in messages:
                    if message and message.reply_markup:
                        for row in message.reply_markup.rows:
                            for button in row.buttons:
                                button_text = button.text.lower()
                                if "подтвердить" in button_text or "confirm" in button_text:
                                    try:
                                        await message.click(data=button.data)
                                        print(f"[{username}] ✅ Размер подтвержден")
                                        confirm_success = True
                                        await asyncio.sleep(3)  # Ждем после подтверждения
                                        break
                                    except Exception as e:
                                        print(f"[{username}] ❌ Ошибка при подтверждении: {str(e)}")
                            if confirm_success:
                                break
                    if confirm_success:
                        break

                if confirm_success:
                    break

                print(f"[{username}] ⏳ Ожидание перед следующей попыткой подтверждения...")
                await asyncio.sleep(3)

            if not confirm_success:
                print(f"[{username}] ❌ Не удалось подтвердить размер позиции")
                attempts += 1
                continue

            # Проверяем, что позиция действительно открылась
            await asyncio.sleep(5)
            print(f"[{username}] ✅ Позиция успешно открыта")

            # Ожидание перед закрытием позиции
            print(f"[{username}] ⏳ Удержание позиции {hold_time} секунд")
            await asyncio.sleep(hold_time)

            # Закрытие позиции
            print(f"[{username}] 🔄 Закрытие позиции")
            await send_message(client, username, f"/close {token_for_value} 100%")
            await asyncio.sleep(5)

            messages = await client.get_messages(username, limit=5)

            for message in messages:
                if message and message.reply_markup:
                    for row in message.reply_markup.rows:
                        for button in row.buttons:
                            print
                            button_text = button.text.lower()
                            if "подтвердить" in button_text or "confirm" in button_text:
                                try: 
                                    await message.click(data=button.data)
                                    print(f"[{username}] ✅ Закрытие подтверждено")
                                    confirm_success = True
                                    await asyncio.sleep(3)  # Ждем после подтверждения
                                    break
                                except Exception as e:
                                    print(f"[{username}] ❌ Ошибка при подтверждении: {str(e)}")
            
            await asyncio.sleep(5)
            print(f"[{username}] ✅ Позиция успешно закрыта")

            # Возвращаем токен для следующей итерации
            return token_for_value

        except Exception as err:
            print(f"[{username}] ❌ Ошибка: {str(err)}")
            attempts += 1
            await asyncio.sleep(5)

    print(f"[{username}] ❌ Превышено максимальное число попыток")
    return None


async def send_error_notification(client, user_username, pair_index, account1, account2, error_msg):  # MODIFIED
    """Отправляет уведомление о приостановке пары через аккаунт Telethon"""
    try:
        message = (
            f"🚨 Пара #{pair_index + 1} приостановлена!\n"
            f"Аккаунт 1: {account1['phone_number']} ({account1['username']})\n"
            f"Аккаунт 2: {account2['phone_number']} ({account2['username']})\n"
            f"Причина: {error_msg}\n"
            f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Отправляем сообщение через первый аккаунт в паре
        await client.send_message(user_username, message)  # MODIFIED
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {str(e)}")
        # Пробуем через второй аккаунт
        try:
            await client.send_message(user_username, "‼️ Critical error! Check logs!")
        except:
            pass


async def run_account_pair(not_us, pair_index, client1, client2, account_pair, tokens, trading_params):
    """
    Функция для управления парой аккаунтов с обработкой ошибок
    """
    token_queue = asyncio.Queue()
    size_queue = asyncio.Queue()
    pair_active = True
    last_error = None

    while pair_active:
        try:
            print(f"\n🔄 Запуск новой итерации для пары {pair_index + 1}")

            # Генерируем новые trade_types для каждой итерации
            pair_trade_types = random.sample([('/long', '/short'), ('/short', '/long')], 1)[0]
            print(f"[Пара {pair_index + 1}] 📊 Направления сделок: {pair_trade_types[0]} и {pair_trade_types[1]}")

            delay_between_accounts = random.randint(
                trading_params['min_delay'],
                trading_params['max_delay']
            )

            # Очищаем очереди
            while not token_queue.empty():
                await token_queue.get()
            while not size_queue.empty():
                await size_queue.get()

            min_hold_time = trading_params['min_hold_time']
            max_hold_time = trading_params['max_hold_time']
            hold_time = random.randint(min_hold_time, max_hold_time)

            sizes = random.randint(trading_params['min_size'], trading_params['max_size'])

            async def run_second_account():
                try:
                    print(
                        f"⏳ Пара {pair_index + 1}: Ожидание {delay_between_accounts} секунд перед хеджирующей сделкой")
                    await asyncio.sleep(delay_between_accounts)

                    result = await account_task(
                        client2,
                        account_pair['second_account']['username'],
                        account_pair['second_account']['phone_number'],
                        tokens,
                        hold_time,
                        token_queue=token_queue,
                        size_queue=size_queue,
                        size_of_trading=sizes,
                        trade_type=pair_trade_types[1]
                    )
                    if result is None:
                        raise Exception("Не удалось выполнить операцию на втором аккаунте")
                    return result
                except Exception as e:
                    # Отправляем уведомление об ошибке
                    await send_error_notification(client2, str(e), account_pair['second_account'])
                    raise

            try:
                # Запускаем оба аккаунта и ждем результаты
                results = await asyncio.gather(
                    account_task(
                        client1,
                        account_pair['first_account']['username'],
                        account_pair['first_account']['phone_number'],
                        tokens,
                        hold_time,
                        token_queue=token_queue,
                        size_queue=size_queue,
                        size_of_trading=sizes,
                        trade_type=pair_trade_types[0]
                    ),
                    run_second_account(),
                    return_exceptions=True
                )

                # Проверяем результаты
                if any(isinstance(r, Exception) for r in results):
                    # Если произошла ошибка в любом из аккаунтов
                    print(f"[Пара {pair_index + 1}] ❌ Критическая ошибка в работе пары")

                    # Отправляем уведомление об ошибке для первого аккаунта
                    if isinstance(results[0], Exception):
                        await send_error_notification(
                            client1,
                            str(results[0]),
                            account_pair['first_account']
                        )

                    # Деактивируем пару
                    pair_active = False

                    error_message = (
                        f"🚫 Пара #{pair_index + 1} деактивирована из-за ошибок:\n"
                        f"Аккаунт 1: {account_pair['first_account']['phone_number']}\n"
                        f"Аккаунт 2: {account_pair['second_account']['phone_number']}"
                    )
                    print(error_message)

                    # Отправляем итоговое уведомление о деактивации пары
                    try:
                        NOTIFICATION_RECIPIENT = not_us
                        await client1.send_message(NOTIFICATION_RECIPIENT, error_message)
                    except:
                        pass

                    break

                print(f"[Пара {pair_index + 1}] ✅ Оба аккаунта успешно завершили операции")

                # Задержка между итерациями
                delay_between_iterations = random.randint(
                    trading_params['min_iteration_delay'],
                    trading_params['max_iteration_delay']
                )
                print(f"⏳ Пара {pair_index + 1}: Ожидание {delay_between_iterations} секунд перед следующей итерацией")
                await asyncio.sleep(delay_between_iterations)

            except Exception as e:
                print(f"[Пара {pair_index + 1}] ❌ Критическая ошибка: {str(e)}")
                pair_active = False
                await send_error_notification(client1, not_us, account_pair['first_account'], account_pair['second_account'], str(e))

        except Exception as e:
            print(f"[Пара {pair_index + 1}] ❌ Критическая ошибка в цикле работы пары: {str(e)}")
            pair_active = False
            try:
                await send_error_notification(client1, not_us, account_pair['first_account'], account_pair['second_account'], str(e))
            except:
                pass


async def main():
    handler  = SignalHandler()
        
    # Запрос ключа активации
    activation_key = input("Введите ваш активационный ключ: ")

    # Получение уникального ID устройства
    device_id = get_or_create_device_id()

    # Проверка ключа
    success, message = verify_key(activation_key, device_id)
    if not success:
        print(f"Активация не удалась: {message}")
        return

    # Проверка подписки
    subscription = check_subscription(success)
    if not subscription:
        print("Ошибка проверки подписки")
        return

    print(f"Бот активирован. Тип подписки: базовый")

    user_username = input("Введите ваш Telegram username для уведомлений (@username): ").strip() 

    # Ввод параметров торговли
    trading_params = input_trading_parameters()

    # Ввод данных аккаунтов
    accounts, tokens_list = input_account_details()

    clients = []
    all_tasks = []

    # Список возможных моделей устройств, версий системы и версий приложения
    system_versions = ['Android 10', 'Android 11', 'iOS 14', 'iOS 15']
    device_models = ['Samsung Galaxy S21', 'iPhone 12', 'Google Pixel 5', 'OnePlus 9']
    app_versions = ['7.0', '7.1', '7.2', '7.3']

    # Создаем все клиенты и задачи
    for i, account_pair in enumerate(accounts):
        # Первый аккаунт пары
        client1 = TelegramClient(
            f'session_name_{i * 2 + 1}',
            account_pair['first_account']['api_id'],
            account_pair['first_account']['api_hash'],
            system_version=random.choice(system_versions),
            device_model=random.choice(device_models),
            app_version=random.choice(app_versions)
        )
        await client1.start(account_pair['first_account']['phone_number'])
        clients.append(client1)

        # Второй аккаунт пары
        client2 = TelegramClient(
            f'session_name_{i * 2 + 2}',
            account_pair['second_account']['api_id'],
            account_pair['second_account']['api_hash'],
            system_version=random.choice(system_versions),
            device_model=random.choice(device_models),
            app_version=random.choice(app_versions)
        )
        await client2.start(account_pair['second_account']['phone_number'])
        clients.append(client2)

        # Создаем задачу для пары и добавляем в список
        task = run_account_pair(
            user_username,
            pair_index=i,
            client1=client1,
            client2=client2,
            account_pair=account_pair,
            tokens=tokens_list[i],
            trading_params=trading_params,
        )
        all_tasks.append(task)

    try:
        main_trade_task = asyncio.gather(*all_tasks)
        
        # Основной цикл ожидания
        while not handler.shutdown_requested:
            await asyncio.sleep(0.5)
            
        # Отмена всех задач при завершении
        print("\n🛑 Отмена всех торговых задач...")
        main_trade_task.cancel()
        try:
            await main_trade_task
        except asyncio.CancelledError:
            print("✅ Все торговые задачи отменены")
        except Exception as e:
            print(f"⚠️ Ошибка при отмене задач: {e}")
    except KeyboardInterrupt:
        print("\n⚠️ Получен сигнал остановки. Закрываем соединения...")
    finally:
        if handler.shutdown_requested:
            print("\n🔧 Завершение работы...")
            disconnect_tasks = []  # Явно инициализируем список

            # Для всех пар аккаунтов
            for i in range(len(accounts)):
                first_client = clients[i*2]
                second_client = clients[i*2+1]
                tokens = tokens_list[i]
                
                disconnect_tasks.append(
                    safe_disconnect(first_client, accounts[i]['first_account'], tokens)
                )
                disconnect_tasks.append(
                    safe_disconnect(second_client, accounts[i]['second_account'], tokens)
                )

            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            print("✅ Все соединения закрыты")
            sys.exit(0)
        for client in clients:
            await client.disconnect()
        
    while not handler.shutdown_requested:
        await asyncio.sleep(1)


def input_trading_parameters():
    """
    Интерактивный ввод параметров торговли
    """
    print("\n📊 Настройка параметров торговли")

    params = {}

    try:
        # Размер торговли
        print("\n💰 Настройка размера торговли:")
        params['min_size'] = int(input("Минимальный размер торговли: "))
        params['max_size'] = int(input("Максимальный размер торговли: "))

        # Время удержания
        print("\n⏱ Настройка времени удержания (в секундах):")
        params['min_hold_time'] = int(input("Минимальное время: "))
        params['max_hold_time'] = int(input("Максимальное время: "))

        # Задержки между аккаунтами в паре
        print("\n⏳ Настройка задержек между аккаунтами в паре (в секундах):")
        params['min_delay'] = int(input("Минимальная задержка: "))
        params['max_delay'] = int(input("Максимальная задержка: "))

        # Задержки между итерациями
        print("\n⌛️ Настройка задержек между итерациями (в секундах):")
        params['min_iteration_delay'] = int(input("Минимальная задержка: "))
        params['max_iteration_delay'] = int(input("Максимальная задержка: "))

        # Проверка корректности введенных данных
        if any(v < 0 for v in params.values()):
            print("❌ Значения не могут быть отрицательными!")
            return input_trading_parameters()

        if params['min_size'] > params['max_size'] or \
                params['min_hold_time'] > params['max_hold_time'] or \
                params['min_delay'] > params['max_delay'] or \
                params['min_iteration_delay'] > params['max_iteration_delay']:
            print("❌ Минимальные значения не могут быть больше максимальных!")
            return input_trading_parameters()

        # Показываем сводку
        print("\n📋 Проверьте настройки:")
        print(f"Размер торговли: {params['min_size']} - {params['max_size']}")
        print(f"Время удержания: {params['min_hold_time']} - {params['max_hold_time']} сек")
        print(f"Задержка между аккаунтами: {params['min_delay']} - {params['max_delay']} сек")
        print(f"Задержка между итерациями: {params['min_iteration_delay']} - {params['max_iteration_delay']} сек")

        if input("\n✨ Все верно? (y/n): ").lower() != 'y':
            return input_trading_parameters()

        return params

    except ValueError:
        print("❌ Пожалуйста, введите числовые значения!")
        return input_trading_parameters()


if __name__ == '__main__':
    asyncio.run(main())
