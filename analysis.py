# analysis.py - データ分析・可視化モジュール
import matplotlib
matplotlib.use('Agg')  # GUI不要なバックエンドを指定（必ずここに追加する）
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
import os
import io
import base64


class PriceAnalyzer:
    """価格分析・可視化クラス"""
    
    def __init__(self, db):
        self.db = db
        self.output_dir = os.path.join('static', 'reports')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_price_trend_chart(self, product_id, days=30):
        """価格推移グラフを生成"""
        product = self.db.get_product_by_id(product_id)
        history = self.db.get_product_price_history(product_id, limit=days)
        
        if not product or not history:
            return None
        
        # DataFrameに変換
        df = pd.DataFrame(history)
        if 'fetched_at' in df.columns:
            try:
                df['fetched_at'] = pd.to_datetime(df['fetched_at'])
                df = df.sort_values('fetched_at')
            except Exception as e:
                print(f"日付変換エラー: {e}")
        
        # グラフ作成
        plt.figure(figsize=(12, 6))
        
        # 通常価格
        if 'regular_price' in df.columns:
            plt.plot(df['fetched_at'], df['regular_price'], 'b-', label='通常価格')
        
        # セール価格
        if 'sale_price' in df.columns:
            plt.plot(df['fetched_at'], df['sale_price'], 'r-', label='セール価格')
        
        # タイトルと軸ラベル
        plt.title(f'価格推移: {product["name"]}', fontsize=15)
        plt.xlabel('日付')
        plt.ylabel('価格 (円)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # 日付フォーマットを調整
        plt.gcf().autofmt_xdate()
        
        # 保存
        filename = f"price_trend_{product_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_price_comparison(self, product_ids, output_format='html'):
        """複数商品の価格比較グラフ"""
        if not product_ids:
            return None
            
        # データ収集
        data = []
        for pid in product_ids:
            product = self.db.get_product_by_id(pid)
            latest = self.db.get_latest_price(pid)
            if product and latest:
                price = latest['sale_price'] if latest['sale_price'] else latest['regular_price']
                data.append({
                    'id': pid,
                    'name': product['name'],
                    'platform': product['platform'],
                    'price': price
                })
        
        if not data:
            return None
            
        df = pd.DataFrame(data)
        
        # グラフ作成
        plt.figure(figsize=(10, 6))
        bars = plt.bar(df['name'], df['price'], color=sns.color_palette("muted", len(df)))
        
        # プラットフォームに基づいて色分け
        platform_colors = {'amazon': 'orange', 'rakuten': 'red', 'yahoo': 'green'}
        for i, platform in enumerate(df['platform']):
            color = platform_colors.get(platform, 'blue')
            bars[i].set_color(color)
        
        plt.title('商品価格比較', fontsize=15)
        plt.ylabel('価格 (円)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # 価格ラベルを追加
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'¥{int(height):,}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 出力形式に応じて保存
        filename = f"price_comparison.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        if output_format == 'html':
            # HTMLページを作成
            html_file = f"price_comparison.html"
            html_path = os.path.join(self.output_dir, html_file)
            
            # 画像のBase64エンコード
            with open(filepath, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            html = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
                    h1, h2 {{ color: #3498db; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .amazon {{ color: #ff9900; }}
                    .rakuten {{ color: #bf0000; }}
                    .yahoo {{ color: #ff0033; }}
                </style>
            </head>
            <body>
                <h1>商品価格比較</h1>
                <img src="data:image/png;base64,{img_data}" style="max-width: 100%;">
                <h2>価格比較表</h2>
                <table>
                    <tr>
                        <th>商品名</th>
                        <th>プラットフォーム</th>
                        <th>価格</th>
                    </tr>
            """
            
            for item in data:
                platform_class = item['platform']
                html += f"""
                    <tr>
                        <td>{item['name']}</td>
                        <td class="{platform_class}">{item['platform']}</td>
                        <td>¥{int(item['price']):,}</td>
                    </tr>
                """
            
            html += """
                </table>
            </body>
            </html>
            """
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            return html_path
        else:
            return filepath
    
    def generate_price_alerts_report(self, threshold_percent=10, days=7):
        """価格変動アラートレポート"""
        products = self.db.get_all_products()
        alerts = []
        
        for product in products:
            history = self.db.get_product_price_history(product['id'], limit=30)
            if len(history) < 2:
                continue
                
            # 最新と最古の価格を比較
            newest = history[0]
            oldest = history[-1]
            
            newest_price = newest['sale_price'] or newest['regular_price']
            oldest_price = oldest['sale_price'] or oldest['regular_price']
            
            if newest_price and oldest_price:
                change = (newest_price - oldest_price) / oldest_price * 100
                if abs(change) >= threshold_percent:
                    direction = "上昇" if change > 0 else "下落"
                    alerts.append({
                        'id': product['id'],
                        'name': product['name'],
                        'platform': product['platform'],
                        'old_price': oldest_price,
                        'new_price': newest_price,
                        'change': change,
                        'direction': direction,
                        'url': product['url']
                    })
        
        if not alerts:
            return None
            
        # レポート生成
        html_file = f"price_alerts.html"
        html_path = os.path.join(self.output_dir, html_file)
        
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #2c3e50; text-align: center; }}
                h2 {{ color: #3498db; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .up {{ color: #e74c3c; }}
                .down {{ color: #27ae60; }}
            </style>
        </head>
        <body>
            <h1>価格変動アラートレポート</h1>
            <p style="text-align: center; color: #666;">生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p style="text-align: center;">過去{days}日間で{threshold_percent}%以上の価格変動があった商品</p>
            
            <table>
                <tr>
                    <th>商品名</th>
                    <th>プラットフォーム</th>
                    <th>価格変動</th>
                    <th>変動率</th>
                    <th>リンク</th>
                </tr>
        """
        
        for alert in alerts:
            color = "#ff7675" if alert['direction'] == "上昇" else "#27ae60"
            html += f"""
                <tr>
                    <td>{alert['name']}</td>
                    <td>{alert['platform']}</td>
                    <td>
                        ¥{int(alert['old_price']):,} → ¥{int(alert['new_price']):,}
                    </td>
                    <td style="color: {color};">
                        {alert['direction']} {abs(alert['change']):.1f}%
                    </td>
                    <td>
                        <a href="{alert['url']}" target="_blank">商品ページ</a>
                    </td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return (html_file, len(alerts))