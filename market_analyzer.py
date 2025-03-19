# market_analyzer.py - 競合分析・価格最適化
import pandas as pd
import numpy as np
from database import Database
from scrapers import AmazonScraper, RakutenScraper, YahooScraper

class MarketAnalyzer:
    """競合分析・価格最適化クラス"""
    
    def __init__(self, db):
        self.db = db
    
    def find_similar_products(self, product_id, search_keywords=None, limit=5):
        """類似商品を検索"""
        product = self.db.get_product_by_id(product_id)
        if not product:
            return []
        
        # 検索キーワードが指定されていない場合は商品名を使用
        if not search_keywords:
            # 商品名から特徴的な単語を抽出
            name_parts = product['name'].split()
            # 短い単語と一般的な単語を除去
            filtered_parts = [p for p in name_parts if len(p) > 1]
            search_keywords = ' '.join(filtered_parts[:3])  # 最初の3単語
        
        # プラットフォームに応じたスクレイパーを使って類似商品を検索
        similar_products = []
        
        if product['platform'] == 'amazon':
            similar_products = self._search_amazon(search_keywords, limit)
        elif product['platform'] == 'rakuten':
            similar_products = self._search_rakuten(search_keywords, limit)
        elif product['platform'] == 'yahoo':
            similar_products = self._search_yahoo(search_keywords, limit)
        
        # 元の商品を除外
        similar_products = [p for p in similar_products if p['url'] != product['url']]
        
        return similar_products[:limit]
    
    def _search_amazon(self, keywords, limit=5):
        """Amazon商品検索"""
        scraper = AmazonScraper()
        try:
            results = []
            # 検索結果ページをスクレイピング
            url = f"https://www.amazon.co.jp/s?k={keywords.replace(' ', '+')}"
            html = scraper.get_page(url)
            # 検索結果から商品を抽出する処理
            # ここではAmazonCollectorクラスの検索機能を流用できます
            # ...
            
            # ダミーデータ（実際の実装では削除）
            results = [
                {"name": f"Amazon製品 {i}", "url": f"https://amazon.co.jp/dp/DUMMY{i}", 
                 "price": 5000 + i*500, "platform": "amazon"} 
                for i in range(limit)
            ]
            
            return results
        finally:
            scraper.close()
    
    def _search_rakuten(self, keywords, limit=5):
        """楽天商品検索"""
        # Amazon検索と同様の実装
        return [
            {"name": f"楽天商品 {i}", "url": f"https://item.rakuten.co.jp/shop/DUMMY{i}", 
             "price": 4800 + i*400, "platform": "rakuten"} 
            for i in range(limit)
        ]
    
    def _search_yahoo(self, keywords, limit=5):
        """Yahoo商品検索"""
        # Amazon検索と同様の実装
        return [
            {"name": f"Yahoo商品 {i}", "url": f"https://store.shopping.yahoo.co.jp/shop/DUMMY{i}", 
             "price": 5200 + i*300, "platform": "yahoo"} 
            for i in range(limit)
        ]
    
    def recommend_price(self, product_id):
        """価格最適化・推奨価格を算出"""
        product = self.db.get_product_by_id(product_id)
        if not product:
            return None
            
        # 類似商品の検索
        similar_products = self.find_similar_products(product_id)
        if not similar_products:
            return None
            
        # 現在の価格を取得
        current_price = None
        latest_price = self.db.get_latest_price(product_id)
        if latest_price:
            current_price = latest_price['sale_price'] or latest_price['regular_price']
        
        # 類似商品の価格分析
        prices = [p['price'] for p in similar_products if 'price' in p]
        if not prices:
            return None
            
        # 統計分析
        avg_price = np.mean(prices)
        median_price = np.median(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # 推奨価格の計算（様々な戦略に基づく複数の提案）
        recommendations = {
            'current_price': current_price,
            'market_data': {
                'average': avg_price,
                'median': median_price,
                'min': min_price,
                'max': max_price,
                'similar_products': similar_products
            },
            'strategies': {
                'competitive': min_price * 0.95,  # 最安値より5%安く
                'average': avg_price * 0.98,      # 平均より少し安く
                'premium': avg_price * 1.1,       # 平均より10%高く（プレミアム戦略）
                'optimal_margin': avg_price * 0.9  # 最適利益率を想定
            }
        }
        
        return recommendations