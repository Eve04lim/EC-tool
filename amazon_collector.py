# amazon_collector.py ヘッドレスモード有効化版
import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import json
import argparse

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AmazonCollector:
    """Amazonから商品URLを収集するクラス"""
    
    def __init__(self, max_items=10):
        """初期化"""
        self.max_items = max_items
        self.driver = None
        self.setup_selenium()
    
    def setup_selenium(self):
        """Seleniumの設定"""
        try:
            chrome_options = Options()
            # ヘッドレスモードを有効化
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # ボット検出回避のための追加設定
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Heroku環境かどうかを判定
            import os
            if os.environ.get("DYNO"):  # Herokuで実行している場合
                chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_SHIM", None)
                service = Service()
            else:
                # ローカル環境の場合は指定されたパスのChromeドライバーを使用
                service = Service("C:\\chromedriver\\chromedriver.exe")
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # WebDriverフラグを偽装
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.set_page_load_timeout(30)
            # 一般的なウィンドウサイズに設定
            self.driver.set_window_size(1366, 768)
            
            logger.info("Selenium WebDriver initialized in headless mode")
        except Exception as e:
            logger.error(f"Failed to setup Selenium: {e}")
            raise
    
    def collect_from_category(self, category_url):
        """カテゴリページから商品URLを収集"""
        products = []
        try:
            logger.info(f"Collecting products from category: {category_url}")
            self.driver.get(category_url)
            
            # 人間らしいスクロール
            for scroll in range(1, 10):
                self.driver.execute_script(f"window.scrollTo(0, {scroll * 500})")
                time.sleep(random.uniform(0.5, 1.5))
            
            # 商品カードを探す
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, 
                "div[data-component-type='s-search-result']")
            
            for card in product_cards[:self.max_items]:
                try:
                    # 商品リンクを探す
                    link_element = card.find_element(By.CSS_SELECTOR, "a.a-link-normal.s-no-outline")
                    link = link_element.get_attribute("href")
                    
                    # ASIN抽出
                    if "/dp/" in link:
                        asin = link.split("/dp/")[1].split("/")[0]
                        product_url = f"https://www.amazon.co.jp/dp/{asin}"
                        products.append(product_url)
                        logger.info(f"Found product: {product_url}")
                except Exception as e:
                    logger.warning(f"Error extracting product link: {e}")
                    continue
            
            logger.info(f"Collected {len(products)} products")
            return products
        except Exception as e:
            logger.error(f"Error collecting from category: {e}")
            return products
        
    def collect_from_search(self, search_term):
        """検索結果から商品URLを収集"""
        search_url = f"https://www.amazon.co.jp/s?k={search_term.replace(' ', '+')}"
        return self.collect_from_category(search_url)
    
    def collect_from_bestsellers(self, category=None):
        """ベストセラーから商品URLを収集"""
        if category:
            url = f"https://www.amazon.co.jp/gp/bestsellers/{category}"
        else:
            url = "https://www.amazon.co.jp/gp/bestsellers/"
        
        products = []
        try:
            logger.info(f"Collecting bestsellers from: {url}")
            self.driver.get(url)
            
            # 人間らしいスクロール
            for scroll in range(1, 10):
                self.driver.execute_script(f"window.scrollTo(0, {scroll * 500})")
                time.sleep(random.uniform(0.5, 1.5))
            
            # 商品カードを探す
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.p13n-sc-uncoverable-faceout")
            
            for element in product_elements[:self.max_items]:
                try:
                    # 商品リンクを探す
                    link_element = element.find_element(By.CSS_SELECTOR, "a")
                    link = link_element.get_attribute("href")
                    
                    # ASIN抽出
                    if "/dp/" in link:
                        asin = link.split("/dp/")[1].split("/")[0]
                        product_url = f"https://www.amazon.co.jp/dp/{asin}"
                        products.append(product_url)
                        logger.info(f"Found bestseller: {product_url}")
                except Exception as e:
                    logger.warning(f"Error extracting bestseller link: {e}")
                    continue
            
            logger.info(f"Collected {len(products)} bestsellers")
            return products
        except Exception as e:
            logger.error(f"Error collecting bestsellers: {e}")
            return products
    
    def add_products_to_tracker(self, products):
        """収集した商品を追跡ツールに追加"""
        success_count = 0
        
        for url in products:
            try:
                logger.info(f"Adding product to tracker: {url}")
                
                # main.pyを呼び出して商品を追加
                result = subprocess.run(
                    ["python", "main.py", "add", url],
                    capture_output=True,
                    text=True
                )
                
                # 結果をチェック
                if "商品を追加しました" in result.stdout:
                    success_count += 1
                    logger.info(f"Successfully added: {url}")
                else:
                    logger.warning(f"Failed to add: {url}")
                    logger.warning(result.stderr)
                
                # 連続リクエストを避けるための待機
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"Error adding product {url}: {e}")
        
        return success_count
    
    def close(self):
        """リソースを解放"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

def main():
    parser = argparse.ArgumentParser(description='Amazon商品自動収集ツール')
    parser.add_argument('--mode', choices=['category', 'search', 'bestsellers'], 
                        default='bestsellers', help='収集モード')
    parser.add_argument('--term', help='検索キーワードまたはカテゴリURL')
    parser.add_argument('--category', help='ベストセラーカテゴリ(例: electronics)')
    parser.add_argument('--max', type=int, default=10, help='最大収集数')
    
    args = parser.parse_args()
    
    collector = AmazonCollector(max_items=args.max)
    
    try:
        products = []
        
        if args.mode == 'category':
            if not args.term:
                logger.error("カテゴリURLが指定されていません")
                return
            products = collector.collect_from_category(args.term)
            
        elif args.mode == 'search':
            if not args.term:
                logger.error("検索キーワードが指定されていません")
                return
            products = collector.collect_from_search(args.term)
            
        elif args.mode == 'bestsellers':
            products = collector.collect_from_bestsellers(args.category)
        
        if products:
            print(f"{len(products)}件の商品URLを収集しました")
            
            # 収集した商品リストを表示
            for i, url in enumerate(products):
                print(f"{i+1}. {url}")
            
            # 確認
            confirm = input("これらの商品を追跡リストに追加しますか？ (y/n): ")
            if confirm.lower() == 'y':
                success_count = collector.add_products_to_tracker(products)
                print(f"{success_count}/{len(products)}件の商品を追加しました")
            else:
                print("追加をキャンセルしました")
        else:
            print("商品を収集できませんでした")
    
    finally:
        collector.close()

if __name__ == "__main__":
    main()