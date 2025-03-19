# market_insight.py - マーケットインサイト機能（続き）
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
import seaborn as sns
from datetime import datetime, timedelta
import os
import json
from wordcloud import WordCloud
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

class MarketInsight:
   """マーケットインサイト機能"""
   
   def __init__(self, db):
       self.db = db
       self.output_dir = os.path.join('static', 'reports')
       os.makedirs(self.output_dir, exist_ok=True)
   
   def generate_platform_comparison(self):
       """プラットフォーム比較分析"""
       products = self.db.get_all_products()
       if not products:
           return False, "分析に必要な商品データがありません"
       
       # プラットフォームごとのデータを収集
       platform_data = {
           "amazon": {"products": [], "prices": [], "stock_rate": 0, "review_counts": []},
           "rakuten": {"products": [], "prices": [], "stock_rate": 0, "review_counts": []},
           "yahoo": {"products": [], "prices": [], "stock_rate": 0, "review_counts": []}
       }
       
       for product in products:
           platform = product['platform']
           if platform not in platform_data:
               continue
               
           price_info = self.db.get_latest_price(product['id'])
           if price_info:
               price = price_info['sale_price'] or price_info['regular_price']
               platform_data[platform]["products"].append(product)
               platform_data[platform]["prices"].append(price)
               
               if price_info['in_stock']:
                   platform_data[platform]["stock_rate"] += 1
                   
               if price_info['review_count']:
                   platform_data[platform]["review_counts"].append(price_info['review_count'])
       
       # プラットフォームごとの統計計算
       result = {}
       for platform, data in platform_data.items():
           if not data["products"]:
               continue
               
           count = len(data["products"])
           result[platform] = {
               "product_count": count,
               "avg_price": np.mean(data["prices"]) if data["prices"] else 0,
               "median_price": np.median(data["prices"]) if data["prices"] else 0,
               "min_price": min(data["prices"]) if data["prices"] else 0,
               "max_price": max(data["prices"]) if data["prices"] else 0,
               "stock_rate": (data["stock_rate"] / count * 100) if count > 0 else 0,
               "avg_reviews": np.mean(data["review_counts"]) if data["review_counts"] else 0
           }
       
       # 可視化
       chart_file = self._visualize_platform_comparison(result)
       
       return True, {
           "platforms": result,
           "chart_file": chart_file
       }
   
   def _visualize_platform_comparison(self, data):
       """プラットフォーム比較の可視化"""
       plt.figure(figsize=(15, 10))
       
       # プラットフォーム名の日本語表記
       platform_names = {
           "amazon": "Amazon",
           "rakuten": "楽天市場",
           "yahoo": "Yahoo!ショッピング"
       }
       
       # 色の設定
       colors = {
           "amazon": "#FF9900",
           "rakuten": "#BF0000",
           "yahoo": "#FF0033"
       }
       
       # サブプロット1: 平均価格比較
       plt.subplot(2, 2, 1)
       platforms = list(data.keys())
       avg_prices = [data[p]["avg_price"] for p in platforms]
       bars = plt.bar(
           [platform_names.get(p, p) for p in platforms],
           avg_prices,
           color=[colors.get(p, "blue") for p in platforms]
       )
       
       # 価格ラベルを追加
       for bar in bars:
           height = bar.get_height()
           plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'¥{int(height):,}', ha='center', va='bottom')
       
       plt.title("プラットフォーム別 平均価格", fontsize=12)
       plt.ylabel("価格 (円)")
       plt.grid(axis='y', alpha=0.3)
       
       # サブプロット2: 在庫率比較
       plt.subplot(2, 2, 2)
       stock_rates = [data[p]["stock_rate"] for p in platforms]
       bars = plt.bar(
           [platform_names.get(p, p) for p in platforms],
           stock_rates,
           color=[colors.get(p, "blue") for p in platforms]
       )
       
       # パーセントラベルを追加
       for bar in bars:
           height = bar.get_height()
           plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{height:.1f}%', ha='center', va='bottom')
       
       plt.title("プラットフォーム別 在庫率", fontsize=12)
       plt.ylabel("在庫率 (%)")
       plt.ylim(0, 110)  # スケールを0-100%+マージンに
       plt.grid(axis='y', alpha=0.3)
       
       # サブプロット3: 価格帯分布
       plt.subplot(2, 2, 3)
       price_ranges = {
           platform: {
               "min": data[platform]["min_price"],
               "q1": data[platform]["min_price"] + (data[platform]["median_price"] - data[platform]["min_price"])/2,
               "median": data[platform]["median_price"],
               "q3": data[platform]["median_price"] + (data[platform]["max_price"] - data[platform]["median_price"])/2,
               "max": data[platform]["max_price"]
           } for platform in platforms
       }
       
       # 箱ひげ図データの準備
       box_data = []
       box_labels = []
       box_colors = []
       
       for p in platforms:
           pr = price_ranges[p]
           box_data.append([pr["min"], pr["q1"], pr["median"], pr["q3"], pr["max"]])
           box_labels.append(platform_names.get(p, p))
           box_colors.append(colors.get(p, "blue"))
       
       # 箱ひげ図を描画
       plt.boxplot(box_data, labels=box_labels, patch_artist=True,
                 boxprops=dict(facecolor="lightgray"))
       
       plt.title("プラットフォーム別 価格帯分布", fontsize=12)
       plt.ylabel("価格 (円)")
       plt.grid(axis='y', alpha=0.3)
       
       # サブプロット4: 商品数・レビュー数比較
       plt.subplot(2, 2, 4)
       
       width = 0.35
       x = np.arange(len(platforms))
       
       product_counts = [data[p]["product_count"] for p in platforms]
       review_avgs = [data[p]["avg_reviews"] for p in platforms]
       
       ax1 = plt.bar(x - width/2, product_counts, width, label='商品数', color='lightblue')
       ax2 = plt.twinx()
       ax2.bar(x + width/2, review_avgs, width, label='平均レビュー数', color='lightgreen')
       
       plt.xticks(x, [platform_names.get(p, p) for p in platforms])
       plt.title("商品数・レビュー数比較", fontsize=12)
       plt.legend(handles=[ax1, ax2], loc='upper left')
       
       plt.tight_layout()
       
       # 保存
       filename = "platform_comparison.png"
       filepath = os.path.join(self.output_dir, filename)
       plt.savefig(filepath, dpi=100, bbox_inches='tight')
       plt.close()
       
       return filename
   
   def generate_price_trend_overview(self, days=30):
       """全商品の価格トレンド概要"""
       products = self.db.get_all_products()
       if not products:
           return False, "分析に必要な商品データがありません"
       
       # 期間の設定
       end_date = datetime.now()
       start_date = end_date - timedelta(days=days)
       
       # 商品ごとの価格トレンドを収集
       trends = []
       for product in products:
           history = self.db.get_product_price_history(product['id'], limit=90)
           if len(history) < 3:
               continue
           
           # データフレームに変換
           df = pd.DataFrame(history)
           df['fetched_at'] = pd.to_datetime(df['fetched_at'])
           df = df.sort_values('fetched_at')
           
           # 指定期間内のデータにフィルタリング
           df = df[df['fetched_at'] >= start_date]
           if len(df) < 2:
               continue
           
           # 価格の計算
           df['price'] = df['sale_price'].fillna(df['regular_price'])
           
           # 最初と最後の価格
           first_price = df['price'].iloc[0]
           last_price = df['price'].iloc[-1]
           
           # 価格変動の計算
           price_change = last_price - first_price
           price_change_pct = (price_change / first_price) * 100 if first_price else 0
           
           # 傾向（線形回帰の傾き）
           X = np.array(range(len(df))).reshape(-1, 1)
           y = df['price'].values
           slope, intercept, r_value, p_value, std_err = stats.linregress(X.flatten(), y)
           
           # 価格変動の分類
           if abs(price_change_pct) < 1:
               trend_type = "stable"  # 安定
           elif price_change_pct >= 1:
               trend_type = "rising"  # 上昇
           else:
               trend_type = "falling"  # 下落
           
           trends.append({
               "product_id": product['id'],
               "product_name": product['name'],
               "platform": product['platform'],
               "first_price": float(first_price),
               "last_price": float(last_price),
               "price_change": float(price_change),
               "price_change_pct": float(price_change_pct),
               "slope": float(slope),
               "trend_type": trend_type
           })
       
       # トレンドの集計
       trend_counts = {
           "rising": len([t for t in trends if t["trend_type"] == "rising"]),
           "falling": len([t for t in trends if t["trend_type"] == "falling"]),
           "stable": len([t for t in trends if t["trend_type"] == "stable"])
       }
       
       # 価格上昇率/下落率の大きい商品を抽出
       rising_products = sorted([t for t in trends if t["trend_type"] == "rising"], 
                              key=lambda x: x["price_change_pct"], reverse=True)[:5]
       
       falling_products = sorted([t for t in trends if t["trend_type"] == "falling"], 
                               key=lambda x: x["price_change_pct"])[:5]
       
       # 可視化
       chart_file = self._visualize_price_trends(trends, trend_counts, days)
       
       return True, {
           "trends": trends,
           "trend_counts": trend_counts,
           "top_rising": rising_products,
           "top_falling": falling_products,
           "chart_file": chart_file
       }
   
   def _visualize_price_trends(self, trends, trend_counts, days):
       """価格トレンドの可視化"""
       plt.figure(figsize=(15, 10))
       
       # サブプロット1: トレンド分布
       plt.subplot(2, 2, 1)
       labels = ['価格上昇', '価格安定', '価格下落']
       sizes = [trend_counts['rising'], trend_counts['stable'], trend_counts['falling']]
       colors = ['#ff7675', '#74b9ff', '#55efc4']
       
       # 円グラフを描画
       plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
       plt.axis('equal')
       plt.title(f'過去{days}日間の価格トレンド分布', fontsize=12)
       
       # サブプロット2: プラットフォーム別トレンド
       plt.subplot(2, 2, 2)
       
       # プラットフォームごとにトレンドをカウント
       platforms = ['amazon', 'rakuten', 'yahoo']
       platform_names = {'amazon': 'Amazon', 'rakuten': '楽天', 'yahoo': 'Yahoo!'}
       
       platform_trends = {}
       for p in platforms:
           p_trends = [t for t in trends if t["platform"] == p]
           platform_trends[p] = {
               "rising": len([t for t in p_trends if t["trend_type"] == "rising"]),
               "falling": len([t for t in p_trends if t["trend_type"] == "falling"]),
               "stable": len([t for t in p_trends if t["trend_type"] == "stable"])
           }
       
       # 積み上げ棒グラフのデータ準備
       rising_data = [platform_trends[p]["rising"] for p in platforms]
       stable_data = [platform_trends[p]["stable"] for p in platforms]
       falling_data = [platform_trends[p]["falling"] for p in platforms]
       
       x = np.arange(len(platforms))
       width = 0.6
       
       # 積み上げ棒グラフを描画
       plt.bar(x, rising_data, width, label='価格上昇', color='#ff7675')
       plt.bar(x, stable_data, width, bottom=rising_data, label='価格安定', color='#74b9ff')
       
       bottom_data = [sum(x) for x in zip(rising_data, stable_data)]
       plt.bar(x, falling_data, width, bottom=bottom_data, label='価格下落', color='#55efc4')
       
       plt.xticks(x, [platform_names.get(p, p) for p in platforms])
       plt.ylabel('商品数')
       plt.title('プラットフォーム別価格トレンド', fontsize=12)
       plt.legend()
       
       # サブプロット3: 価格変動率の分布
       plt.subplot(2, 2, 3)
       
       # 価格変動率のデータ
       change_pcts = [t["price_change_pct"] for t in trends]
       
       # ヒストグラムを描画
       plt.hist(change_pcts, bins=20, color='#74b9ff', alpha=0.7)
       plt.axvline(x=0, color='red', linestyle='--')
       
       plt.xlabel('価格変動率 (%)')
       plt.ylabel('商品数')
       plt.title('価格変動率の分布', fontsize=12)
       plt.grid(axis='y', alpha=0.3)
       
       # サブプロット4: 主要トレンド商品
       plt.subplot(2, 2, 4)
       
       # 価格変動率でソート
       sorted_trends = sorted(trends, key=lambda x: abs(x["price_change_pct"]), reverse=True)[:10]
       
       # バブルチャートのデータ準備
       x_data = [t["price_change_pct"] for t in sorted_trends]
       y_data = [t["last_price"] for t in sorted_trends]
       s_data = [abs(t["price_change_pct"]) * 5 for t in sorted_trends]  # バブルのサイズ
       c_data = ['#ff7675' if t["price_change_pct"] > 0 else '#55efc4' for t in sorted_trends]  # 色
       
       # バブルチャートを描画
       scatter = plt.scatter(x_data, y_data, s=s_data, c=c_data, alpha=0.6)
       
       plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
       plt.xlabel('価格変動率 (%)')
       plt.ylabel('現在価格 (円)')
       plt.title('価格変動の大きい商品', fontsize=12)
       plt.grid(alpha=0.3)
       
       # 全体レイアウトの調整
       plt.tight_layout()
       
       # 保存
       filename = f"price_trends_{days}days.png"
       filepath = os.path.join(self.output_dir, filename)
       plt.savefig(filepath, dpi=100, bbox_inches='tight')
       plt.close()
       
       return filename