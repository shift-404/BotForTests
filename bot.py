"""
Телеграм-бот для ферми "Смак природи" - ОПТИМИЗИРОВАННАЯ ВЕРСІЯ
Асинхронна робота з високою швидкістю відповіді
"""

import os
import json
import asyncio
import aiohttp
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
from threading import Thread
from flask import Flask

# ==================== БАЗА ДАНИХ ====================

def init_database():
    """Ініціалізація бази даних"""
    conn = sqlite3.connect('farm_bot.db')
    cursor = conn.cursor()
    
    # Таблиця користувачів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблиця кошиків
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблиця замовлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            username TEXT,
            phone TEXT,
            city TEXT,
            np_department TEXT,
            total REAL,
            status TEXT DEFAULT 'нове',
            order_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблиця елементів замовлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_name TEXT,
            quantity REAL,
            price_per_unit REAL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id)
        )
    ''')
    
    # Таблиця повідомлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            username TEXT,
            text TEXT,
            message_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблиця сесій користувачів
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT '',
            temp_data TEXT DEFAULT '{}',
            last_section TEXT DEFAULT 'main_menu',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

TOKEN = os.getenv("BOT_TOKEN")

# ==================== ДАНІ ПРОДУКТІВ ====================

PRODUCTS = [
    {
        "id": 1,
        "name": "Артишоки преміум",
        "category": "овочі",
        "description": "Свіжі артишоки вищого ґатунку, зібрані вручну",
        "price": 350,
        "unit": "кг",
        "image": "🥬"
    },
    {
        "id": 2,
        "name": "Спаржа зелена",
        "category": "овочі",
        "description": "Нарізана спаржа, готова до приготування, без пестицидів",
        "price": 280,
        "unit": "кг",
        "image": "🌱"
    },
    {
        "id": 3,
        "name": "Яблука Голден",
        "category": "фрукти",
        "description": "Солодкі яблука сорту Голден, ідеальні для пирогів",
        "price": 60,
        "unit": "кг",
        "image": "🍎"
    },
    {
        "id": 4,
        "name": "Інжир свіжий",
        "category": "фрукти",
        "description": "Стиглий інжир прямо з саду, дуже соковитий",
        "price": 200,
        "unit": "кг",
        "image": "🍈"
    },
    {
        "id": 5,
        "name": "Грецькі горіхи",
        "category": "горіхи",
        "description": "Великі смачні горіхи, багаті на вітаміни",
        "price": 300,
        "unit": "кг",
        "image": "🌰"
    },
    {
        "id": 6,
        "name": "Мед акацієвий",
        "category": "мед",
        "description": "Натуральний мед з власної пасіки",
        "price": 450,
        "unit": "літр",
        "image": "🍯"
    }
]

FAQS = [
    {
        "question": "Які способи оплати ви приймаєте?",
        "answer": "✅ Готівка при отриманні\n✅ Переказ на карту ПриватБанку\n✅ Оплата через LiqPay"
    },
    {
        "question": "Які терміни доставки?",
        "answer": "🚚 Київ - 1-2 дні\n🚚 Україна - 2-4 дні\n🚛 Великі партії - 3-5 днів"
    },
    {
        "question": "Чи є гарантія якості?",
        "answer": "⭐ Всі продукти екологічно чисті\n⭐ Без штучних добавок\n⭐ Щоденний контроль якості"
    },
    {
        "question": "Як зберігати продукти?",
        "answer": "❄️ Овочі/фрукти - у холодильнику\n🌰 Горіхи - у сухому місці\n🍯 Мед - кімнатна температура"
    },
    {
        "question": "Чи є знижки?",
        "answer": "🎁 Постійним клієнтам - 5%\n🎁 Замовлення від 1000 грн - 3%\n🎁 При самовивозі - 2%"
    }
]

COMPANY_INFO = {
    "name": "🌱 Ферма 'Смак природи'",
    "description": "Ми сімейна ферма, що спеціалізується на вирощуванні екологічно чистих овочів, фруктів та горіхів.",
    "details": [
        "👨‍🌾 Працюємо з 2015 року",
        "📍 Розташування: Київська область, с. Зелене",
        "📞 Телефон: +380 (67) 123-45-67",
        "📧 Email: info@smak-pryrody.ua",
        "🕒 Графік: Пн-Пт 9:00-18:00, Сб 10:00-15:00",
        "🚚 Доставка: по всій Україні"
    ]
}

# ==================== ОПТИМИЗОВАНІ УТІЛІТИ ДЛЯ РОБОТИ З TELEGRAM API ====================

class TelegramAPI:
    """Асинхронний клас для роботи з Telegram API"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = None
        self._session_lock = asyncio.Lock()
        
    async def get_session(self):
        """Получает или создает aiohttp сессию"""
        if self.session is None or self.session.closed:
            async with self._session_lock:
                if self.session is None or self.session.closed:
                    timeout = aiohttp.ClientTimeout(total=30)
                    connector = aiohttp.TCPConnector(limit=100)
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector
                    )
        return self.session
    
    async def _make_request(self, method: str, data: dict = None, params: dict = None) -> dict:
        """Виконує асинхронний HTTP запит"""
        try:
            session = await self.get_session()
            url = f"{self.base_url}/{method}"
            
            async with session.post(url, json=data, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"❌ Помилка API {method}: {response.status} - {text[:100]}")
                    return {"ok": False}
                    
        except Exception as e:
            print(f"❌ Помилка запиту {method}: {e}")
            return {"ok": False}
    
    async def get_updates(self, offset: int = 0, timeout: int = 1) -> list:
        """Отримує оновлення асинхронно (короткий timeout для швидкої реакції)"""
        params = {"offset": offset, "timeout": timeout, "limit": 100}
        result = await self._make_request("getUpdates", params=params)
        return result.get("result", [])
    
    async def send_message(self, chat_id: int, text: str, 
                          reply_markup: dict = None,
                          parse_mode: str = "HTML") -> bool:
        """Надсилає повідомлення користувачеві асинхронно"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        result = await self._make_request("sendMessage", data=data)
        return result.get("ok", False)
    
    async def edit_message(self, chat_id: int, message_id: int, text: str,
                          reply_markup: dict = None) -> bool:
        """Редагує існуюче повідомлення асинхронно"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        result = await self._make_request("editMessageText", data=data)
        return result.get("ok", False)
    
    async def answer_callback(self, callback_id: str, text: str = None) -> bool:
        """Відповідає на callback запит асинхронно"""
        data = {"callback_query_id": callback_id}
        if text:
            data["text"] = text
        
        result = await self._make_request("answerCallbackQuery", data=data)
        return result.get("ok", False)
    
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Видаляє повідомлення асинхронно"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        result = await self._make_request("deleteMessage", data=data)
        return result.get("ok", False)
    
    async def close(self):
        """Закриває сесію"""
        if self.session and not self.session.closed:
            await self.session.close()

# ==================== УТІЛІТИ ДЛЯ РОБОТИ З БАЗОЮ ДАНИХ (оптимізовані) ====================

class Database:
    """Клас для роботи з базою даних"""
    
    @staticmethod
    def get_connection():
        """Повертає з'єднання з базою даних"""
        return sqlite3.connect('farm_bot.db', check_same_thread=False)
    
    @staticmethod
    def save_user(user_id: int, first_name: str = "", last_name: str = "", username: str = ""):
        """Зберігає або оновлює користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, first_name, last_name, username)
            VALUES (?, ?, ?, ?)
        ''', (user_id, first_name, last_name, username))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_user_session(user_id: int) -> Dict:
        """Отримує сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT state, temp_data, last_section 
            FROM user_sessions 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            state, temp_data_json, last_section = row
            temp_data = json.loads(temp_data_json) if temp_data_json else {}
            return {
                "state": state,
                "temp_data": temp_data,
                "last_section": last_section
            }
        return {"state": "", "temp_data": {}, "last_section": "main_menu"}
    
    @staticmethod
    def save_user_session(user_id: int, state: str = "", temp_data: Dict = None, last_section: str = ""):
        """Зберігає сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        temp_data_json = json.dumps(temp_data) if temp_data else "{}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions (user_id, state, temp_data, last_section, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, state, temp_data_json, last_section))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def clear_user_session(user_id: int):
        """Очищає сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM user_sessions WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_to_cart(user_id: int, product_id: int, quantity: float) -> bool:
        """Додає товар до кошика або оновлює кількість"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, quantity FROM carts 
            WHERE user_id = ? AND product_id = ?
        ''', (user_id, product_id))
        
        existing = cursor.fetchone()
        
        if existing:
            cart_id, old_quantity = existing
            new_quantity = old_quantity + quantity
            cursor.execute('''
                UPDATE carts SET quantity = ?, added_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_quantity, cart_id))
        else:
            cursor.execute('''
                INSERT INTO carts (user_id, product_id, quantity)
                VALUES (?, ?, ?)
            ''', (user_id, product_id, quantity))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_cart_items(user_id: int) -> List[Dict]:
        """Отримує товари з кошика користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        # Простий способ без сложных JOIN
        cursor.execute('''
            SELECT id, product_id, quantity FROM carts 
            WHERE user_id = ?
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            cart_id, product_id, quantity = row
            product = next((p for p in PRODUCTS if p["id"] == product_id), None)
            if product:
                items.append({
                    "cart_id": cart_id,
                    "product": {
                        "id": product_id,
                        "name": product["name"],
                        "price": product["price"],
                        "unit": product["unit"],
                        "image": product["image"]
                    },
                    "quantity": quantity
                })
        
        return items
    
    @staticmethod
    def clear_cart(user_id: int):
        """Очищає кошик користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def remove_from_cart(cart_id: int):
        """Видаляє товар з кошика"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM carts WHERE id = ?', (cart_id,))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def create_order(user_id: int, order_data: Dict) -> int:
        """Створює нове замовлення"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO orders (user_id, user_name, username, phone, city, np_department, total, order_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            order_data.get("name", ""),
            order_data.get("username", ""),
            order_data.get("phone", ""),
            order_data.get("city", ""),
            order_data.get("np_department", ""),
            order_data.get("total", 0),
            order_data.get("order_type", "")
        ))
        
        order_id = cursor.lastrowid
        
        # Додаємо товари до замовлення
        cart_items = Database.get_cart_items(user_id)
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_name, quantity, price_per_unit)
                VALUES (?, ?, ?, ?)
            ''', (
                order_id,
                item["product"]["name"],
                item["quantity"],
                item["product"]["price"]
            ))
        
        Database.clear_cart(user_id)
        
        conn.commit()
        conn.close()
        return order_id
    
    @staticmethod
    def save_message(user_id: int, user_name: str, username: str, text: str, message_type: str):
        """Зберігає повідомлення від користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (user_id, user_name, username, text, message_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, user_name, username, text, message_type))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_user_orders(user_id: int, limit: int = 5) -> List[Dict]:
        """Отримує замовлення користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT order_id, user_name, phone, city, np_department, 
                   total, status, order_type, created_at
            FROM orders 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        orders = []
        for row in rows:
            (order_id, user_name, phone, city, np_department, 
             total, status, order_type, created_at) = row
            
            # Отримуємо товари для замовлення
            conn2 = Database.get_connection()
            cursor2 = conn2.cursor()
            cursor2.execute('''
                SELECT product_name, quantity 
                FROM order_items 
                WHERE order_id = ?
            ''', (order_id,))
            products_rows = cursor2.fetchall()
            conn2.close()
            
            products = ", ".join([f"{name} ({qty}кг)" for name, qty in products_rows])
            
            orders.append({
                "order_id": order_id,
                "user_name": user_name,
                "phone": phone,
                "city": city,
                "np_department": np_department,
                "total": total,
                "status": status,
                "order_type": order_type,
                "created_at": created_at,
                "products": products
            })
        
        return orders
    
    @staticmethod
    def get_statistics() -> Dict:
        """Повертає статистику"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM carts')
        active_carts = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_orders": total_orders,
            "total_messages": total_messages,
            "total_users": total_users,
            "active_carts": active_carts
        }

# ==================== ГЕНЕРАТОРИ КЛАВІАТУР ====================

def create_inline_keyboard(buttons: List[List[Dict]]) -> Dict:
    """Створює inline клавіатуру для Telegram"""
    keyboard = []
    
    for row in buttons:
        keyboard_row = []
        for button in row:
            keyboard_row.append({
                "text": button.get("text", ""),
                "callback_data": button.get("callback_data", "")
            })
        keyboard.append(keyboard_row)
    
    return {"inline_keyboard": keyboard}

def get_main_menu() -> Dict:
    """Повертає головне меню"""
    buttons = [
        [{"text": "🏢 Про компанію", "callback_data": "company"}],
        [{"text": "📦 Наші продукти", "callback_data": "products"}],
        [{"text": "❓ Часті запитання", "callback_data": "faq"}],
        [{"text": "🚀 Написати нам", "callback_data": "quick_message"}],  # ИЗМЕНЕНО!
        [{"text": "🛒 Моя корзина", "callback_data": "cart"}, 
         {"text": "📋 Мої замовлення", "callback_data": "my_orders"}],
        [{"text": "📞 Зв'язатися з нами", "callback_data": "contact"}]
    ]
    return create_inline_keyboard(buttons)

def get_back_keyboard(back_to: str) -> Dict:
    """Повертає кнопку 'Назад' на попередню сторінку"""
    return create_inline_keyboard([[{"text": "🔙 Назад", "callback_data": f"back_{back_to}"}]])

def get_products_menu() -> Dict:
    """Повертає меню продуктів"""
    buttons = []
    
    for i in range(0, len(PRODUCTS), 2):
        row = []
        for j in range(2):
            if i + j < len(PRODUCTS):
                product = PRODUCTS[i + j]
                row.append({
                    "text": f"{product['image']} {product['name']}",
                    "callback_data": f"product_{product['id']}"
                })
        if row:
            buttons.append(row)
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_product_detail_menu(product_id: int) -> Dict:
    """Повертає меню для детальної сторінки продукту"""
    buttons = [
        [{"text": "🛒 Додати в кошик", "callback_data": f"add_to_cart_{product_id}"}],
        [{"text": "🔙 Назад", "callback_data": "back_products"}],
    ]
    return create_inline_keyboard(buttons)

def get_faq_menu() -> Dict:
    """Повертає меню FAQ"""
    buttons = []
    
    for i, faq in enumerate(FAQS, 1):
        buttons.append([{
            "text": f"❔ {faq['question'][:40]}...",
            "callback_data": f"faq_{i}"
        }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_contact_menu() -> Dict:
    """Повертає меню контактів"""
    buttons = [
        [{"text": "📞 Зателефонувати", "callback_data": "call_us"}],
        [{"text": "📧 Написати email", "callback_data": "email_us"}],
        [{"text": "📍 Наша адреса", "callback_data": "our_address"}],
        [{"text": "💬 Написати нам тут", "callback_data": "write_here"}],
        [{"text": "🔙 Назад", "callback_data": "back_main_menu"}]
    ]
    return create_inline_keyboard(buttons)

def get_quick_message_menu() -> Dict:  # НОВЫЙ МЕНЮ!
    """Повертає меню для швидкого повідомлення"""
    return create_inline_keyboard([
        [{"text": "✍️ Написати повідомлення", "callback_data": "write_quick_message"}],
        [{"text": "🔙 Назад", "callback_data": "back_main_menu"}]
    ])

def get_cart_menu(cart_items: List) -> Dict:
    """Повертає меню кошика"""
    buttons = []
    
    if cart_items:
        buttons.append([{"text": "✅ Оформити замовлення", "callback_data": "checkout_cart"}])
        buttons.append([{"text": "🗑️ Очистити корзину", "callback_data": "clear_cart"}])
        for item in cart_items:
            product_name = item["product"]["name"][:20] + "..." if len(item["product"]["name"]) > 20 else item["product"]["name"]
            buttons.append([{
                "text": f"❌ {product_name} ({item['quantity']}кг)",
                "callback_data": f"remove_from_cart_{item['cart_id']}"
            }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_order_confirmation_keyboard() -> Dict:
    """Повертає клавіатуру для підтвердження замовлення"""
    return create_inline_keyboard([
        [{"text": "✅ Так, продовжити", "callback_data": "confirm_order_yes"}],
        [{"text": "❌ Ні, скасувати", "callback_data": "confirm_order_no"}]
    ])

# ==================== УТІЛІТИ ДЛЯ ВАЛІДАЦІЇ ====================

def parse_quantity(text: str) -> Tuple[bool, float, str]:
    """Парсить кількість з тексту"""
    text = text.strip().replace(" ", "")
    match = re.search(r'(\d+(?:[.,]\d+)?)', text)
    
    if not match:
        return False, 0, "❌ Будь ласка, введіть число (наприклад: 1, 1.5, 2.3)"
    
    try:
        num_str = match.group(1).replace(",", ".")
        quantity = float(num_str)
        
        if quantity <= 0:
            return False, 0, "❌ Кількість повинна бути більше 0"
        if quantity > 100:
            return False, 0, "❌ Занадто велика кількість. Максимум 100 кг"
        
        return True, quantity, ""
    except ValueError:
        return False, 0, "❌ Некоректний формат числа"

# ==================== ГЕНЕРАТОРИ ТЕКСТУ ====================

def get_welcome_text() -> str:
    """Повертає текст привітання"""
    return """
<b>🇺🇦 Вітаємо у боті ферми "Смак природи"! 🌱</b>

Ми спеціалізуємося на вирощуванні <b>екологічно чистих</b> продуктів:
    
🥬 <b>Артишоки</b> - для здорового харчування
🌱 <b>Спаржа</b> - багата на вітаміни
🍎 <b>Яблука</b> - соковиті та солодкі
🍈 <b>Інжир</b> - натуральна солодкість
🌰 <b>Горіхи</b> - джерело енергії
🍯 <b>Мед</b> - натуральний та корисний

<b>Оберіть опцію з меню 👇</b>
    """

def get_company_text() -> str:
    """Повертає текст про компанію"""
    text = f"""
<b>{COMPANY_INFO['name']}</b>

{COMPANY_INFO['description']}

<b>📋 Деталі:</b>
"""
    for detail in COMPANY_INFO['details']:
        text += f"• {detail}\n"
    
    text += "\n<b>🌿 Наша філософія:</b>\n"
    text += "• Повага до природи\n"
    text += "• Чесність перед клієнтами\n"
    text += "• Якість у кожній деталі\n"
    text += "• Сімейні традиції\n"
    
    return text

def get_product_text(product_id: int) -> str:
    """Повертає текст продукту"""
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return "❌ Продукт не знайдено"
    
    unit_text = "кг" if product['unit'] == "кг" else "літр"
    
    return f"""
<b>{product['image']} {product['name']}</b>

📝 <i>{product['description']}</i>

💰 <b>Ціна:</b> {product['price']} грн/{unit_text}
🏷️ <b>Категорія:</b> {product['category']}
📦 <b>Наявність:</b> Є в наявності

<b>🌟 Переваги:</b>
• Екологічно чистий
• Свіжий продукт
• Без пестицидів
• Висока якість

<b>🍽️ Як використовувати:</b>
Ідеально підходить для салатів, гарнірів та самостійних страв.
    """

def get_faq_text(faq_id: int) -> str:
    """Повертає текст FAQ"""
    if 0 <= faq_id - 1 < len(FAQS):
        faq = FAQS[faq_id - 1]
        return f"""
<b>❔ {faq['question']}</b>

{faq['answer']}

<i>📞 Маєте інші запитання? Зв'яжіться з нами!</i>
        """
    return "❌ Питання не знайдено"

def get_contact_text() -> str:
    """Повертає текст контактів"""
    return """
<b>📞 Зв'язок з нами</b>

Ми завжди раді допомогти вам!

<b>Оберіть спосіб зв'язку:</b>
• <b>Телефон</b> - для швидких запитань
• <b>Email</b> - для детальних консультацій
• <b>Адреса</b> - для самовивозу
• <b>Написати тут</b> - швидке повідомлення в чаті

<i>Просто напишіть нам повідомлення в цьому чаті 👇</i>
    """

def get_quick_message_text() -> str:  # НОВЫЙ ТЕКСТ!
    """Повертає текст для швидкого повідомлення"""
    return """
<b>💬 Написати нам повідомлення</b>

Напишіть ваше повідомлення прямо в цьому чаті:

• Питання про продукти
• Консультація щодо замовлення
• Пропозиції співпраці
• Інші питання

<b>Ми відповімо вам якнайшвидше! ⚡</b>

<i>Просто напишіть ваше повідомлення нижче 👇</i>
    """

def get_cart_text(cart_items: List[Dict]) -> str:
    """Повертає текст кошика"""
    if not cart_items:
        return "🛒 <b>Ваша корзина порожня</b>\n\nДодайте товари з каталогу!"
    
    text = "🛒 <b>Ваша корзина</b>\n\n"
    
    total = 0
    for i, item in enumerate(cart_items, 1):
        quantity = item["quantity"]
        product = item["product"]
        item_total = product["price"] * quantity
        
        text += f"<b>{i}. {product['name']}</b>\n"
        text += f"   📊 Кількість: <b>{quantity} кг</b>\n"
        text += f"   💰 Ціна: {product['price']} грн/кг × {quantity}кг = <b>{item_total:.2f} грн</b>\n\n"
        
        total += item_total
    
    text += f"<b>📊 Всього товарів:</b> {len(cart_items)}\n"
    text += f"<b>💰 Загальна сума:</b> <b>{total:.2f} грн</b>\n\n"
    text += "<i>Для оформлення замовлення натисніть кнопку нижче</i>"
    
    return text

# ==================== ОСНОВНИЙ КЛАС БОТА (АСИНХРОННИЙ) ====================

class FarmBot:
    """Асинхронний основний клас бота ферми"""
    
    def __init__(self):
        self.api = TelegramAPI(TOKEN)
        self.running = True
        self.offset = 0
    
    async def start(self):
        """Асинхронний запуск бота"""
        print("=" * 50)
        print("🌱 БОТ ФЕРМИ 'СМАК ПРИРОДИ' ЗАПУЩЕНО (асинхронна версія)")
        print("=" * 50)
        
        init_database()
        
        stats = Database.get_statistics()
        print("📊 Статистика:")
        print(f"• Користувачів: {stats['total_users']}")
        print(f"• Замовлень: {stats['total_orders']}")
        print(f"• Повідомлень: {stats['total_messages']}")
        print(f"• Активних кошиків: {stats['active_carts']}")
        print(f"• Продуктів у базі: {len(PRODUCTS)}")
        print("=" * 50)
        print("🔄 Очікування повідомлень...\n")
        
        while self.running:
            try:
                updates = await self.api.get_updates(self.offset)
                
                for update in updates:
                    self.offset = update["update_id"] + 1
                    
                    # Обробка в окремій задачі для швидкості
                    asyncio.create_task(self.process_update(update))
                
                await asyncio.sleep(0.01)  # Дуже коротка затримка
                
            except KeyboardInterrupt:
                print("\n🛑 Бот зупиняється...")
                self.running = False
            except Exception as e:
                print(f"⚠️ Помилка в основному циклі: {e}")
                await asyncio.sleep(1)
    
    async def process_update(self, update: Dict):
        """Обробляє оновлення в окремій задачі"""
        try:
            if "message" in update:
                await self.handle_message(update["message"])
            elif "callback_query" in update:
                await self.handle_callback(update["callback_query"])
        except Exception as e:
            print(f"⚠️ Помилка обробки оновлення: {e}")
    
    async def handle_message(self, message: Dict):
        """Асинхронна обробка текстових повідомлень"""
        try:
            chat_id = message["chat"]["id"]
            user = message.get("from", {})
            user_id = user.get("id")
            text = message.get("text", "").strip()
            
            print(f"👤 [{datetime.now().strftime('%H:%M:%S')}] {user.get('first_name', 'Користувач')}: {text}")
            print(f"🔍 DEBUG: chat_id={chat_id}, user_id={user_id}, text='{text}'")
            
            # Зберігаємо користувача
            Database.save_user(
                user_id,
                user.get("first_name", ""),
                user.get("last_name", ""),
                user.get("username", "")
            )
            
            # ВАЖНО: /start и /cancel всегда сбрасывают состояние!
            if text == "/start" or text == "/cancel" or text.lower() == "скасувати":
                Database.clear_user_session(user_id)
                welcome = get_welcome_text()
                await self.api.send_message(chat_id, welcome, get_main_menu())
                Database.save_user_session(user_id, last_section="main_menu")
                return  # Выходим из метода!
            
            # Отримуємо стан користувача
            session = Database.get_user_session(user_id)
            state = session["state"]
            temp_data = session["temp_data"]
            
            # Обробка інших команд
            if text.startswith("/"):
                if text == "/help":
                    await self.api.send_message(chat_id, "ℹ️ Допомога: оберіть опцію з меню", get_main_menu())
                else:
                    await self.api.send_message(chat_id, "🤔 Невідома команда. Використовуйте /start для початку", get_main_menu())
            
            # Обробка станів
            elif state == "waiting_quantity":
                await self._handle_quantity_input(chat_id, user_id, user, text, temp_data)
            
            elif state == "waiting_message" or state == "waiting_quick_message":
                await self._handle_message_input(chat_id, user_id, user, text, state)
            
            elif state.startswith("full_order_"):
                await self._handle_full_order_input(chat_id, user_id, user, text, state, temp_data)
            
            else:
                # Звичайне повідомлення
                await self._handle_regular_message(chat_id, user_id, user, text)
                
        except Exception as e:
            print(f"❌ ОШИБКА В handle_message: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_quantity_input(self, chat_id: int, user_id: int, user: Dict, text: str, temp_data: Dict):
        """Обробляє введення кількості"""
        product_id = temp_data.get("product_id")
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        
        if not product:
            await self.api.send_message(chat_id, "❌ Помилка: продукт не знайдено", get_main_menu())
            Database.clear_user_session(user_id)
            return
        
        # Парсимо кількість
        success, quantity, error_msg = parse_quantity(text)
        
        if not success:
            response = f"❌ <b>Невірний формат!</b>\n\n{error_msg}\n\n"
            response += f"<b>Продукт:</b> {product['name']}\n"
            response += f"<b>Ціна:</b> {product['price']} грн/кг\n\n"
            response += "📊 <b>Введіть кількість в кг (тільки число):</b>\n"
            response += "<i>Наприклад: 1.5 або 2</i>"
            
            await self.api.send_message(chat_id, response)
            return
        
        # Додаємо до кошика
        Database.add_to_cart(user_id, product_id, quantity)
        
        # Очищаємо сесію
        Database.clear_user_session(user_id)
        
        # Показуємо підтвердження
        total_price = product["price"] * quantity
        response = f"✅ <b>{product['name']}</b> додано до кошика!\n\n"
        response += f"📊 Кількість: <b>{quantity} кг</b>\n"
        response += f"💰 Ціна: {product['price']} грн/кг\n"
        response += f"💵 Сума: <b>{total_price:.2f} грн</b>\n\n"
        
        cart_items = Database.get_cart_items(user_id)
        response += f"🛒 У кошику: <b>{len(cart_items)} товар(ів)</b>\n\n"
        response += "<i>Продовжуйте додавати товари або перейдіть до оформлення замовлення.</i>"
        
        await self.api.send_message(chat_id, response)
        
        # Показуємо продукти
        products_text = "📦 <b>Наші продукти</b>\n\nОберіть продукт для детальної інформації:"
        await self.api.send_message(chat_id, products_text, get_products_menu())
        Database.save_user_session(user_id, last_section="products")
    
    async def _handle_message_input(self, chat_id: int, user_id: int, user: Dict, text: str, state: str):
        """Обробляє введення повідомлення"""
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
        username = user.get('username', 'немає')
        
        # Определяем тип сообщения
        message_type = "повідомлення з кнопки 'Написати нам тут'" if state == "waiting_message" else "швидке повідомлення"
        
        # Зберігаємо повідомлення
        Database.save_message(user_id, user_name, username, text, message_type)
        
        # Логуємо в консоль
        print(f"\n{'='*80}")
        print(f"💬 НОВЕ ПОВІДОМЛЕННЯ ({message_type}):")
        print(f"👤 Ім'я: {user_name}")
        print(f"📱 Username: @{username}" if username != 'немає' else f"📱 Username: немає")
        print(f"🆔 ID: {user_id}")
        print(f"💬 Текст: {text}")
        print(f"🕒 Час: {datetime.now().isoformat()}")
        print(f"{'='*80}\n")
        
        # Відповідаємо користувачеві
        response = "✅ <b>Повідомлення отримано!</b>\n\n"
        response += "Ми відповімо вам найближчим часом.\n"
        response += "<i>Дякуємо за звернення! 🌱</i>"
        
        await self.api.send_message(chat_id, response, get_main_menu())
        Database.clear_user_session(user_id)
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_full_order_input(self, chat_id: int, user_id: int, user: Dict, text: str, state: str, temp_data: Dict):
        """Обробляє введення для повного замовлення"""
        if state == "full_order_name":
            temp_data["name"] = text
            temp_data["username"] = user.get("username", "немає")
            Database.save_user_session(user_id, "full_order_phone", temp_data)
            
            response = "📱 <b>Введіть ваш номер телефону:</b>\n\n"
            response += "<i>Приклад: +380501234567 або 0501234567</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_phone":
            # Валідація телефону
            import re
            phone = text.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            
            # Упрощенная валидация
            if not re.match(r'^(\+38|38)?0\d{9}$', phone):
                response = f"❌ <b>Невірний номер телефону!</b>\n\n"
                response += "📱 <b>Введіть ваш номер телефону ще раз:</b>\n"
                response += "<i>Приклад: +380501234567 або 0501234567</i>"
                
                await self.api.send_message(chat_id, response)
                return
            
            # Приводим к стандартному формату
            if phone.startswith("0"):
                phone = "+38" + phone
            elif phone.startswith("38"):
                phone = "+" + phone
            elif phone.startswith("+380"):
                pass
            else:
                phone = "+380" + phone[1:] if phone.startswith("+") else "+380" + phone
            
            temp_data["phone"] = phone
            Database.save_user_session(user_id, "full_order_city", temp_data)
            
            response = "🏙️ <b>Введіть місто доставки:</b>\n\n"
            response += "<i>Наприклад: Київ, Львів, Одеса</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_city":
            temp_data["city"] = text
            Database.save_user_session(user_id, "full_order_np", temp_data)
            
            response = "🏣 <b>Введіть номер відділення Нової Пошти або адресу:</b>\n\n"
            response += "<i>Наприклад: Відділення №25 або вул. Садова, 10, кв. 5</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_np":
            temp_data["np_department"] = text
            
            # Розраховуємо загальну суму
            cart_items = Database.get_cart_items(user_id)
            total = sum(item["product"]["price"] * item["quantity"] for item in cart_items)
            temp_data["total"] = total
            temp_data["order_type"] = "повне замовлення"
            
            # Зберігаємо дані
            Database.save_user_session(user_id, "full_order_confirm", temp_data)
            
            # Показуємо підтвердження
            response = "✅ <b>Дані отримано! Перевірте інформацію:</b>\n\n"
            response += f"👤 <b>ПІБ:</b> {temp_data.get('name', '')}\n"
            response += f"📱 <b>Телефон:</b> {temp_data.get('phone', '')}\n"
            response += f"🏙️ <b>Місто:</b> {temp_data.get('city', '')}\n"
            response += f"🏣 <b>Адреса/Відділення:</b> {text}\n"
            response += f"🛒 <b>Товарів у кошику:</b> {len(cart_items)}\n"
            response += f"💰 <b>Загальна сума:</b> {total:.2f} грн\n\n"
            response += "<b>Підтвердити замовлення?</b>"
            
            await self.api.send_message(chat_id, response, get_order_confirmation_keyboard())
    
    async def _handle_regular_message(self, chat_id: int, user_id: int, user: Dict, text: str):
        """Обробляє звичайне повідомлення"""
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
        username = user.get('username', 'немає')
        
        # Зберігаємо повідомлення
        Database.save_message(user_id, user_name, username, text, "повідомлення в чаті")
        
        # Логуємо
        print(f"\n{'='*80}")
        print(f"💬 НОВЕ ПОВІДОМЛЕННЯ В ЧАТІ:")
        print(f"👤 Ім'я: {user_name}")
        print(f"📱 Username: @{username}" if username != 'немає' else f"📱 Username: немає")
        print(f"🆔 ID: {user_id}")
        print(f"💬 Текст: {text}")
        print(f"🕒 Час: {datetime.now().isoformat()}")
        print(f"{'='*80}\n")
        
        # Відповідаємо
        response = "✅ <b>Повідомлення отримано!</b>\n\n"
        response += "Ми відповімо вам найближчим часом.\n"
        response += "<i>Дякуємо за звернення! 🌱</i>"
        
        await self.api.send_message(chat_id, response, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def handle_callback(self, callback: Dict):
        """Асинхронна обробка натискання кнопок"""
        callback_id = callback["id"]
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        data = callback["data"]
        user = callback["from"]
        user_id = user["id"]
        
        print(f"🖱️ [{datetime.now().strftime('%H:%M:%S')}] {user.get('first_name', 'Користувач')} натиснув: {data}")
        
        # Зберігаємо користувача
        Database.save_user(
            user_id,
            user.get("first_name", ""),
            user.get("last_name", ""),
            user.get("username", "")
        )
        
        # Відповідаємо на callback
        await self.api.answer_callback(callback_id)
        
        # Обробка кнопок "Назад"
        if data.startswith("back_"):
            await self._handle_back_button(chat_id, message_id, user_id, data)
        
        # Головне меню
        elif data == "company":
            await self._handle_company(chat_id, message_id, user_id)
        
        elif data == "products":
            await self._handle_products(chat_id, message_id, user_id)
        
        elif data.startswith("product_"):
            await self._handle_product_detail(chat_id, message_id, user_id, data)
        
        elif data.startswith("add_to_cart_"):
            await self._handle_add_to_cart(chat_id, message_id, user_id, data)
        
        elif data == "faq":
            await self._handle_faq(chat_id, message_id, user_id)
        
        elif data.startswith("faq_"):
            await self._handle_faq_detail(chat_id, message_id, user_id, data)
        
        elif data == "quick_message":  # ИЗМЕНЕНО!
            await self._handle_quick_message(chat_id, message_id, user_id)
        
        elif data == "write_quick_message":  # НОВЫЙ ОБРАБОТЧИК!
            await self._handle_write_quick_message(chat_id, message_id, user_id)
        
        elif data == "cart":
            await self._handle_cart(chat_id, message_id, user_id)
        
        elif data.startswith("remove_from_cart_"):
            await self._handle_remove_from_cart(chat_id, message_id, user_id, data)
        
        elif data == "checkout_cart":
            await self._handle_checkout_cart(chat_id, message_id, user_id)
        
        elif data == "clear_cart":
            await self._handle_clear_cart(chat_id, message_id, user_id)
        
        elif data == "my_orders":
            await self._handle_my_orders(chat_id, message_id, user_id)
        
        elif data == "contact":
            await self._handle_contact(chat_id, message_id, user_id)
        
        elif data == "write_here":
            await self._handle_write_here(chat_id, message_id, user_id)
        
        elif data in ["call_us", "email_us", "our_address"]:
            await self._handle_contact_info(chat_id, message_id, user_id, data)
        
        elif data.startswith("confirm_order_"):
            await self._handle_order_confirmation(chat_id, message_id, user_id, data)
        
        else:
            await self._handle_unknown_callback(chat_id, message_id, user_id, data)
    
    async def _handle_back_button(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє кнопку 'Назад'"""
        back_target = data[5:]
        
        if back_target == "main_menu":
            welcome = get_welcome_text()
            await self.api.edit_message(chat_id, message_id, welcome, get_main_menu())
            Database.save_user_session(user_id, last_section="main_menu")
        
        elif back_target == "products":
            products_text = "📦 <b>Наші продукти</b>\n\nОберіть продукт для детальної інформації:"
            await self.api.edit_message(chat_id, message_id, products_text, get_products_menu())
            Database.save_user_session(user_id, last_section="products")
        
        elif back_target == "faq":
            faq_text = "❓ <b>Часті запитання</b>\n\nОберіть питання для отримання відповіді:"
            await self.api.edit_message(chat_id, message_id, faq_text, get_faq_menu())
            Database.save_user_session(user_id, last_section="faq")
        
        elif back_target == "contact":
            contact_text = get_contact_text()
            await self.api.edit_message(chat_id, message_id, contact_text, get_contact_menu())
            Database.save_user_session(user_id, last_section="contact")
        
        elif back_target == "quick_message":
            quick_message_text = get_quick_message_text()
            await self.api.edit_message(chat_id, message_id, quick_message_text, get_quick_message_menu())
            Database.save_user_session(user_id, last_section="quick_message")
        
        elif back_target == "cart":
            await self._handle_cart(chat_id, message_id, user_id)
        
        else:
            welcome = get_welcome_text()
            await self.api.edit_message(chat_id, message_id, welcome, get_main_menu())
            Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_company(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Про компанію'"""
        company_text = get_company_text()
        await self.api.edit_message(chat_id, message_id, company_text, get_back_keyboard("main_menu"))
        Database.save_user_session(user_id, last_section="company")
    
    async def _handle_products(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Наші продукти'"""
        products_text = "📦 <b>Наші продукти</b>\n\nОберіть продукт для детальної інформації:"
        await self.api.edit_message(chat_id, message_id, products_text, get_products_menu())
        Database.save_user_session(user_id, last_section="products")
    
    async def _handle_product_detail(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє вибір продукту"""
        try:
            product_id = int(data.split("_")[1])
            product_text = get_product_text(product_id)
            await self.api.edit_message(chat_id, message_id, product_text, get_product_detail_menu(product_id))
            Database.save_user_session(user_id, last_section=f"product_{product_id}")
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка завантаження продукту", get_back_keyboard("products"))
    
    async def _handle_add_to_cart(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє додавання до кошика"""
        try:
            product_id = int(data.split("_")[3])
            product = next((p for p in PRODUCTS if p["id"] == product_id), None)
            
            if not product:
                await self.api.edit_message(chat_id, message_id, "❌ Продукт не знайдено", get_back_keyboard("products"))
                return
            
            # Зберігаємо сесію з ID товару
            temp_data = {"product_id": product_id}
            Database.save_user_session(user_id, "waiting_quantity", temp_data)
            
            # Видаляємо повідомлення з кнопками
            await self.api.delete_message(chat_id, message_id)
            
            # Запитуємо кількість
            response = f"📦 <b>Додавання {product['name']} до кошика</b>\n\n"
            response += f"💰 Ціна: {product['price']} грн/кг\n\n"
            response += "📊 <b>Введіть кількість в кг (тільки число):</b>\n\n"
            response += "<i>Наприклад: 1.5 або 2</i>"
            
            await self.api.send_message(chat_id, response)
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка додавання до кошика", get_back_keyboard("products"))
    
    async def _handle_faq(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Часті запитання'"""
        faq_text = "❓ <b>Часті запитання</b>\n\nОберіть питання для отримання відповіді:"
        await self.api.edit_message(chat_id, message_id, faq_text, get_faq_menu())
        Database.save_user_session(user_id, last_section="faq")
    
    async def _handle_faq_detail(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє вибір питання FAQ"""
        try:
            faq_id = int(data.split("_")[1])
            faq_text = get_faq_text(faq_id)
            await self.api.edit_message(chat_id, message_id, faq_text, get_back_keyboard("faq"))
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка завантаження питання", get_back_keyboard("faq"))
    
    async def _handle_quick_message(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Написати нам'"""
        quick_message_text = get_quick_message_text()
        await self.api.edit_message(chat_id, message_id, quick_message_text, get_quick_message_menu())
        Database.save_user_session(user_id, last_section="quick_message")
    
    async def _handle_write_quick_message(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Написати повідомлення' для швидкого замовлення"""
        Database.save_user_session(user_id, "waiting_quick_message")
        
        # Видаляємо повідомлення
        await self.api.delete_message(chat_id, message_id)
        
        response = "💬 <b>Написати нам повідомлення</b>\n\n"
        response += "Напишіть ваше повідомлення прямо в цьому чаті:\n\n"
        response += "• Питання про продукти\n"
        response += "• Консультація щодо замовлення\n"
        response += "• Пропозиції співпраці\n"
        response += "• Інші питання\n\n"
        response += "<b>Ми відповімо вам якнайшвидше! ⚡</b>\n\n"
        response += "<i>Просто напишіть ваше повідомлення нижче 👇</i>"
        
        await self.api.send_message(chat_id, response)
    
    async def _handle_cart(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Моя корзина'"""
        cart_items = Database.get_cart_items(user_id)
        cart_text = get_cart_text(cart_items)
        await self.api.edit_message(chat_id, message_id, cart_text, get_cart_menu(cart_items))
        Database.save_user_session(user_id, last_section="cart")
    
    async def _handle_remove_from_cart(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє видалення з кошика"""
        try:
            cart_id = int(data.split("_")[3])
            Database.remove_from_cart(cart_id)
            
            # Оновлюємо кошик
            cart_items = Database.get_cart_items(user_id)
            cart_text = get_cart_text(cart_items)
            await self.api.edit_message(chat_id, message_id, cart_text, get_cart_menu(cart_items))
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка видалення", get_back_keyboard("cart"))
    
    async def _handle_checkout_cart(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє оформлення замовлення з кошика"""
        cart_items = Database.get_cart_items(user_id)
        
        if not cart_items:
            response = "🛒 <b>Ваша корзина порожня</b>\n\n"
            response += "Додайте товари з каталогу перед оформленням замовлення!"
            await self.api.edit_message(chat_id, message_id, response, get_back_keyboard("main_menu"))
            return
        
        # Починаємо оформлення
        Database.save_user_session(user_id, "full_order_name", {})
        
        # Видаляємо повідомлення
        await self.api.delete_message(chat_id, message_id)
        
        # Запитуємо ПІБ
        response = "🛒 <b>Оформлення замовлення</b>\n\n"
        response += f"📦 У вашій корзині: <b>{len(cart_items)} товар(ів)</b>\n"
        
        total = sum(item["product"]["price"] * item["quantity"] for item in cart_items)
        response += f"💰 Загальна сума: <b>{total:.2f} грн</b>\n\n"
        response += "📝 <b>Введіть ваше ПІБ (повне ім'я):</b>\n\n"
        response += "<i>Наприклад: Іванов Іван Іванович</i>"
        
        await self.api.send_message(chat_id, response)
    
    async def _handle_clear_cart(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє очищення кошика"""
        Database.clear_cart(user_id)
        
        response = "🗑️ <b>Корзина очищена!</b>\n\n"
        response += "Ваша корзина тепер порожня.\n"
        response += "<i>Додайте товари з каталогу.</i>"
        
        await self.api.edit_message(chat_id, message_id, response, get_back_keyboard("main_menu"))
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_my_orders(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Мої замовлення'"""
        orders = Database.get_user_orders(user_id)
        
        if orders:
            orders_text = "📋 <b>Ваші замовлення</b>\n\n"
            for order in orders[:5]:
                orders_text += f"🆔 <b>#{order['order_id']}</b>\n"
                orders_text += f"   📦 Тип: {order['order_type']}\n"
                orders_text += f"   🛒 Товари: {order['products'] or 'не вказано'}\n"
                orders_text += f"   💰 Сума: {order['total']:.2f} грн\n"
                orders_text += f"   📊 Статус: {order['status']}\n"
                orders_text += f"   🕒 {order['created_at'][:10]}\n\n"
            
            if len(orders) > 5:
                orders_text += f"<i>Показано останні 5 з {len(orders)} замовлень</i>\n"
            
            orders_text += "\n📞 <b>Питання щодо замовлення?</b>\nНапишіть нам у чат!"
        else:
            orders_text = "📋 <b>Ваші замовлення</b>\n\n"
            orders_text += "У вас ще немає замовлень.\n"
            orders_text += "Оберіть продукти та зробіть своє перше замовлення! 🚀"
        
        await self.api.edit_message(chat_id, message_id, orders_text, get_back_keyboard("main_menu"))
        Database.save_user_session(user_id, last_section="my_orders")
    
    async def _handle_contact(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Зв'язатися з нами'"""
        contact_text = get_contact_text()
        await self.api.edit_message(chat_id, message_id, contact_text, get_contact_menu())
        Database.save_user_session(user_id, last_section="contact")
    
    async def _handle_write_here(self, chat_id: int, message_id: int, user_id: int):
        """Обробляє кнопку 'Написати нам тут'"""
        Database.save_user_session(user_id, "waiting_message")
        
        # Видаляємо повідомлення
        await self.api.delete_message(chat_id, message_id)
        
        response = "💬 <b>Написати нам тут</b>\n\n"
        response += "Напишіть ваше повідомлення прямо в цьому чаті:\n\n"
        response += "• Питання про продукти\n"
        response += "• Консультація\n"
        response += "• Пропозиції співпраці\n"
        response += "• Інші питання\n\n"
        response += "<i>Ми відповімо вам найближчим часом!</i>"
        
        await self.api.send_message(chat_id, response)
    
    async def _handle_contact_info(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє контактну інформацію"""
        if data == "call_us":
            contact_info = "📞 <b>Телефон для зв'язку:</b>\n\n"
            contact_info += "✅ <code>+380 (67) 123-45-67</code>\n"
            contact_info += "✅ <code>+380 (63) 987-65-43</code>\n\n"
            contact_info += "<i>Графік роботи: Пн-Пт 9:00-18:00</i>"
        
        elif data == "email_us":
            contact_info = "📧 <b>Email для листування:</b>\n\n"
            contact_info += "✅ <code>info@smak-pryrody.ua</code>\n"
            contact_info += "✅ <code>sales@smak-pryrody.ua</code>\n\n"
            contact_info += "<i>Відповідаємо протягом 24 годин</i>"
        
        else:  # our_address
            contact_info = "📍 <b>Наша адреса:</b>\n\n"
            contact_info += "🏠 Київська область\n"
            contact_info += "📌 село Зелене, вул. Садова, 42\n"
            contact_info += "🗺️ Координати: 50.4504° N, 30.5245° E\n\n"
            contact_info += "<i>Самовивіз: Пн-Сб 10:00-17:00</i>"
        
        await self.api.edit_message(chat_id, message_id, contact_info, get_back_keyboard("contact"))
    
    async def _handle_order_confirmation(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє підтвердження замовлення"""
        if data == "confirm_order_yes":
            # Отримуємо дані
            session = Database.get_user_session(user_id)
            temp_data = session["temp_data"]
            
            # Створюємо замовлення
            order_id = Database.create_order(user_id, temp_data)
            
            # Очищаємо сесію
            Database.clear_user_session(user_id)
            
            # Надсилаємо підтвердження
            response = "✅ <b>Замовлення оформлено!</b>\n\n"
            response += f"🆔 Номер замовлення: <b>#{order_id}</b>\n"
            response += f"👤 ПІБ: <b>{temp_data.get('name', '')}</b>\n"
            response += f"📱 Телефон: <b>{temp_data.get('phone', '')}</b>\n"
            response += f"🏙️ Місто: <b>{temp_data.get('city', '')}</b>\n"
            response += f"🏣 Адреса: <b>{temp_data.get('np_department', '')}</b>\n"
            response += f"💰 Сума: <b>{temp_data.get('total', 0):.2f} грн</b>\n\n"
            response += "📞 <b>Ми зв'яжемось з вами для підтвердження!</b>\n\n"
            response += "<i>Дякуємо за замовлення! 🌱</i>"
            
            # Логуємо
            print(f"\n{'='*80}")
            print(f"🛒 НОВЕ ПОВНЕ ЗАМОВЛЕННЯ #{order_id}:")
            print(f"👤 Клієнт: {temp_data.get('name', '')}")
            print(f"📞 Телефон: {temp_data.get('phone', '')}")
            print(f"🏙️ Місто: {temp_data.get('city', '')}")
            print(f"🏣 Адреса: {temp_data.get('np_department', '')}")
            print(f"💰 Сума: {temp_data.get('total', 0):.2f} грн")
            print(f"🆔 User ID: {user_id}")
            print(f"{'='*80}\n")
            
        else:
            response = "❌ <b>Замовлення скасовано</b>\n\n"
            response += "Ви можете продовжити покупки.\n"
            Database.clear_user_session(user_id)
        
        await self.api.edit_message(chat_id, message_id, response, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_unknown_callback(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє невідомий callback"""
        print(f"⚠️ Невідомий callback: {data}")
        welcome = get_welcome_text()
        await self.api.edit_message(chat_id, message_id, welcome, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")

# ==================== FLASK СЕРВЕР ДЛЯ RENDER ====================

app = Flask(__name__)

@app.route('/')
def home():
    return "🌱 Бот фермы 'Смак природи' працює! 🚀"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==================== ЗАПУСК БОТА ====================

async def main_async():
    """Асинхронна головна функція"""
    print("🌱 Завантаження бота ферми 'Смак природи'...")
    
    # Запускаем Flask сервер для Render
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"✅ Flask сервер запущено на порті 8080")
    
    # Ініціалізація бази даних
    init_database()
    print("✅ База даних ініціалізована")
    
    # Створюємо та запускаємо бота
    bot = FarmBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n\n🛑 Бот зупинено користувачем")
    except Exception as e:
        print(f"\n\n❌ Критична помилка: {e}")
    
    # Виводимо статистику
    print("\n" + "=" * 50)
    print("📊 ФІНАЛЬНА СТАТИСТИКА:")
    stats = Database.get_statistics()
    print(f"• Замовлень: {stats['total_orders']}")
    print(f"• Повідомлень: {stats['total_messages']}")
    print(f"• Користувачів: {stats['total_users']}")
    print("=" * 50)
    print("👋 До побачення!")

def main():
    """Синхронна обгортка для запуску"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
