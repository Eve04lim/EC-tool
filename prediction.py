# prediction.py - 価格予測モジュール
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

class PriceForecast:
    """価格予測エンジン"""
    
    def __init__(self, db):
        self.db = db
        self.output_dir = os.path.join('static', 'reports')
        os.makedirs(self.output_dir, exist_ok=True)
        self.models = {}  # 商品ごとのモデルを保存
    
    def _prepare_features(self, history_data):
        """特徴量を準備"""
        # DataFrameに変換
        df = pd.DataFrame(history_data)
        
        # 日付を処理
        df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        df = df.sort_values('fetched_at')
        
        # 価格を設定
        df['price'] = df['sale_price'].fillna(df['regular_price'])
        
        # 時間特徴量を抽出
        df['dayofweek'] = df['fetched_at'].dt.dayofweek
        df['month'] = df['fetched_at'].dt.month
        df['day'] = df['fetched_at'].dt.day
        df['days_from_start'] = (df['fetched_at'] - df['fetched_at'].min()).dt.days
        
        # 過去のデータを特徴量としてシフト
        for i in range(1, 4):
            df[f'price_lag_{i}'] = df['price'].shift(i)
            
        # 移動平均
        df['price_ma3'] = df['price'].rolling(window=3).mean()
        df['price_ma7'] = df['price'].rolling(window=7).mean()
        
        # 欠損値を削除
        df = df.dropna()
        
        return df

    def train_model(self, product_id, algorithm='rf'):
        """価格予測モデルを訓練"""
        # 履歴データを取得
        history = self.db.get_product_price_history(product_id, limit=90)
        if len(history) < 10:
            return False, "訓練データが不足しています（10件以上必要）"
        
        # 特徴量を準備
        df = self._prepare_features(history)
        
        # 特徴量とターゲットを分離
        X = df[['dayofweek', 'month', 'day', 'days_from_start', 
               'price_lag_1', 'price_lag_2', 'price_lag_3', 'price_ma3', 'price_ma7']]
        y = df['price']
        
        # データ分割
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # スケーリング
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # モデルを選択
        if algorithm == 'lr':
            model = LinearRegression()
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # モデルを訓練
        model.fit(X_train_scaled, y_train)
        
        # モデルの性能を評価
        score = model.score(X_test_scaled, y_test)
        
        # モデルを保存
        self.models[product_id] = {
            'model': model,
            'scaler': scaler,
            'score': score,
            'last_date': df['fetched_at'].max(),
            'last_features': df.iloc[-1][['dayofweek', 'month', 'day', 'days_from_start', 
                                          'price_lag_1', 'price_lag_2', 'price_lag_3', 'price_ma3', 'price_ma7']]
        }
        
        return True, score
    
    def predict_future_prices(self, product_id, days=30):
        """将来の価格を予測"""
        if product_id not in self.models:
            success, message = self.train_model(product_id)
            if not success:
                return False, message
        
        model_data = self.models[product_id]
        model = model_data['model']
        scaler = model_data['scaler']
        last_date = model_data['last_date']
        
        # 商品情報を取得
        product = self.db.get_product_by_id(product_id)
        if not product:
            return False, "商品が見つかりません"
        
        # 最新の価格情報
        latest_price = self.db.get_latest_price(product_id)
        if not latest_price:
            return False, "価格情報が見つかりません"
        
        current_price = latest_price['sale_price'] or latest_price['regular_price']
        
        # 予測用データを準備
        future_prices = []
        features = model_data['last_features'].copy()
        
        for i in range(days):
            # 予測する日付
            future_date = last_date + timedelta(days=i+1)
            
            # 特徴量を更新
            features['dayofweek'] = future_date.dayofweek
            features['month'] = future_date.month
            features['day'] = future_date.day
            features['days_from_start'] += 1
            
            # ラグ特徴量を更新
            if i == 0:
                price_lag_1 = current_price
                price_lag_2 = features['price_lag_1']
                price_lag_3 = features['price_lag_2']
            elif i == 1:
                price_lag_1 = future_prices[-1]
                price_lag_2 = current_price
                price_lag_3 = features['price_lag_1']
            elif i == 2:
                price_lag_1 = future_prices[-1]
                price_lag_2 = future_prices[-2]
                price_lag_3 = current_price
            else:
                price_lag_1 = future_prices[-1]
                price_lag_2 = future_prices[-2]
                price_lag_3 = future_prices[-3]
            
            features['price_lag_1'] = price_lag_1
            features['price_lag_2'] = price_lag_2
            features['price_lag_3'] = price_lag_3
            
            # 移動平均を更新
            recent_prices = [future_prices[-i] if i < len(future_prices) else current_price for i in range(1, 8)]
            features['price_ma3'] = sum(recent_prices[:3]) / 3
            features['price_ma7'] = sum(recent_prices) / len(recent_prices)
            
            # 特徴量をスケーリング
            X_future = scaler.transform([features])
            
            # 価格を予測
            predicted_price = max(0, model.predict(X_future)[0])
            future_prices.append(predicted_price)
        
        # 結果を返す
        dates = [(last_date + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(days)]
        result = {
            "dates": dates,
            "prices": future_prices,
            "current_price": current_price,
            "model_score": model_data['score']
        }
        
        # 可視化
        self._visualize_prediction(product, current_price, dates, future_prices)
        
        return True, result
    
    def _visualize_prediction(self, product, current_price, dates, predictions):
        """予測結果を可視化"""
        plt.figure(figsize=(12, 6))
        
        # 現在の価格を点線で表示
        plt.axhline(y=current_price, color='r', linestyle='--', alpha=0.7, label='現在の価格')
        
        # 予測価格を実線で表示
        plt.plot(dates, predictions, 'b-', marker='o', label='予測価格')
        
        # グラフの装飾
        plt.title(f'価格予測: {product["name"]}', fontsize=15)
        plt.xlabel('日付')
        plt.ylabel('価格 (円)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # x軸の日付を見やすくする
        num_dates = len(dates)
        if num_dates > 10:
            # 日付を間引く
            step = num_dates // 10 + 1
            plt.xticks(range(0, num_dates, step), [dates[i] for i in range(0, num_dates, step)], rotation=45)
        else:
            plt.xticks(rotation=45)
        
        # マージンの調整
        plt.tight_layout()
        
        # 保存
        filename = f"price_prediction_{product['id']}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()