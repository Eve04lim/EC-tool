# scrapers.py - ECサイトスクレイピングモジュール
import logging
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from config import USER_AGENT, REQUEST_TIMEOUT, REQUEST_RETRY, REQUEST_INTERVAL, SELENIUM_TIMEOUT, SELENIUM_WAIT

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """スクレイパーの基底クラス"""
    
    def __init__(self, use_selenium=False, proxy=None):
        self.use_selenium = use_selenium
        self.proxy = proxy
        self.driver = None
        self.session = requests.Session()
        self.headers = {"User-Agent": USER_AGENT}
        
        if use_selenium:
            self._setup_selenium()
    
    def _setup_selenium(self):
        """Seleniumの設定"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            if self.proxy:
                chrome_options.add_argument(f"--proxy-server={self.proxy}")

            # ✅ Heroku環境なら /usr/bin を使う
            if os.environ.get("DYNO"):
                chrome_options.binary_location = "/usr/bin/chromium-browser"
                driver_path = "/usr/bin/chromedriver"
            else:
                # ローカル用
                driver_path = "C:\\chromedriver\\chromedriver.exe"

            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(SELENIUM_TIMEOUT)
            self.driver.set_window_size(1366, 768)

            logger.info("Selenium WebDriver initialized in headless mode")
        except Exception as e:
            logger.error(f"Failed to setup Selenium: {e}")
            raise

    
    
    def _get_page_with_requests(self, url):
        """RequestsでWebページを取得"""
        for attempt in range(REQUEST_RETRY):
            try:
                response = self.session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT, proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt+1}/{REQUEST_RETRY} failed: {e}")
                if attempt < REQUEST_RETRY - 1:
                    sleep_time = REQUEST_INTERVAL * (attempt + 1)
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to get page after {REQUEST_RETRY} attempts: {url}")
                    raise
    
    def _get_page_with_selenium(self, url):
        """SeleniumでWebページを取得"""
        if not self.driver:
            self._setup_selenium()
        
        try:
            self.driver.get(url)
            
            # 人間らしいスクロール挙動を再現
            for scroll in [300, 600, 900, 1200]:
                self.driver.execute_script(f"window.scrollTo(0, {scroll})")
                time.sleep(random.uniform(0.5, 1.5))
            
            # ランダムな待機時間を設定（より長め）
            time.sleep(SELENIUM_WAIT + random.uniform(3, 7))
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Failed to get page with Selenium: {e}")
            raise
    
    def get_page(self, url):
        """Webページを取得する"""
        logger.info(f"Fetching page: {url}")
        if self.use_selenium:
            return self._get_page_with_selenium(url)
        else:
            return self._get_page_with_requests(url)
    
    def wait_for_element(self, selector, by=By.CSS_SELECTOR, timeout=SELENIUM_TIMEOUT):
        """要素が表示されるまで待機（Seleniumのみ）"""
        if not self.use_selenium:
            logger.warning("wait_for_element called but not using Selenium")
            return None
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            return None
    
    def close(self):
        """リソースを解放する"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Selenium WebDriver closed")
    
    @abstractmethod
    def scrape_product(self, url):
        """商品情報をスクレイピングする（サブクラスで実装）"""
        pass


class AmazonScraper(BaseScraper):
    """Amazon.co.jpスクレイパー"""
    
    def __init__(self, proxy=None):
        super().__init__(use_selenium=True, proxy=proxy)
    
    def scrape_product(self, url):
        """Amazon商品ページから情報を取得"""
        logger.info(f"Scraping Amazon product: {url}")
        html = self.get_page(url)
        
        # 追加：ページが完全に読み込まれるのを待つ
        if self.use_selenium and self.driver:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "productTitle"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for product title to load")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 商品名
        try:
            name = soup.select_one("#productTitle").text.strip()
        except (AttributeError, TypeError):
            logger.warning("Could not find product name")
            name = None
        
        # 商品画像
        try:
            image_url = soup.select_one("#landingImage")['src']
        except (AttributeError, TypeError, KeyError):
            try:
                image_url = soup.select_one("#imgBlkFront")['src']
            except (AttributeError, TypeError, KeyError):
                # 別の画像セレクタも試す
                try:
                    image_url = soup.select_one("#main-image")['src']
                except (AttributeError, TypeError, KeyError):
                    logger.warning("Could not find product image")
                    image_url = None
        
        # ASIN
        try:
            asin = None
            for element in soup.select("div.content ul li"):
                text = element.text.strip()
                if "ASIN" in text:
                    asin = text.split(':')[-1].strip()
                    break
            
            if not asin:
                # URLからASINを抽出
                asin = url.split('/dp/')[-1].split('/')[0] if '/dp/' in url else None
        except Exception:
            logger.warning("Could not find ASIN")
            asin = None
        
        # 通常価格
        regular_price = None
        try:
            price_element = soup.select_one("span.a-text-price span.a-offscreen")
            if price_element:
                regular_price = float(price_element.text.replace("￥", "").replace(",", "").strip())
        except (AttributeError, ValueError):
            logger.warning("Could not find regular price")
        
        # セール価格
        sale_price = None
        try:
            price_element = soup.select_one("span.a-price span.a-offscreen")
            if price_element:
                sale_price = float(price_element.text.replace("￥", "").replace(",", "").strip())
            # 通常価格がなく、セール価格のみある場合
            if not regular_price and sale_price:
                regular_price = sale_price
        except (AttributeError, ValueError):
            # 別の価格セレクタも試す
            try:
                price_element = soup.select_one("#priceblock_ourprice")
                if price_element:
                    sale_price = float(price_element.text.replace("￥", "").replace(",", "").strip())
                    if not regular_price:
                        regular_price = sale_price
            except (AttributeError, ValueError):
                logger.warning("Could not find sale price")
        
        # 在庫状況
        in_stock = False
        try:
            availability = soup.select_one("#availability span")
            if availability:
                availability_text = availability.text.strip().lower()
                in_stock = "在庫あり" in availability_text or "在庫" not in availability_text
            
            # 別の在庫表示も確認
            if not in_stock:
                add_to_cart = soup.select_one("#add-to-cart-button")
                if add_to_cart:
                    in_stock = True
        except (AttributeError, TypeError):
            logger.warning("Could not determine stock status")
        
        # レビュー数と評価
        review_count = None
        review_rating = None
        try:
            reviews_element = soup.select_one("#acrCustomerReviewText")
            if reviews_element:
                review_count = int(reviews_element.text.split()[0].replace(",", ""))
            
            rating_element = soup.select_one("span.a-icon-alt")
            if rating_element:
                rating_text = rating_element.text
                if "5つ星のうち" in rating_text:
                    review_rating = float(rating_text.replace("5つ星のうち", "").strip())
        except (AttributeError, ValueError, IndexError):
            logger.warning("Could not find review information")
        
        # デバッグ用：商品名が取得できていない場合、ページソースを確認
        if name is None:
            logger.debug("Page source snippet for debugging:")
            page_source_snippet = html[:500] + "..." if len(html) > 500 else html
            logger.debug(page_source_snippet)
        
        return {
            "name": name,
            "image_url": image_url,
            "product_code": asin,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "in_stock": in_stock,
            "review_count": review_count,
            "review_rating": review_rating,
            "platform": "amazon"
        }


class RakutenScraper(BaseScraper):
    """楽天市場スクレイパー"""
    
    def __init__(self, proxy=None):
        super().__init__(use_selenium=True, proxy=proxy)
    
    def scrape_product(self, url):
        """楽天商品ページから情報を取得"""
        logger.info(f"Scraping Rakuten product: {url}")
        html = self.get_page(url)
        
        # 楽天のページが完全に読み込まれるのを待つ
        if self.use_selenium and self.driver:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "item_name"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for item name to load")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 商品名
        try:
            name = soup.select_one("span.item_name").text.strip()
        except (AttributeError, TypeError):
            try:
                name = soup.select_one("h1.item_name").text.strip()
            except (AttributeError, TypeError):
                logger.warning("Could not find product name")
                name = None
        
        # 商品画像
        try:
            image_url = soup.select_one("div#image_main img")['src']
        except (AttributeError, TypeError, KeyError):
            logger.warning("Could not find product image")
            image_url = None
        
        # 商品コード (JAN)
        jan = None
        try:
            details = soup.select("div.rcSectionTable tr")
            for row in details:
                header = row.select_one("th")
                if header and ("JAN" in header.text or "JANコード" in header.text):
                    jan = row.select_one("td").text.strip()
                    break
        except Exception:
            logger.warning("Could not find JAN code")
        
        # 価格
        regular_price = None
        sale_price = None
        try:
            # セール価格
            price_element = soup.select_one("span.price2")
            if price_element:
                sale_price = float(price_element.text.replace("円", "").replace(",", "").strip())
            
            # 通常価格（税抜表示の場合があるため注意）
            regular_price_element = soup.select_one("span.price1")
            if regular_price_element:
                regular_price_text = regular_price_element.text.strip()
                if "税抜" in regular_price_text:
                    regular_price = float(regular_price_text.replace("税抜", "").replace("円", "").replace(",", "").strip())
                    # 税抜表示の場合、おおよその税込価格に変換（10%）
                    regular_price = round(regular_price * 1.1)
                else:
                    regular_price = float(regular_price_text.replace("円", "").replace(",", "").strip())
            
            # 通常価格がなく、セール価格のみある場合
            if not regular_price and sale_price:
                regular_price = sale_price
        except (AttributeError, ValueError):
            logger.warning("Could not find price information")
        
        # 在庫状況
        in_stock = False
        try:
            availability = soup.select_one("div.purchaseButtonArea")
            if availability:
                sold_out = soup.select_one("div.soldout_notice")
                in_stock = sold_out is None
        except (AttributeError, TypeError):
            logger.warning("Could not determine stock status")
        
        # レビュー数と評価
        review_count = None
        review_rating = None
        try:
            reviews_element = soup.select_one("span.revEvaNumber")
            if reviews_element:
                review_count = int(reviews_element.text.strip())
            
            rating_element = soup.select_one("span.revEvaValue")
            if rating_element:
                review_rating = float(rating_element.text.strip())
        except (AttributeError, ValueError):
            logger.warning("Could not find review information")
        
        return {
            "name": name,
            "image_url": image_url,
            "product_code": jan,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "in_stock": in_stock,
            "review_count": review_count,
            "review_rating": review_rating,
            "platform": "rakuten"
        }


class YahooScraper(BaseScraper):
    """Yahooショッピングスクレイパー"""
    
    def __init__(self, proxy=None):
        super().__init__(use_selenium=True, proxy=proxy)
    
    def scrape_product(self, url):
        """Yahoo商品ページから情報を取得"""
        logger.info(f"Scraping Yahoo Shopping product: {url}")
        html = self.get_page(url)
        
        # Yahooのページが完全に読み込まれるのを待つ
        if self.use_selenium and self.driver:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "elTitle"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for title to load")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 商品名
        try:
            name = soup.select_one("h1.elTitle").text.strip()
        except (AttributeError, TypeError):
            logger.warning("Could not find product name")
            name = None
        
        # 商品画像
        try:
            image_url = soup.select_one("div.elMain img")['src']
        except (AttributeError, TypeError, KeyError):
            logger.warning("Could not find product image")
            image_url = None
        
        # 商品コード (JANまたは商品ID)
        product_code = None
        try:
            # URLから商品IDを抽出
            if '/store/' in url:
                product_code = url.split('/store/')[1].split('/')[1]
            elif '/shopping/' in url:
                product_code = url.split('/shopping/')[1].split('/')[0]
        except Exception:
            logger.warning("Could not find product code")
        
        # 価格情報
        regular_price = None
        sale_price = None
        try:
            # セール価格
            price_element = soup.select_one("span.elPriceValue")
            if price_element:
                sale_price = float(price_element.text.replace("円", "").replace(",", "").strip())
            
            # 通常価格（取り消し線の価格）
            regular_price_element = soup.select_one("span.elPriceL")
            if regular_price_element:
                regular_price = float(regular_price_element.text.replace("円", "").replace(",", "").strip())
            
            # 通常価格がなく、セール価格のみある場合
            if not regular_price and sale_price:
                regular_price = sale_price
        except (AttributeError, ValueError):
            logger.warning("Could not find price information")
        
        # 在庫状況
        in_stock = False
        try:
            sold_out_element = soup.select_one("div.elSoldout")
            if sold_out_element:
                in_stock = False
            else:
                cart_button = soup.select_one("button.elCartButton")
                in_stock = cart_button is not None
        except (AttributeError, TypeError):
            logger.warning("Could not determine stock status")
        
        # レビュー数と評価
        review_count = None
        review_rating = None
        try:
            reviews_element = soup.select_one("span.elReviewNumber")
            if reviews_element:
                review_count = int(reviews_element.text.strip())
            
            rating_element = soup.select_one("span.elTotalNominator")
            if rating_element:
                review_rating = float(rating_element.text.strip())
        except (AttributeError, ValueError):
            logger.warning("Could not find review information")
        
        return {
            "name": name,
            "image_url": image_url,
            "product_code": product_code,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "in_stock": in_stock,
            "review_count": review_count,
            "review_rating": review_rating,
            "platform": "yahoo"
        }


def get_scraper_for_url(url, proxy=None):
    """URLに対応するスクレイパーを返す"""
    if "amazon.co.jp" in url or "amzn.to" in url:
        return AmazonScraper(proxy=proxy)
    elif "rakuten.co.jp" in url or "r10.to" in url:
        return RakutenScraper(proxy=proxy)
    elif "shopping.yahoo.co.jp" in url:
        return YahooScraper(proxy=proxy)
    else:
        raise ValueError(f"Unsupported URL: {url}")