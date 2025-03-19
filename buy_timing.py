# buy_timing.py - 買い時判定アルゴリズム
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

class BuyTimingAdvisor:
    """買い時判定アルゴリズム"""
    
    def __init__(self, db):
        self.db = db
        self.output_dir = os.path.join('static', 'reports')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def analyze_product(self, product_id):
        """商品の買い時分析"""
        product = self.db.get_product_by_id(product_id)
        history = self.db.get_product_price_history(product_id, limit=90)
        
        if not product or len(history) < 10:
            return {
                "success": False,
                "message": "十分なデータがありません（10件以上の価格履歴が必要です）"
            }
        
        # データフレームに変換
        df = pd.DataFrame(history)
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        df = df.sort_values('fetched_at')
        
        # 価格データ準備
        df['price'] = df['sale_price'].fillna(df['regular_price'])
        
        # 最新の価格を取得
        current_price = df['price'].iloc[-1]
        
        # 価格統計
        price_stats = {
            "current": float(current_price),
            "min": float(df['price'].min()),
            "max": float(df['price'].max()),
            "mean": float(df['price'].mean()),
            "median": float(df['price'].median()),
            "std": float(df['price'].std())
        }
        
        # 価格の変動性分析
        price_volatility = price_stats["std"] / price_stats["mean"]
        
        # 過去最低価格との比較
        minimum_price = price_stats["min"]
        price_vs_minimum = (current_price - minimum_price) / minimum_price * 100
        
        # 履歴の中で現在の価格のパーセンタイル（低いほど良い）
        price_percentile = stats.percentileofscore(df['price'], current_price)
        
        # 過去30日間の傾向分析（最近の傾向）
        recent_df = df.iloc[-min(30, len(df)):]
        if len(recent_df) >= 5:
            X = np.array(range(len(recent_df))).reshape(-1, 1)
            y = recent_df['price'].values
            slope, intercept, r_value, p_value, std_err = stats.linregress(X.flatten(), y)
            
            # 傾きが負（価格が下がっている）かどうか
            downward_trend = slope < 0
            trend_strength = abs(r_value)  # 相関係数の絶対値
        else:
            downward_trend = False
            trend_strength = 0
        
        # 季節性分析（データが十分にある場合）
        seasonality = {}
        if len(df) >= 30:
            # 曜日別平均価格
            df['dayofweek'] = df['fetched_at'].dt.dayofweek
            day_avg = df.groupby('dayofweek')['price'].mean()
            
            # 最も価格が安い曜日
            cheapest_day = day_avg.idxmin()
            day_names = ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日']
            
            seasonality = {
                "cheapest_day": day_names[cheapest_day],
                "day_prices": {day_names[i]: float(price) for i, price in day_avg.items()}
            }
        
        # 買い時スコア計算（0-100、高いほど今が買い時）
        buy_score = 0
        
        # 1. 現在価格が過去最低に近いほど高スコア（最大30点）
        min_price_factor = min(30, max(0, 30 - price_vs_minimum))
        
        # 2. 価格パーセンタイルが低いほど高スコア（最大25点）
        percentile_factor = (100 - price_percentile) / 4
        
        # 3. 下降トレンドなら加点（最大20点）
        trend_factor = 20 * trend_strength if downward_trend else 0
        
        # 4. 価格の変動性が高いほど加点（最大15点）
        volatility_factor = min(15, 15 * price_volatility * 2)
        
        # 5. 季節性の最安値に近いほど加点（最大10点）
        season_factor = 0
        if seasonality:
            today = datetime.now().weekday()
            day_name = day_names[today]
            cheapest_price = min(seasonality["day_prices"].values())
            today_avg_price = seasonality["day_prices"][day_name]
            
            if day_name == seasonality["cheapest_day"]:
                season_factor = 10
            else:
                # 最安値日との差が少ないほど高スコア
                price_diff_pct = (today_avg_price - cheapest_price) / cheapest_price
                season_factor = max(0, 10 - 20 * price_diff_pct)
        
        # 合計スコア
        buy_score = min(100, min_price_factor + percentile_factor + trend_factor + volatility_factor + season_factor)
        
        # 買い時判定（スコアに基づく）
        if buy_score >= 80:
            recommendation = "絶好の買い時です！現在の価格は非常に有利です。"
            recommendation_level = "excellent"
        elif buy_score >= 60:
            recommendation = "良い買い時です。現在の価格はお得です。"
            recommendation_level = "good"
        elif buy_score >= 40:
            recommendation = "普通の価格です。特に急いで購入する必要はありません。"
            recommendation_level = "neutral"
        else:
            recommendation = "現在は買い時ではありません。価格が下がるのを待つことをお勧めします。"
            recommendation_level = "wait"
        
        # 可視化
        chart_file = self._visualize_buy_timing(product, df, buy_score, recommendation_level)
        
        # 結果を返す
        return {
            "success": True,
            "product_name": product["name"],
            "price_stats": price_stats,
            "current_vs_min": {
                "difference": float(current_price - minimum_price),
                "percentage": float(price_vs_minimum)
            },
            "price_percentile": float(price_percentile),
            "recent_trend": {
                "direction": "下降" if downward_trend else "上昇",
                "strength": float(trend_strength)
            },
            "seasonality": seasonality,
            "buy_score": float(buy_score),
            "recommendation": recommendation,
            "recommendation_level": recommendation_level,
            "chart_file": chart_file
        }
    
    def _visualize_buy_timing(self, product, df, buy_score, recommendation_level):
        """買い時分析結果を可視化"""
        plt.figure(figsize=(12, 8))
        
        # サブプロット1: 価格推移
        plt.subplot(2, 1, 1)
        plt.plot(df['fetched_at'], df['price'], 'b-', marker='o', alpha=0.7)
        
        # 現在の価格をマーク
        current_price = df['price'].iloc[-1]
        plt.scatter([df['fetched_at'].iloc[-1]], [current_price], color='red', s=100, zorder=5)
        plt.text(df['fetched_at'].iloc[-1], current_price*1.05, f'現在: ¥{int(current_price):,}', color='red', ha='right')
        
        # 最低価格をマーク
        min_price = df['price'].min()
        min_idx = df['price'].idxmin()
        plt.scatter([df['fetched_at'].iloc[min_idx]], [min_price], color='green', s=100, zorder=5)
        plt.text(df['fetched_at'].iloc[min_idx], min_price*0.95, f'最安値: ¥{int(min_price):,}', color='green', ha='left')
        
        # 平均価格線
        plt.axhline(y=df['price'].mean(), color='gray', linestyle='--', alpha=0.7, label=f'平均: ¥{int(df["price"].mean()):,}')
        
        plt.title(f'価格推移: {product["name"]}', fontsize=14)
        plt.ylabel('価格 (円)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # X軸のフォーマット
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
        
        # サブプロット2: 買い時スコア
        plt.subplot(2, 1, 2)
        
        # スコアゲージを表示
        gauge_colors = {
            "wait": "red",
            "neutral": "orange",
            "good": "lightgreen",
            "excellent": "green"
        }
        
        plt.barh(["買い時スコア"], [buy_score], color=gauge_colors[recommendation_level], alpha=0.7)
        plt.barh(["買い時スコア"], [100], color='lightgray', alpha=0.3)
        
        # スコア領域に色付け
        for score, label, color in [(20, "待機", "red"), (40, "様子見", "orange"), 
                                    (60, "購入検討", "lightgreen"), (80, "お買い得", "green")]:
            plt.axvline(x=score, color=color, linestyle='--', alpha=0.7)
            plt.text(score, 0.5, label, ha='center', va='center', color=color)
        
        # 現在のスコアを表示
        plt.text(buy_score, 1, f"{int(buy_score)}", ha='center', va='bottom', fontsize=16, fontweight='bold')
        
        plt.xlim(0, 100)
        plt.title("買い時スコア (0-100)", fontsize=14)
        plt.grid(axis='x', alpha=0.3)
        
        # 全体の調整
        plt.tight_layout()
        
        # 保存
        filename = f"buy_timing_{product['id']}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filename