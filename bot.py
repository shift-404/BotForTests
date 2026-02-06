"""
БОТ ФЕРМИ "СМАК ПРИРОДИ" - ПОЛНАЯ ВЕРСИЯ СО ВСЕМИ ИСПРАВЛЕНИЯМИ
"""

import os
import json
import asyncio
import aiohttp
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import logging
from flask import Flask
import threading

# ==================== НАСТРОЙКА ====================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Проверка токена
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("❌ ОШИБКА: Токен не найден!")
    logger.error("Добавьте BOT_TOKEN в переменные окружения Render")
    exit(1)

logger.info(f"✅ Токен получен (первые 10 символов): {TOKEN[:10]}...")

# ==================== БАЗА ДАНИХ ====================

def init_database():
    """Ініціалізація бази даних"""
    conn = sqlite3.connect('farm_bot.db', check_same_thread=False)
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
    
    # Таблиця сесій
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT '',
            temp_data TEXT DEFAULT '{}',
            last_section TEXT DEFAULT 'main_menu',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблиця кошиків
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблиця елементів замовлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_name TEXT,
            quantity REAL,
            price_per_unit REAL
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблиця швидких замовлень
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quick_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            username TEXT,
            phone TEXT,
            product_id INTEGER,
            product_name TEXT,
            quantity REAL,
            contact_method TEXT,
            status TEXT DEFAULT 'нове',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

# ==================== ДАНІ ПРОДУКТІВ ====================

# URL фотографій для товарів (используем Render как хостинг)
BASE_URL = os.getenv("RENDER_EXTERNAL_URL", "https://botfortests.onrender.com")

PRODUCT_PHOTOS = {
    1: f"{BASE_URL}/static/products/1.jpg",  # Артишоки
    2: f"{BASE_URL}/static/products/2.jpg",  # Спаржа
    3: f"{BASE_URL}/static/products/3.jpg",  # Яблука
    4: f"{BASE_URL}/static/products/4.jpg",  # Інжир
    5: f"{BASE_URL}/static/products/5.jpg",  # Горіхи
    6: f"{BASE_URL}/static/products/6.jpg"   # Мед
}
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

# ==================== TELEGRAM API ====================

class TelegramAPI:
    """Асинхронний клас для роботи з Telegram API"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = None
        self.last_update_id = 0
        
    async def ensure_session(self):
        """Создает сессию если ее нет"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
    
    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def make_request(self, method: str, data: dict = None, params: dict = None) -> dict:
        """Выполняет запрос к Telegram API"""
        try:
            await self.ensure_session()
            url = f"{self.base_url}/{method}"
            
            if params:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка {method}: {response.status} - {error_text[:200]}")
                        return {"ok": False, "error_code": response.status}
            else:
                async with self.session.post(url, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка {method}: {response.status} - {error_text[:200]}")
                        return {"ok": False, "error_code": response.status}
                    
        except Exception as e:
            logger.error(f"❌ Ошибка запроса {method}: {str(e)}")
            return {"ok": False}
    
    async def get_updates(self, timeout: int = 30) -> list:
        """Получает обновления с использованием last_update_id"""
        params = {
            "offset": self.last_update_id + 1,
            "timeout": timeout,
            "limit": 100
        }
        
        result = await self.make_request("getUpdates", params=params)
        
        if result.get("ok"):
            updates = result.get("result", [])
            if updates:
                self.last_update_id = updates[-1]["update_id"]
            return updates
        else:
            # Если ошибка 409 - ждем и пробуем снова
            if result.get("error_code") == 409:
                logger.warning("⚠️ Конфликт с другим экземпляром бота. Жду 5 секунд...")
                await asyncio.sleep(5)
            return []
    
    async def send_message(self, chat_id: int, text: str, 
                          reply_markup: dict = None,
                          parse_mode: str = "HTML") -> bool:
        """Отправляет сообщение"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        result = await self.make_request("sendMessage", data=data)
        return result.get("ok", False)
    
    async def answer_callback(self, callback_id: str, text: str = None) -> bool:
        """Отвечает на callback запрос"""
        data = {"callback_query_id": callback_id}
        if text:
            data["text"] = text
        
        result = await self.make_request("answerCallbackQuery", data=data)
        return result.get("ok", False)
    
    async def edit_message(self, chat_id: int, message_id: int, text: str,
                          reply_markup: dict = None) -> bool:
        """Редактирует сообщение"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        result = await self.make_request("editMessageText", data=data)
        return result.get("ok", False)
    
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Удаляет сообщение"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        result = await self.make_request("deleteMessage", data=data)
        return result.get("ok", False)

# ==================== УТІЛІТИ БАЗИ ДАНИХ ====================

class Database:
    """Клас для роботи з базою даних"""
    
    @staticmethod
    def get_connection():
        """Повертає з'єднання з базою даних"""
        return sqlite3.connect('farm_bot.db', timeout=20, check_same_thread=False)
    
    @staticmethod
    def save_user(user_id: int, first_name: str = "", last_name: str = "", username: str = ""):
        """Зберігає або оновлює користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, first_name, last_name, username)
                VALUES (?, ?, ?, ?)
            ''', (user_id, first_name, last_name, username))
            
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения пользователя: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def get_user_session(user_id: int) -> Dict:
        """Отримує сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT state, temp_data, last_section 
                FROM user_sessions 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            
            if row:
                state, temp_data_json, last_section = row
                temp_data = json.loads(temp_data_json) if temp_data_json else {}
                return {
                    "state": state,
                    "temp_data": temp_data,
                    "last_section": last_section
                }
            return {"state": "", "temp_data": {}, "last_section": "main_menu"}
        except Exception as e:
            logger.error(f"❌ Ошибка получения сессии: {e}")
            return {"state": "", "temp_data": {}, "last_section": "main_menu"}
        finally:
            conn.close()
    
    @staticmethod
    def save_user_session(user_id: int, state: str = "", temp_data: Dict = None, last_section: str = ""):
        """Зберігає сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            temp_data_json = json.dumps(temp_data) if temp_data else "{}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_sessions (user_id, state, temp_data, last_section, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, state, temp_data_json, last_section))
            
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сессии: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def clear_user_session(user_id: int):
        """Очищає сесію користувача"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка очистки сессии: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def add_to_cart(user_id: int, product_id: int, quantity: float) -> bool:
        """Додає товар до кошика"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            # Проверяем, есть ли уже товар в корзине
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
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в корзину: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_cart_items(user_id: int) -> List[Dict]:
        """Отримує товари з кошика"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, product_id, quantity FROM carts WHERE user_id = ?', (user_id,))
            rows = cursor.fetchall()
            
            items = []
            for row in rows:
                cart_id, product_id, quantity = row
                product = next((p for p in PRODUCTS if p["id"] == product_id), None)
                if product:
                    items.append({
                        "cart_id": cart_id,
                        "product": product,
                        "quantity": quantity
                    })
            
            return items
        except Exception as e:
            logger.error(f"❌ Ошибка получения корзины: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    def clear_cart(user_id: int):
        """Очищає кошик"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка очистки корзины: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def remove_from_cart(cart_id: int):
        """Видаляє товар з кошика"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM carts WHERE id = ?', (cart_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из корзины: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def create_order(order_data: Dict) -> int:
        """Створює замовлення"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            # Используем транзакцию для избежания блокировок
            cursor.execute('BEGIN TRANSACTION')
            
            cursor.execute('''
                INSERT INTO orders (user_id, user_name, username, phone, city, np_department, total, order_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_data.get("user_id"),
                order_data.get("user_name"),
                order_data.get("username"),
                order_data.get("phone"),
                order_data.get("city"),
                order_data.get("np_department"),
                order_data.get("total"),
                order_data.get("order_type")
            ))
            
            order_id = cursor.lastrowid
            
            # Добавляем товары в заказ
            for item in order_data.get("items", []):
                cursor.execute('''
                    INSERT INTO order_items (order_id, product_name, quantity, price_per_unit)
                    VALUES (?, ?, ?, ?)
                ''', (
                    order_id,
                    item.get("product_name"),
                    item.get("quantity"),
                    item.get("price")
                ))
            
            # Очищаем корзину
            cursor.execute('DELETE FROM carts WHERE user_id = ?', (order_data.get("user_id"),))
            
            conn.commit()
            return order_id
        except Exception as e:
            logger.error(f"❌ Ошибка создания заказа: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    @staticmethod
    def save_message(user_id: int, user_name: str, username: str, text: str, message_type: str):
        """Зберігає повідомлення"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO messages (user_id, user_name, username, text, message_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, user_name, username, text, message_type))
            
            conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения сообщения: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def save_quick_order(user_id: int, user_name: str, username: str, product_id: int, 
                        product_name: str, quantity: float, phone: str = None, 
                        contact_method: str = "chat") -> int:
        """Зберігає швидке замовлення"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO quick_orders (user_id, user_name, username, product_id, product_name, 
                                        quantity, phone, contact_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, user_name, username, product_id, product_name, quantity, phone, contact_method))
            
            order_id = cursor.lastrowid
            conn.commit()
            return order_id
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения быстрого заказа: {e}")
            return 0
        finally:
            conn.close()
    
    @staticmethod
    def get_statistics() -> Dict:
        """Повертає статистику"""
        conn = Database.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM orders')
            total_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM messages')
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM carts')
            active_carts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM quick_orders')
            quick_orders = cursor.fetchone()[0]
            
            return {
                "total_orders": total_orders,
                "total_messages": total_messages,
                "total_users": total_users,
                "active_carts": active_carts,
                "quick_orders": quick_orders
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
        finally:
            conn.close()

# ==================== ГЕНЕРАТОРИ КЛАВІАТУР ====================

def create_inline_keyboard(buttons: List[List[Dict]]) -> Dict:
    """Створює inline клавіатуру"""
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
    """Головне меню"""
    buttons = [
        [{"text": "🏢 Про компанію", "callback_data": "company"}],
        [{"text": "📦 Наші продукти", "callback_data": "products"}],
        [{"text": "❓ Часті запитання", "callback_data": "faq"}],
        [{"text": "🛒 Моя корзина", "callback_data": "cart"}, 
         {"text": "📋 Мої замовлення", "callback_data": "my_orders"}],
        [{"text": "📞 Зв'язатися з нами", "callback_data": "contact"}]
    ]
    return create_inline_keyboard(buttons)

def get_back_keyboard(back_to: str) -> Dict:
    """Повертає кнопку 'Назад'"""
    return create_inline_keyboard([[{"text": "🔙 Назад", "callback_data": f"back_{back_to}"}]])

def get_products_menu() -> Dict:
    """Меню продуктів"""
    buttons = []
    
    for product in PRODUCTS:
        buttons.append([{
            "text": f"{product['image']} {product['name']} - {product['price']} грн/{product['unit']}",
            "callback_data": f"product_{product['id']}"
        }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_product_detail_menu(product_id: int) -> Dict:
    """Меню деталей продукту"""
    buttons = [
        [{"text": "🛒 Додати в кошик", "callback_data": f"add_to_cart_{product_id}"}],
        [{"text": "⚡ Швидке замовлення", "callback_data": f"quick_order_{product_id}"}],
        [{"text": "🔙 Назад", "callback_data": "back_products"}]
    ]
    return create_inline_keyboard(buttons)

def get_quick_order_menu(product_id: int) -> Dict:
    """Меню швидкого замовлення"""
    buttons = [
        [{"text": "📞 Зателефонуйте мені", "callback_data": f"quick_call_{product_id}"}],
        [{"text": "💬 Напишіть мені в чат", "callback_data": f"quick_chat_{product_id}"}],
        [{"text": "🔙 Назад", "callback_data": f"product_{product_id}"}]
    ]
    return create_inline_keyboard(buttons)

def get_faq_menu() -> Dict:
    """Меню FAQ"""
    buttons = []
    
    for i, faq in enumerate(FAQS, 1):
        buttons.append([{
            "text": f"❔ {faq['question'][:40]}...",
            "callback_data": f"faq_{i}"
        }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_contact_menu() -> Dict:
    """Меню контактів"""
    buttons = [
        [{"text": "📞 Зателефонувати", "callback_data": "call_us"}],
        [{"text": "📧 Написати email", "callback_data": "email_us"}],
        [{"text": "📍 Наша адреса", "callback_data": "our_address"}],
        [{"text": "💬 Написати нам тут", "callback_data": "write_here"}],
        [{"text": "🔙 Назад", "callback_data": "back_main_menu"}]
    ]
    return create_inline_keyboard(buttons)

def get_cart_menu(cart_items: List) -> Dict:
    """Меню корзини"""
    buttons = []
    
    if cart_items:
        buttons.append([{"text": "✅ Оформити замовлення", "callback_data": "checkout_cart"}])
        buttons.append([{"text": "🗑️ Очистити корзину", "callback_data": "clear_cart"}])
        
        for item in cart_items:
            product_name = item["product"]["name"][:20]
            if len(item["product"]["name"]) > 20:
                product_name += "..."
            
            buttons.append([{
                "text": f"❌ {product_name} ({item['quantity']}{item['product']['unit']})",
                "callback_data": f"remove_from_cart_{item['cart_id']}"
            }])
    
    buttons.append([{"text": "🔙 Назад", "callback_data": "back_main_menu"}])
    return create_inline_keyboard(buttons)

def get_order_confirmation_keyboard() -> Dict:
    """Клавіатура підтвердження замовлення"""
    return create_inline_keyboard([
        [{"text": "✅ Так, продовжити", "callback_data": "confirm_order_yes"}],
        [{"text": "❌ Ні, скасувати", "callback_data": "confirm_order_no"}]
    ])

# ==================== УТІЛІТИ ДЛЯ ВАЛІДАЦІЇ ====================

def parse_quantity(text: str) -> Tuple[bool, float, str]:
    """Парсить кількість"""
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
            return False, 0, "❌ Занадто велика кількість. Максимум 100"
        
        return True, quantity, ""
    except ValueError:
        return False, 0, "❌ Некоректний формат числа"

def validate_phone(phone: str) -> Tuple[bool, str]:
    """Валідує телефон"""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    if re.match(r'^(\+38|38)?0\d{9}$', phone):
        if phone.startswith("0"):
            phone = "+38" + phone
        elif phone.startswith("38"):
            phone = "+" + phone
        elif phone.startswith("+380"):
            pass
        else:
            phone = "+380" + phone[1:] if phone.startswith("+") else "+380" + phone
        
        return True, phone
    
    return False, phone

# ==================== ГЕНЕРАТОРИ ТЕКСТУ ====================

def get_welcome_text() -> str:
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
    """Текст продукту"""
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

def get_quick_order_text(product_id: int) -> str:
    """Текст швидкого замовлення"""
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return "❌ Продукт не знайдено"
    
    return f"""
<b>⚡ Швидке замовлення: {product['image']} {product['name']}</b>

💬 <b>Як ви бажаєте, щоб ми з вами зв'язалися?</b>

📞 <b>Зателефонуйте мені</b> - ми зателефонуємо вам для уточнення деталей
💬 <b>Напишіть мені в чат</b> - ви можете написати всі деталі тут і ми відповімо

<i>Оберіть зручний для вас спосіб зв'язку 👇</i>
    """

def get_faq_text(faq_id: int) -> str:
    """Текст FAQ"""
    if 0 <= faq_id - 1 < len(FAQS):
        faq = FAQS[faq_id - 1]
        return f"""
<b>❔ {faq['question']}</b>

{faq['answer']}

<i>📞 Маєте інші запитання? Зв'яжіться з нами!</i>
        """
    return "❌ Питання не знайдено"

def get_contact_text() -> str:
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

def get_cart_text(cart_items: List[Dict]) -> str:
    """Текст корзини"""
    if not cart_items:
        return "🛒 <b>Ваша корзина порожня</b>\n\nДодайте товари з каталогу!"
    
    text = "🛒 <b>Ваша корзина</b>\n\n"
    
    total = 0
    for i, item in enumerate(cart_items, 1):
        quantity = item["quantity"]
        product = item["product"]
        item_total = product["price"] * quantity
        
        text += f"<b>{i}. {product['name']}</b>\n"
        text += f"   📊 Кількість: <b>{quantity} {product['unit']}</b>\n"
        text += f"   💰 Ціна: {product['price']} грн/{product['unit']} × {quantity} = <b>{item_total:.2f} грн</b>\n\n"
        
        total += item_total
    
    text += f"<b>📊 Всього товарів:</b> {len(cart_items)}\n"
    text += f"<b>💰 Загальна сума:</b> <b>{total:.2f} грн</b>\n\n"
    text += "<i>Для оформлення замовлення натисніть кнопку нижче</i>"
    
    return text

# ==================== ОСНОВНИЙ КЛАС БОТА ====================

class FarmBot:
    def __init__(self):
        self.api = TelegramAPI(TOKEN)
        self.running = True
        self.error_count = 0
        self.max_errors = 10
        self.update_counter = 0
        
    async def start(self):
        """Запуск бота"""
        logger.info("=" * 80)
        logger.info("🌱 БОТ ФЕРМИ 'Смак природи' ЗАПУЩЕНО")
        logger.info(f"🔑 Токен: {TOKEN[:10]}...")
        logger.info("=" * 80)
        
        init_database()
        
        stats = Database.get_statistics()
        logger.info("📊 Статистика:")
        logger.info(f"• Користувачів: {stats.get('total_users', 0)}")
        logger.info(f"• Замовлень: {stats.get('total_orders', 0)}")
        logger.info(f"• Повідомлень: {stats.get('total_messages', 0)}")
        logger.info(f"• Швидких замовлень: {stats.get('quick_orders', 0)}")
        logger.info(f"• Активних кошиків: {stats.get('active_carts', 0)}")
        logger.info(f"• Продуктів у базі: {len(PRODUCTS)}")
        logger.info("=" * 80)
        logger.info("🔄 Очікування повідомлень...\n")
        
        while self.running and self.error_count < self.max_errors:
            try:
                updates = await self.api.get_updates(timeout=30)
                
                if updates:
                    logger.info(f"📥 Получено обновлений: {len(updates)}")
                    self.update_counter += len(updates)
                    
                    for update in updates:
                        await self.process_update(update)
                
                # Сбрасываем счетчик ошибок при успешном получении
                self.error_count = 0
                
                # Периодически выводим статистику
                if self.update_counter % 10 == 0 and self.update_counter > 0:
                    logger.info(f"📊 Всего обработано: {self.update_counter} обновлений")
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Бот зупиняється...")
                self.running = False
            except Exception as e:
                self.error_count += 1
                logger.error(f"⚠️ Помилка в основному циклі ({self.error_count}/{self.max_errors}): {e}")
                
                if self.error_count >= self.max_errors:
                    logger.error("❌ Слишком много ошибок. Перезапуск через 30 секунд...")
                    await asyncio.sleep(30)
                    self.error_count = 0
                else:
                    await asyncio.sleep(1)
        
        await self.api.close()
        logger.info(f"\n📊 ИТОГО: Обработано {self.update_counter} обновлений, ошибок: {self.error_count}")
        logger.info("👋 Бот остановлен")
    
    async def process_update(self, update: Dict):
        """Обробляє оновлення"""
        try:
            if "message" in update:
                await self.handle_message(update["message"])
            elif "callback_query" in update:
                await self.handle_callback(update["callback_query"])
        except Exception as e:
            logger.error(f"❌ Помилка обробки оновлення: {e}")
    
    async def handle_message(self, message: Dict):
        """Обробляє повідомлення"""
        try:
            chat_id = message["chat"]["id"]
            user = message.get("from", {})
            user_id = user.get("id")
            text = message.get("text", "").strip()
            
            logger.info(f"👤 [{datetime.now().strftime('%H:%M:%S')}] {user.get('first_name', 'Користувач')}: {text}")
            
            # Зберігаємо користувача
            Database.save_user(
                user_id,
                user.get("first_name", ""),
                user.get("last_name", ""),
                user.get("username", "")
            )
            
            # Команди /start та /cancel
            if text == "/start" or text == "/cancel" or text.lower() == "скасувати":
                Database.clear_user_session(user_id)
                welcome = get_welcome_text()
                await self.api.send_message(chat_id, welcome, get_main_menu())
                Database.save_user_session(user_id, last_section="main_menu")
                return
            
            # Команда /help
            if text == "/help":
                await self.api.send_message(chat_id, "ℹ️ Допомога: оберіть опцію з меню", get_main_menu())
                return
            
            # Отримуємо стан користувача
            session = Database.get_user_session(user_id)
            state = session["state"]
            temp_data = session["temp_data"]
            
            # Обробка станів
            if state == "waiting_quantity":
                await self._handle_quantity_input(chat_id, user_id, user, text, temp_data)
            
            elif state == "waiting_message":
                await self._handle_message_input(chat_id, user_id, user, text)
            
            elif state.startswith("full_order_"):
                await self._handle_full_order_input(chat_id, user_id, user, text, state, temp_data)
            
            elif state == "waiting_phone_for_quick_order":
                await self._handle_quick_order_phone(chat_id, user_id, user, text, temp_data)
            
            else:
                # Звичайне повідомлення
                await self._handle_regular_message(chat_id, user_id, user, text)
                
        except Exception as e:
            logger.error(f"❌ ОШИБКА В handle_message: {e}")
    
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
            response += f"<b>Ціна:</b> {product['price']} грн/{product['unit']}\n\n"
            response += "📊 <b>Введіть кількість (тільки число):</b>\n"
            response += f"<i>Наприклад: 1, 1.5, 2.3 (в {product['unit']})</i>"
            
            await self.api.send_message(chat_id, response)
            return
        
        # Додаємо до кошика
        Database.add_to_cart(user_id, product_id, quantity)
        
        # Очищаємо сесію
        Database.clear_user_session(user_id)
        
        # Показуємо підтвердження
        total_price = product["price"] * quantity
        response = f"✅ <b>{product['name']}</b> додано до кошика!\n\n"
        response += f"📊 Кількість: <b>{quantity} {product['unit']}</b>\n"
        response += f"💰 Ціна: {product['price']} грн/{product['unit']}\n"
        response += f"💵 Сума: <b>{total_price:.2f} грн</b>\n\n"
        
        cart_items = Database.get_cart_items(user_id)
        response += f"🛒 У кошику: <b>{len(cart_items)} товар(ів)</b>\n\n"
        response += "<i>Продовжуйте додавати товари або перейдіть до оформлення замовлення.</i>"
        
        await self.api.send_message(chat_id, response)
        
        # Показуємо продукти
        products_text = "📦 <b>Наші продукти</b>\n\nОберіть продукт для детальної інформації:"
        await self.api.send_message(chat_id, products_text, get_products_menu())
        Database.save_user_session(user_id, last_section="products")
    
    async def _handle_message_input(self, chat_id: int, user_id: int, user: Dict, text: str):
        """Обробляє введення повідомлення"""
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
        username = user.get('username', 'немає')
        
        # Зберігаємо повідомлення
        Database.save_message(user_id, user_name, username, text, "повідомлення з меню")
        
        # Логуємо
        logger.info(f"\n{'='*80}")
        logger.info(f"💬 НОВЕ ПОВІДОМЛЕННЯ:")
        logger.info(f"👤 Ім'я: {user_name}")
        logger.info(f"📱 Username: {username}")
        logger.info(f"🆔 ID: {user_id}")
        logger.info(f"💬 Текст: {text}")
        logger.info(f"🕒 Час: {datetime.now().isoformat()}")
        logger.info(f"{'='*80}\n")
        
        # Відповідаємо
        response = "✅ <b>Повідомлення отримано!</b>\n\n"
        response += "Ми відповімо вам найближчим часом.\n"
        response += "<i>Дякуємо за звернення! 🌱</i>"
        
        await self.api.send_message(chat_id, response, get_main_menu())
        Database.clear_user_session(user_id)
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_full_order_input(self, chat_id: int, user_id: int, user: Dict, text: str, state: str, temp_data: Dict):
        """Обробляє введення для замовлення"""
        if state == "full_order_name":
            temp_data["user_name"] = text
            temp_data["username"] = user.get("username", "немає")
            Database.save_user_session(user_id, "full_order_phone", temp_data)
            
            response = "📱 <b>Введіть ваш номер телефону:</b>\n\n"
            response += "<i>Приклад: +380501234567 або 0501234567</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_phone":
            # Валідація телефону
            phone = text.strip()
            is_valid, formatted_phone = validate_phone(phone)
            
            if not is_valid:
                response = f"❌ <b>Невірний номер телефону!</b>\n\n"
                response += "📱 <b>Введіть ваш номер телефону ще раз:</b>\n"
                response += "<i>Приклад: +380501234567 або 0501234567</i>"
                
                await self.api.send_message(chat_id, response)
                return
            
            temp_data["phone"] = formatted_phone
            Database.save_user_session(user_id, "full_order_city", temp_data)
            
            response = "🏙️ <b>Введіть місто доставки:</b>\n\n"
            response += "<i>Наприклад: Київ, Львів, Одеса</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_city":
            temp_data["city"] = text
            Database.save_user_session(user_id, "full_order_np", temp_data)
            
            # ИСПРАВЛЕНО: убрано "или адрес"
            response = "🏣 <b>Введіть номер відділення Нової Пошти:</b>\n\n"
            response += "<i>Наприклад: Відділення №25</i>"
            await self.api.send_message(chat_id, response)
        
        elif state == "full_order_np":
            temp_data["np_department"] = text
            
            # Розраховуємо суму
            cart_items = Database.get_cart_items(user_id)
            total = sum(item["product"]["price"] * item["quantity"] for item in cart_items)
            temp_data["total"] = total
            temp_data["order_type"] = "повне замовлення"
            temp_data["user_id"] = user_id
            
            # Підготовлюємо товари
            order_items = []
            for item in cart_items:
                order_items.append({
                    "product_name": item["product"]["name"],
                    "quantity": item["quantity"],
                    "price": item["product"]["price"]
                })
            
            temp_data["items"] = order_items
            
            # Зберігаємо
            Database.save_user_session(user_id, "full_order_confirm", temp_data)
            
            # Показуємо підтвердження
            response = "✅ <b>Дані отримано! Перевірте інформацію:</b>\n\n"
            response += f"👤 <b>ПІБ:</b> {temp_data.get('user_name', '')}\n"
            response += f"📱 <b>Телефон:</b> {temp_data.get('phone', '')}\n"
            response += f"🏙️ <b>Місто:</b> {temp_data.get('city', '')}\n"
            response += f"🏣 <b>Відділення Нової Пошти:</b> {text}\n"
            response += f"🛒 <b>Товарів у кошику:</b> {len(cart_items)}\n"
            response += f"💰 <b>Загальна сума:</b> {total:.2f} грн\n\n"
            response += "<b>Підтвердити замовлення?</b>"
            
            await self.api.send_message(chat_id, response, get_order_confirmation_keyboard())
    
    async def _handle_quick_order_phone(self, chat_id: int, user_id: int, user: Dict, text: str, temp_data: Dict):
        """Обробляє телефон для швидкого замовлення"""
        phone = text.strip()
        product_id = temp_data.get("product_id")
        
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            await self.api.send_message(chat_id, "❌ Помилка: продукт не знайдено", get_main_menu())
            Database.clear_user_session(user_id)
            return
        
        # Валідація
        is_valid, formatted_phone = validate_phone(phone)
        
        if not is_valid:
            response = f"❌ <b>Невірний номер телефону!</b>\n\n"
            response += "📱 <b>Введіть ваш номер телефону ще раз:</b>\n"
            response += "<i>Приклад: +380501234567 або 0501234567</i>"
            
            await self.api.send_message(chat_id, response)
            return
        
        # Зберігаємо швидке замовлення
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
        username = user.get('username', 'немає')
        
        order_id = Database.save_quick_order(
            user_id, user_name, username, product_id, product["name"], 
            0, formatted_phone, "call"
        )
        
        # Логуємо
        logger.info(f"\n{'='*80}")
        logger.info(f"⚡ ШВИДКЕ ЗАМОВЛЕННЯ #{order_id} (ТЕЛЕФОН):")
        logger.info(f"👤 Клієнт: {user_name}")
        logger.info(f"📞 Телефон: {formatted_phone}")
        logger.info(f"📦 Продукт: {product['name']}")
        logger.info(f"🆔 User ID: {user_id}")
        logger.info(f"📱 Username: {username}")
        logger.info(f"{'='*80}\n")
        
        # Очищаємо сесію
        Database.clear_user_session(user_id)
        
        # Відповідаємо
        response = f"✅ <b>Швидке замовлення прийнято!</b>\n\n"
        response += f"🆔 <b>Номер замовлення:</b> #{order_id}\n"
        response += f"📦 <b>Продукт:</b> {product['name']}\n"
        response += f"📞 <b>Ваш телефон:</b> {formatted_phone}\n\n"
        response += "<b>Ми зателефонуємо вам найближчим часом для уточнення деталей!</b>\n\n"
        response += "<i>Дякуємо за замовлення! 🌱</i>"
        
        await self.api.send_message(chat_id, response, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_regular_message(self, chat_id: int, user_id: int, user: Dict, text: str):
        """Обробляє звичайне повідомлення"""
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
        username = user.get('username', 'немає')
        
        # Зберігаємо повідомлення
        Database.save_message(user_id, user_name, username, text, "повідомлення в чаті")
        
        # Відповідаємо
        response = "✅ <b>Повідомлення отримано!</b>\n\n"
        response += "Ми відповімо вам найближчим часом.\n"
        response += "<i>Дякуємо за звернення! 🌱</i>"
        
        await self.api.send_message(chat_id, response, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def handle_callback(self, callback: Dict):
        """Обробляє callback"""
        try:
            callback_id = callback["id"]
            message = callback["message"]
            chat_id = message["chat"]["id"]
            message_id = message["message_id"]
            data = callback["data"]
            user = callback["from"]
            user_id = user["id"]
            
            logger.info(f"🖱️ [{datetime.now().strftime('%H:%M:%S')}] {user.get('first_name', 'Користувач')} натиснув: {data}")
            
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
            
            elif data.startswith("quick_order_"):
                await self._handle_quick_order(chat_id, message_id, user_id, data)
            
            elif data.startswith("quick_call_"):
                await self._handle_quick_call(chat_id, message_id, user_id, data)
            
            elif data.startswith("quick_chat_"):
                await self._handle_quick_chat(chat_id, message_id, user_id, data)
            
            elif data == "faq":
                await self._handle_faq(chat_id, message_id, user_id)
            
            elif data.startswith("faq_"):
                await self._handle_faq_detail(chat_id, message_id, user_id, data)
            
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
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки callback: {e}")
            # При ошибке показываем главное меню
            try:
                text = "❌ <b>Сталася помилка</b>\n\n"
                text += "Будь ласка, спробуйте ще раз або використайте /start"
                keyboard = get_main_menu()
                await self.api.edit_message(chat_id, message_id, text, keyboard)
            except:
                pass
    
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
            
            # Зберігаємо сесію
            temp_data = {"product_id": product_id}
            Database.save_user_session(user_id, "waiting_quantity", temp_data)
            
            # Видаляємо повідомлення з кнопками
            await self.api.delete_message(chat_id, message_id)
            
            # Запитуємо кількість
            response = f"📦 <b>Додавання {product['name']} до кошика</b>\n\n"
            response += f"💰 Ціна: {product['price']} грн/{product['unit']}\n\n"
            response += "📊 <b>Введіть кількість (тільки число):</b>\n\n"
            response += f"<i>Наприклад: 1, 1.5, 2.3 (в {product['unit']})</i>"
            
            await self.api.send_message(chat_id, response)
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка додавання до кошика", get_back_keyboard("products"))
    
    async def _handle_quick_order(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє швидке замовлення"""
        try:
            product_id = int(data.split("_")[2])
            product = next((p for p in PRODUCTS if p["id"] == product_id), None)
            
            if not product:
                await self.api.edit_message(chat_id, message_id, "❌ Продукт не знайдено", get_back_keyboard("products"))
                return
            
            # Показуємо меню вибору способу зв'язку (без запиту кількості)
            quick_order_text = get_quick_order_text(product_id)
            await self.api.edit_message(chat_id, message_id, quick_order_text, get_quick_order_menu(product_id))
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка швидкого замовлення", get_back_keyboard("products"))
    
    async def _handle_quick_call(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє вибір телефону для швидкого замовлення"""
        try:
            product_id = int(data.split("_")[2])
            product = next((p for p in PRODUCTS if p["id"] == product_id), None)
            
            if not product:
                await self.api.edit_message(chat_id, message_id, "❌ Продукт не знайдено", get_back_keyboard("products"))
                return
            
            # Зберігаємо сесію для запиту телефона
            temp_data = {"product_id": product_id}
            Database.save_user_session(user_id, "waiting_phone_for_quick_order", temp_data)
            
            # Видаляємо повідомлення
            await self.api.delete_message(chat_id, message_id)
            
            # Запитуємо телефон
            response = f"📞 <b>Зателефонуйте мені: {product['name']}</b>\n\n"
            response += f"💰 Ціна: {product['price']} грн/{product['unit']}\n\n"
            response += "📱 <b>Введіть ваш номер телефону:</b>\n\n"
            response += "<i>Приклад: +380501234567 або 0501234567</i>\n\n"
            response += "<b>Ми зателефонуємо вам для уточнення деталей замовлення!</b>"
            
            await self.api.send_message(chat_id, response)
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка швидкого замовлення", get_back_keyboard("products"))
    
    async def _handle_quick_chat(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє вибір чату для швидкого замовлення"""
        try:
            product_id = int(data.split("_")[2])
            product = next((p for p in PRODUCTS if p["id"] == product_id), None)
            
            if not product:
                await self.api.edit_message(chat_id, message_id, "❌ Продукт не знайдено", get_back_keyboard("products"))
                return
            
            # Видаляємо повідомлення
            await self.api.delete_message(chat_id, message_id)
            
            response = f"💬 <b>Напишіть мені в чат: {product['name']}</b>\n\n"
            response += f"💰 Ціна: {product['price']} грн/{product['unit']}\n\n"
            response += "💬 <b>Просто напишіть ваше повідомлення в цей чат!</b>\n\n"
            response += "Вкажіть:\n"
            response += "• Бажану кількість\n"
            response += "• Контактні дані\n"
            response += "• Бажаний час доставки\n\n"
            response += "<b>Ми відповімо вам найближчим часом для уточнення деталей замовлення!</b>"
            
            await self.api.send_message(chat_id, response)
            
            # Логуємо в консоль
            user = Database.get_user_session(user_id)
            user_name = f"User_{user_id}"
            
            logger.info(f"\n{'='*80}")
            logger.info(f"⚡ ШВИДКЕ ЗАМОВЛЕННЯ (ЧАТ):")
            logger.info(f"👤 Клієнт: {user_name}")
            logger.info(f"📦 Продукт: {product['name']}")
            logger.info(f"💰 Ціна: {product['price']} грн/{product['unit']}")
            logger.info(f"🆔 User ID: {user_id}")
            logger.info(f"💬 Контакт: Чат Telegram")
            logger.info(f"{'='*80}\n")
            
            Database.clear_user_session(user_id)
            
        except:
            await self.api.edit_message(chat_id, message_id, "❌ Помилка швидкого замовлення", get_back_keyboard("products"))
    
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
        text = "📋 <b>Мої замовлення</b>\n\n"
        text += "Функція перегляду замовлень знаходиться в розробці.\n"
        text += "<i>Зв'яжіться з нами для отримання інформації про ваші замовлення.</i>"
        
        await self.api.edit_message(chat_id, message_id, text, get_back_keyboard("main_menu"))
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
            # Получаем данные
            session = Database.get_user_session(user_id)
            temp_data = session["temp_data"]
            
            # ИСПРАВЛЕНО: использование транзакций для избежания блокировок
            try:
                # Создаем заказ
                order_id = Database.create_order(temp_data)
                
                if order_id > 0:
                    # Логируем
                    logger.info(f"\n{'='*80}")
                    logger.info(f"✅ НОВЫЙ ЗАКАЗ #{order_id}:")
                    logger.info(f"👤 Клиент: {temp_data.get('user_name', '')}")
                    logger.info(f"📞 Телефон: {temp_data.get('phone', '')}")
                    logger.info(f"🏙️ Город: {temp_data.get('city', '')}")
                    logger.info(f"🏣 НП: {temp_data.get('np_department', '')}")
                    logger.info(f"💰 Сумма: {temp_data.get('total', 0):.2f} грн")
                    logger.info(f"🛒 Товаров: {len(temp_data.get('items', []))}")
                    logger.info(f"🆔 User ID: {user_id}")
                    logger.info(f"{'='*80}\n")
                    
                    # Очищаем сессию
                    Database.clear_user_session(user_id)
                    
                    # Отправляем подтверждение
                    text = f"✅ <b>Замовлення оформлено!</b>\n\n"
                    text += f"🆔 Номер замовлення: <b>#{order_id}</b>\n"
                    text += f"👤 ПІБ: <b>{temp_data.get('user_name', '')}</b>\n"
                    text += f"📱 Телефон: <b>{temp_data.get('phone', '')}</b>\n"
                    text += f"🏙️ Місто: <b>{temp_data.get('city', '')}</b>\n"
                    text += f"🏣 Відділення Нової Пошти: <b>{temp_data.get('np_department', '')}</b>\n"
                    text += f"💰 Сума: <b>{temp_data.get('total', 0):.2f} грн</b>\n\n"
                    text += "📞 <b>Ми зв'яжемось з вами для підтвердження!</b>\n\n"
                    text += "<i>Дякуємо за замовлення! 🌱</i>"
                else:
                    text = "❌ <b>Помилка оформлення замовлення!</b>\n\n"
                    text += "Будь ласка, спробуйте ще раз або зв'яжіться з нами.\n\n"
                    text += "<i>Вибачте за незручності.</i>"
                    Database.clear_user_session(user_id)
            except Exception as e:
                logger.error(f"❌ Ошибка при создании заказа: {e}")
                text = "❌ <b>Помилка оформлення замовлення!</b>\n\n"
                text += "Будь ласка, спробуйте ще раз.\n\n"
                text += "<i>Вибачте за незручності.</i>"
                Database.clear_user_session(user_id)
            
        else:
            text = "❌ <b>Замовлення скасовано</b>\n\n"
            text += "Ви можете продовжити покупки.\n"
            text += "<i>Ваша корзина збережена.</i>"
            Database.clear_user_session(user_id)
        
        keyboard = get_main_menu()
        await self.api.edit_message(chat_id, message_id, text, keyboard)
        Database.save_user_session(user_id, last_section="main_menu")
    
    async def _handle_unknown_callback(self, chat_id: int, message_id: int, user_id: int, data: str):
        """Обробляє невідомий callback"""
        logger.warning(f"⚠️ Невідомий callback: {data}")
        welcome = get_welcome_text()
        await self.api.edit_message(chat_id, message_id, welcome, get_main_menu())
        Database.save_user_session(user_id, last_section="main_menu")

# ==================== FLASK СЕРВЕР ====================

app = Flask(__name__, static_folder='static')

@app.route('/')
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Бот ферми "Смак природи"</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2e7d32;
        }
        .status {
            padding: 10px;
            background: #e8f5e9;
            border-radius: 5px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌱 Бот ферми "Смак природи"</h1>
        <div class="status">
            <h3>✅ Бот работает и готов к приему сообщений!</h3>
            <p>Бот успешно запущен и подключен к Telegram API.</p>
        </div>
        <p><a href="/health">Проверить статус (health check)</a></p>
        <p><a href="/ping">Пинг сервера</a></p>
    </div>
</body>
</html>
"""

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

# ==================== ЗАПУСК ====================

async def main():
    """Головна функція"""
    bot = FarmBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
    finally:
        if hasattr(bot, 'api'):
            await bot.api.close()

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"✅ Flask сервер запущено на порті {os.environ.get('PORT', 8080)}")
    
    # Запускаем бота
    asyncio.run(main())
    


