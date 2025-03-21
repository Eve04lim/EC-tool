# database.py - スレッドセーフ版
import logging
import os
import sqlite3
import psycopg2
from datetime import datetime
import threading

from config import DATABASE_URL, DB_TYPE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logger = logging.getLogger(__name__)

class Database:
    """スレッドセーフなデータベース操作クラス"""
    
    _local = threading.local()
    
    def __init__(self):
        """初期化"""
        self.connect()
        self.create_tables()
    
    def connect(self):
        """データベースに接続する"""
        try:
            if DB_TYPE.lower() == "sqlite":
                self._local.connection = sqlite3.connect(DB_NAME)
                self._local.connection.row_factory = sqlite3.Row
            elif DB_TYPE.lower() == "postgresql":
                # Herokuの環境変数DATABASE_URLがある場合はそれを使用
                if 'DATABASE_URL' in os.environ:
                    import psycopg2
                    self._local.connection = psycopg2.connect(DATABASE_URL)
                else:
                    self._local.connection = psycopg2.connect(
                        dbname=DB_NAME,
                        user=DB_USER,
                        password=DB_PASSWORD,
                        host=DB_HOST,
                        port=DB_PORT
                    )
            else:
                raise ValueError(f"Unsupported database type: {DB_TYPE}")
            
            self._local.cursor = self._local.connection.cursor()
            logger.info(f"Connected to {DB_TYPE} database: {DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    @property
    def connection(self):
        """現在のスレッド用のコネクションを取得"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self.connect()
        return self._local.connection
    
    @property
    def cursor(self):
        """現在のスレッド用のカーソルを取得"""
        if not hasattr(self._local, 'cursor') or self._local.cursor is None:
            self.connect()
        return self._local.cursor
    
    def create_tables(self):
        """必要なテーブルを作成する"""
        try:
            # 商品テーブル
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                image_url TEXT,
                product_code TEXT,
                platform TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            ''')

            # 価格・在庫履歴テーブル
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                regular_price REAL,
                sale_price REAL,
                in_stock BOOLEAN NOT NULL,
                review_count INTEGER,
                review_rating REAL,
                fetched_at TIMESTAMP NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            # 通知履歴テーブル
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TIMESTAMP NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
            ''')

            self.connection.commit()
            logger.info("Database tables created or already exist")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
            raise

    def add_product(self, name, url, platform, image_url=None, product_code=None):
        """新しい商品を追加する"""
        try:
            now = datetime.now()
            self.cursor.execute(
                "INSERT INTO products (name, url, image_url, product_code, platform, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, url, image_url, product_code, platform, now, now)
            )
            self.connection.commit()
            product_id = self.cursor.lastrowid
            logger.info(f"Added new product: {name} (ID: {product_id})")
            return product_id
        except Exception as e:
            logger.error(f"Failed to add product: {e}")
            self.connection.rollback()
            raise

    def update_product(self, product_id, name=None, image_url=None, product_code=None):
        """商品情報を更新する"""
        try:
            updates = []
            params = []
            if name:
                updates.append("name = ?")
                params.append(name)
            if image_url:
                updates.append("image_url = ?")
                params.append(image_url)
            if product_code:
                updates.append("product_code = ?")
                params.append(product_code)
            
            if not updates:
                return
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(product_id)
            
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.connection.commit()
            logger.info(f"Updated product (ID: {product_id})")
        except Exception as e:
            logger.error(f"Failed to update product: {e}")
            self.connection.rollback()
            raise

    def add_price_history(self, product_id, regular_price, sale_price, in_stock, review_count=None, review_rating=None):
        """価格・在庫履歴を追加する"""
        try:
            now = datetime.now()
            self.cursor.execute(
                "INSERT INTO price_history (product_id, regular_price, sale_price, in_stock, review_count, review_rating, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (product_id, regular_price, sale_price, in_stock, review_count, review_rating, now)
            )
            self.connection.commit()
            history_id = self.cursor.lastrowid
            logger.info(f"Added price history for product {product_id}: ¥{regular_price}/¥{sale_price} (in stock: {in_stock})")
            return history_id
        except Exception as e:
            logger.error(f"Failed to add price history: {e}")
            self.connection.rollback()
            raise

    def add_notification(self, product_id, notification_type, message):
        """通知履歴を追加する"""
        try:
            now = datetime.now()
            self.cursor.execute(
                "INSERT INTO notifications (product_id, notification_type, message, sent_at) VALUES (?, ?, ?, ?)",
                (product_id, notification_type, message, now)
            )
            self.connection.commit()
            notification_id = self.cursor.lastrowid
            logger.info(f"Added notification for product {product_id}: {notification_type}")
            return notification_id
        except Exception as e:
            logger.error(f"Failed to add notification: {e}")
            self.connection.rollback()
            raise

    def get_all_products(self):
        """すべての登録商品を取得する"""
        try:
            self.cursor.execute("SELECT * FROM products")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            raise

    def get_product_by_id(self, product_id):
        """IDから商品を取得する"""
        try:
            self.cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get product by ID: {e}")
            raise

    def get_latest_price(self, product_id):
        """商品の最新価格・在庫情報を取得する"""
        try:
            self.cursor.execute(
                "SELECT * FROM price_history WHERE product_id = ? ORDER BY fetched_at DESC LIMIT 1",
                (product_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get latest price: {e}")
            raise

    def get_product_price_history(self, product_id, limit=10):
        """商品の価格履歴を取得する"""
        try:
            self.cursor.execute(
                "SELECT * FROM price_history WHERE product_id = ? ORDER BY fetched_at DESC LIMIT ?",
                (product_id, limit)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get price history: {e}")
            raise

    def close(self):
        """データベース接続を閉じる"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            self._local.cursor = None
            logger.info("Database connection closed")