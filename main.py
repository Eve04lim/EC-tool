# main.py - メインアプリケーション
import logging
import argparse
import time
import json
import random
import schedule
from datetime import datetime
import pandas as pd
import os
from typing import List, Dict, Any, Optional

# ローカルモジュールのインポート
from config import (
    ENABLE_GSHEETS, ENABLE_PROXY, PROXY_LIST, LOG_LEVEL, LOG_FILE,
    REQUEST_INTERVAL
)
from database import Database
from scrapers import get_scraper_for_url
from notifier import Notifier
from gsheets import GoogleSheetsExporter

# ロギングの設定
def setup_logging():
    """ロギングの設定を行う"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class ECTracker:
    """EC商品価格・在庫追跡ツールのメインクラス"""
    
    def __init__(self):
        """初期化"""
        self.db = Database()
        self.notifier = Notifier(self.db)
        self.gsheets_exporter = GoogleSheetsExporter() if ENABLE_GSHEETS else None
        logger.info("ECTracker initialized")
    
    def add_product(self, url: str) -> Optional[int]:
        """新しい商品を追加する"""
        try:
            # スクレイパーを取得
            proxy = self._get_random_proxy() if ENABLE_PROXY else None
            scraper = get_scraper_for_url(url, proxy=proxy)
            
            # 商品情報を取得
            product_data = scraper.scrape_product(url)
            scraper.close()
            
            # データベースに追加
            if product_data and product_data['name']:
                product_id = self.db.add_product(
                    name=product_data['name'],
                    url=url,
                    platform=product_data['platform'],
                    image_url=product_data['image_url'],
                    product_code=product_data['product_code']
                )
                
                # 初回の価格・在庫情報を保存
                self.db.add_price_history(
                    product_id=product_id,
                    regular_price=product_data['regular_price'],
                    sale_price=product_data['sale_price'],
                    in_stock=product_data['in_stock'],
                    review_count=product_data['review_count'],
                    review_rating=product_data['review_rating']
                )
                
                logger.info(f"Added new product: {product_data['name']} (ID: {product_id})")
                return product_id
            else:
                logger.error(f"Failed to scrape product data from: {url}")
                return None
        except Exception as e:
            logger.error(f"Error adding product {url}: {e}")
            return None
    
    def update_all_products(self) -> int:
        """すべての商品情報を更新する"""
        products = self.db.get_all_products()
        if not products:
            logger.warning("No products to update")
            return 0
        
        updated_count = 0
        for product in products:
            try:
                # 少し待機して連続リクエストを避ける
                time.sleep(REQUEST_INTERVAL + random.uniform(1, 3))
                
                # 商品情報を更新
                success = self.update_product(product['id'])
                if success:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error updating product {product['id']}: {e}")
        
        logger.info(f"Updated {updated_count}/{len(products)} products")
        
        # Google Sheetsにエクスポート
        if ENABLE_GSHEETS and self.gsheets_exporter and updated_count > 0:
            try:
                self.gsheets_exporter.export_products(self.db)
                self.gsheets_exporter.export_price_history(self.db)
            except Exception as e:
                logger.error(f"Failed to export to Google Sheets: {e}")
        
        return updated_count
    
    def update_product(self, product_id: int) -> bool:
        """特定の商品情報を更新する"""
        try:
            product = self.db.get_product_by_id(product_id)
            if not product:
                logger.error(f"Product not found: {product_id}")
                return False
            
            # 最新の価格情報を取得
            latest_price = self.db.get_latest_price(product_id)
            
            # スクレイパーを取得
            proxy = self._get_random_proxy() if ENABLE_PROXY else None
            scraper = get_scraper_for_url(product['url'], proxy=proxy)
            
            # 商品情報を取得
            product_data = scraper.scrape_product(product['url'])
            scraper.close()
            
            if not product_data or not product_data['name']:
                logger.error(f"Failed to scrape product data: {product['url']}")
                return False
            
            # 商品情報を更新（必要な場合）
            if (product_data['name'] and product_data['name'] != product['name']) or \
               (product_data['image_url'] and product_data['image_url'] != product['image_url']) or \
               (product_data['product_code'] and product_data['product_code'] != product['product_code']):
                self.db.update_product(
                    product_id=product_id,
                    name=product_data['name'],
                    image_url=product_data['image_url'],
                    product_code=product_data['product_code']
                )
            
            # 価格・在庫情報を追加
            self.db.add_price_history(
                product_id=product_id,
                regular_price=product_data['regular_price'],
                sale_price=product_data['sale_price'],
                in_stock=product_data['in_stock'],
                review_count=product_data['review_count'],
                review_rating=product_data['review_rating']
            )
            
            # 価格変動をチェック
            if latest_price:
                old_price = latest_price['sale_price'] or latest_price['regular_price']
                new_price = product_data['sale_price'] or product_data['regular_price']
                self.notifier.check_price_change(product_id, new_price, old_price)
                
                # 在庫状況の変化をチェック
                self.notifier.check_stock_change(product_id, product_data['in_stock'], latest_price['in_stock'])
            
            logger.info(f"Updated product {product_id}: {product['name']}")
            return True
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return False
    
    def export_to_gsheets(self) -> bool:
        """Google Sheetsにデータをエクスポートする"""
        if not ENABLE_GSHEETS or not self.gsheets_exporter:
            logger.warning("Google Sheets export is disabled")
            return False
        
        try:
            self.gsheets_exporter.export_products(self.db)
            self.gsheets_exporter.export_price_history(self.db)
            return True
        except Exception as e:
            logger.error(f"Failed to export to Google Sheets: {e}")
            return False
    
    def _get_random_proxy(self) -> Optional[str]:
        """ランダムなプロキシを返す"""
        if not PROXY_LIST:
            return None
        return random.choice(PROXY_LIST)
    
    def cleanup(self):
        """リソースを解放する"""
        if self.db:
            self.db.close()
            logger.info("Database connection closed")

def load_products_from_file(filename: str) -> List[str]:
    """ファイルから商品URLリストを読み込む"""
    if not os.path.exists(filename):
        logger.error(f"File not found: {filename}")
        return []
    
    try:
        with open(filename, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return urls
    except Exception as e:
        logger.error(f"Error reading product file: {e}")
        return []

def run_scheduled_update():
    """定期実行用の関数"""
    tracker = ECTracker()
    try:
        logger.info("Starting scheduled update...")
        tracker.update_all_products()
        logger.info("Scheduled update completed")
    except Exception as e:
        logger.error(f"Error in scheduled update: {e}")
    finally:
        tracker.cleanup()

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='EC商品価格・在庫追跡ツール')
    subparsers = parser.add_subparsers(dest='command', help='コマンド')
    
    # add コマンド
    add_parser = subparsers.add_parser('add', help='商品を追加')
    add_parser.add_argument('url', help='商品ページのURL')
    
    # add-bulk コマンド
    add_bulk_parser = subparsers.add_parser('add-bulk', help='複数商品を一括追加')
    add_bulk_parser.add_argument('file', help='商品URLリストのファイルパス')
    
    # update コマンド
    update_parser = subparsers.add_parser('update', help='商品情報を更新')
    update_parser.add_argument('--id', type=int, help='更新する商品のID（指定がなければすべて更新）')
    
    # export コマンド
    subparsers.add_parser('export', help='Google Sheetsにエクスポート')
    
    # schedule コマンド
    schedule_parser = subparsers.add_parser('schedule', help='定期実行を設定')
    schedule_parser.add_argument('--interval', type=int, default=12, help='更新間隔（時間）')
    
    args = parser.parse_args()
    
    tracker = ECTracker()
    
    try:
        if args.command == 'add':
            product_id = tracker.add_product(args.url)
            if product_id:
                print(f"商品を追加しました（ID: {product_id}）")
            else:
                print("商品の追加に失敗しました")
        
        elif args.command == 'add-bulk':
            urls = load_products_from_file(args.file)
            if not urls:
                print("URLが見つからないか、ファイルの読み込みに失敗しました")
                return
            
            print(f"{len(urls)}件の商品を追加します...")
            success_count = 0
            for url in urls:
                product_id = tracker.add_product(url)
                if product_id:
                    success_count += 1
                time.sleep(REQUEST_INTERVAL)
            
            print(f"{success_count}/{len(urls)}件の商品を追加しました")
        
        elif args.command == 'update':
            if args.id:
                success = tracker.update_product(args.id)
                if success:
                    print(f"商品（ID: {args.id}）を更新しました")
                else:
                    print(f"商品（ID: {args.id}）の更新に失敗しました")
            else:
                count = tracker.update_all_products()
                print(f"{count}件の商品を更新しました")
        
        elif args.command == 'export':
            success = tracker.export_to_gsheets()
            if success:
                print("Google Sheetsへのエクスポートが完了しました")
            else:
                print("Google Sheetsへのエクスポートに失敗しました")
        
        elif args.command == 'schedule':
            hours = args.interval
            print(f"{hours}時間ごとに更新を実行します。Ctrl+Cで停止してください。")
            
            # 即時実行
            run_scheduled_update()
            
            # スケジュール設定
            schedule.every(hours).hours.do(run_scheduled_update)
            
            # スケジューラを実行
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n終了します...")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        print(f"エラーが発生しました: {e}")
    finally:
        tracker.cleanup()

if __name__ == "__main__":
    main()