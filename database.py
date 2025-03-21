# database.py - Supabase (PostgreSQL) 対応・スレッドセーフ版
import logging
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import threading

from config import DATABASE_URL, DB_TYPE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

logger = logging.getLogger(__name__)

class Database:
    _local = threading.local()

    def __init__(self):
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            if DB_TYPE.lower() == "sqlite":
                self._local.connection = sqlite3.connect(DB_NAME)
                self._local.connection.row_factory = sqlite3.Row
                self._local.cursor = self._local.connection.cursor()
            elif DB_TYPE.lower() == "postgresql":
                conn_str = DATABASE_URL if DATABASE_URL else f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"
                self._local.connection = psycopg2.connect(conn_str, cursor_factory=RealDictCursor)
                self._local.cursor = self._local.connection.cursor()
            else:
                raise ValueError(f"Unsupported database type: {DB_TYPE}")

            logger.info(f"Connected to {DB_TYPE} database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @property
    def connection(self):
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self.connect()
        return self._local.connection

    @property
    def cursor(self):
        if not hasattr(self._local, 'cursor') or self._local.cursor is None:
            self.connect()
        return self._local.cursor

    def create_tables(self):
        try:
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                image_url TEXT,
                product_code TEXT,
                platform TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            ''')

            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
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

            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
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
        try:
            now = datetime.now()
            self.cursor.execute(
                """INSERT INTO products (name, url, image_url, product_code, platform, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (name, url, image_url, product_code, platform, now, now)
            )
            product_id = self.cursor.fetchone()['id']
            self.connection.commit()
            logger.info(f"Added new product: {name} (ID: {product_id})")
            return product_id
        except Exception as e:
            logger.error(f"Failed to add product: {e}")
            self.connection.rollback()
            raise

    def add_price_history(self, product_id, regular_price, sale_price, in_stock, review_count=None, review_rating=None):
        try:
            now = datetime.now()
            self.cursor.execute(
                """INSERT INTO price_history (product_id, regular_price, sale_price, in_stock, review_count, review_rating, fetched_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (product_id, regular_price, sale_price, in_stock, review_count, review_rating, now)
            )
            history_id = self.cursor.fetchone()['id']
            self.connection.commit()
            logger.info(f"Added price history for product {product_id}")
            return history_id
        except Exception as e:
            logger.error(f"Failed to add price history: {e}")
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
        
    def get_latest_price(self, product_id):
        """商品の最新価格・在庫情報を取得する"""
        try:
            self.cursor.execute(
                "SELECT * FROM price_history WHERE product_id = %s ORDER BY fetched_at DESC LIMIT 1",
                (product_id,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get latest price: {e}")
            raise
        
    def get_product_by_id(self, product_id):
        """IDから商品を取得する"""
        try:
            self.cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get product by ID: {e}")
            raise
        
    def get_product_price_history(self, product_id, limit=10):
        """商品の価格履歴を取得する"""
        try:
            self.cursor.execute(
                "SELECT * FROM price_history WHERE product_id = %s ORDER BY fetched_at DESC LIMIT %s",
                (product_id, limit)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get price history: {e}")
            raise



    def close(self):
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.cursor.close()
            self._local.connection.close()
            self._local.connection = None
            self._local.cursor = None
            logger.info("Database connection closed")
