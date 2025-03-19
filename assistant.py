# assistant.py - AIアシスタント・自動レポート生成
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import openai
import os
from database import Database
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config import EMAIL_SERVER, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO

class ECAssistant:
    """AIアシスタント・自動レポート生成"""
    
    def __init__(self, db, api_key=None):
        self.db = db
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        self.output_dir = "reports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_weekly_report(self):
        """週次レポートを生成"""
        # データ準備
        products = self.db.get_all_products()
        if not products:
            return None
            
        # 週次データの計算
        report_data = {
            'product_count': len(products),
            'price_changes': [],
            'stock_changes': [],
            'top_products': [],
            'platforms': {'amazon': 0, 'rakuten': 0, 'yahoo': 0}
        }
        
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        for product in products:
            # プラットフォームの集計
            platform = product['platform']
            if platform in report_data['platforms']:
                report_data['platforms'][platform] += 1
            
            # 価格履歴を取得
            history = self.db.get_product_price_history(product['id'])
            
            # 直近の履歴を時間でフィルタリング
            recent_history = []
            for item in history:
                date = item['fetched_at']
                if isinstance(date, str):
                    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                if date >= week_ago:
                    recent_history.append(item)
            
            if recent_history and len(recent_history) >= 2:
                newest = recent_history[0]
                oldest = recent_history[-1]
                
                # 価格変化
                newest_price = newest['sale_price'] or newest['regular_price']
                oldest_price = oldest['sale_price'] or oldest['regular_price']
                
                if newest_price and oldest_price and newest_price != oldest_price:
                    change_pct = (newest_price - oldest_price) / oldest_price * 100
                    report_data['price_changes'].append({
                        'product': product['name'],
                        'platform': product['platform'],
                        'old_price': oldest_price,
                        'new_price': newest_price,
                        'change_pct': change_pct
                    })
                
                # 在庫変化
                if newest['in_stock'] != oldest['in_stock']:
                    report_data['stock_changes'].append({
                        'product': product['name'],
                        'platform': product['platform'],
                        'old_stock': '在庫あり' if oldest['in_stock'] else '在庫なし',
                        'new_stock': '在庫あり' if newest['in_stock'] else '在庫なし'
                    })
        
        # 価格変動が大きい順にソート
        report_data['price_changes'] = sorted(
            report_data['price_changes'], 
            key=lambda x: abs(x['change_pct']), 
            reverse=True
        )
        
        # レポート生成
        if self.api_key:
            report_text = self._generate_ai_report(report_data)
        else:
            report_text = self._generate_basic_report(report_data)
        
        # HTML形式で保存
        filename = f"{self.output_dir}/weekly_report_{now.strftime('%Y%m%d')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return filename
    
    def _generate_ai_report(self, data):
        """OpenAI APIを使用したAIレポート生成"""
        try:
            # レポートデータをJSON形式に変換
            data_json = json.dumps(data, ensure_ascii=False, indent=2)
            
            # OpenAI APIリクエスト
            prompt = f"""
            あなたはEC市場分析の専門家です。以下のデータを元に、ECサイト価格・在庫追跡ツールの週次レポートを作成してください。
            データはJSON形式で提供されます。レポートはHTML形式で作成し、適切な見出し、段落、表、色分け等を使用して読みやすく仕上げてください。
            
            データ:
            {data_json}
            
            レポートには以下の要素を含めてください：
            1. 全体サマリー（追跡商品数、プラットフォーム別商品数など）
            2. 価格変動のあった商品のハイライト（上昇/下落）
            3. 在庫状況に変化のあった商品
            4. 市場の傾向と分析
            5. 次週に注目すべきポイント
            
            レポートは専門的かつ具体的な内容にしてください。
            """
            
            response = openai.Completion.create(
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            report_text = response.choices[0].text.strip()
            
            # レスポンスがHTMLでない場合はHTMLで包む
            if not report_text.startswith('<'):
                report_text = f"""
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
                    <h1>ECサイト価格・在庫追跡 週次レポート</h1>
                    <p><strong>生成日時:</strong> {datetime.now().strftime('%Y年%m月%d日')}</p>
                    {report_text}
                </body>
                </html>
                """
            
            return report_text
            
        except Exception as e:
            print(f"AIレポート生成エラー: {e}")
            # エラー時はベーシックレポートにフォールバック
            return self._generate_basic_report(data)
    
    def _generate_basic_report(self, data):
        """基本的なテンプレートベースのレポート生成"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        # プラットフォーム分布
        platform_html = ""
        for platform, count in data['platforms'].items():
            if count > 0:
                platform_name = {'amazon': 'Amazon', 'rakuten': '楽天市場', 'yahoo': 'Yahoo!ショッピング'}.get(platform, platform)
                platform_html += f"<li>{platform_name}: {count}商品</li>"
        
        # 価格変動テーブル
        price_changes_html = ""
        if data['price_changes']:
            price_changes_html = """
            <h2>価格変動のあった商品</h2>
            <table>
                <tr>
                    <th>商品名</th>
                    <th>プラットフォーム</th>
                    <th>価格変動</th>
                    <th>変動率</th>
                </tr>
            """
            
            for change in data['price_changes'][:10]:  # 上位10件
                direction_class = "up" if change['change_pct'] > 0 else "down"
                direction_symbol = "↑" if change['change_pct'] > 0 else "↓"
                
                price_changes_html += f"""
                <tr>
                    <td>{change['product']}</td>
                    <td>{change['platform']}</td>
                    <td>¥{int(change['old_price']):,} → ¥{int(change['new_price']):,}</td>
                    <td class="{direction_class}">{direction_symbol} {abs(change['change_pct']):.1f}%</td>
                </tr>
                """
            
            price_changes_html += "</table>"
        
        # 在庫変動テーブル
        stock_changes_html = ""
        if data['stock_changes']:
            stock_changes_html = """
            <h2>在庫状況に変化のあった商品</h2>
            <table>
                <tr>
                    <th>商品名</th>
                    <th>プラットフォーム</th>
                    <th>変化</th>
                </tr>
            """
            
            for change in data['stock_changes']:
                stock_changes_html += f"""
                <tr>
                    <td>{change['product']}</td>
                    <td>{change['platform']}</td>
                    <td>{change['old_stock']} → {change['new_stock']}</td>
                </tr>
                """
            
            stock_changes_html += "</table>"
        
        # レポート全体のHTML
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
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>ECサイト価格・在庫追跡 週次レポート</h1>
            <p><strong>生成日時:</strong> {now.strftime('%Y年%m月%d日')}</p>
            <p><strong>対象期間:</strong> {week_ago.strftime('%Y年%m月%d日')} 〜 {now.strftime('%Y年%m月%d日')}</p>
            
            <div class="summary">
                <h2>サマリー</h2>
                <p>現在、<strong>{data['product_count']}商品</strong>を追跡中です。</p>
                <p>プラットフォーム別商品数:</p>
                <ul>
                    {platform_html}
                </ul>
                <p>過去1週間で<strong>{len(data['price_changes'])}</strong>件の価格変動と<strong>{len(data['stock_changes'])}</strong>件の在庫変動がありました。</p>
            </div>
            
            {price_changes_html}
            
            {stock_changes_html}
            
            <h2>市場の傾向</h2>
            <p>過去1週間の全体的な傾向として、価格の変動が見られる商品が複数あります。特に注目すべき変動については上記の表をご参照ください。</p>
            
            <h2>次週に注目すべきポイント</h2>
            <p>価格変動の大きい商品については引き続き追跡が必要です。また、在庫状況が変化した商品については、今後の入荷状況や価格変動に注意が必要かもしれません。</p>
        </body>
        </html>
        """
        
        return html
    
    def send_report_email(self, report_file):
        """レポートをメールで送信"""
        try:
            if not os.path.exists(report_file):
                print(f"レポートファイルが見つかりません: {report_file}")
                return False
                
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USER
            msg['To'] = ", ".join(EMAIL_TO) if isinstance(EMAIL_TO, list) else EMAIL_TO
            msg['Subject'] = f"ECサイト価格・在庫追跡 週次レポート {datetime.now().strftime('%Y-%m-%d')}"
            
            # 本文
            body = """
            <html>
            <body>
                <p>お世話になっております。</p>
                <p>ECサイト価格・在庫追跡ツールの週次レポートを添付いたします。</p>
                <p>主な内容:</p>
                <ul>
                    <li>価格変動のあった商品</li>
                    <li>在庫状況に変化のあった商品</li>
                    <li>市場の傾向と分析</li>
                </ul>
                <p>詳細は添付ファイルをご確認ください。</p>
                <p>--<br>ECサイト価格・在庫追跡ツール</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            
            # 添付ファイル
            with open(report_file, 'r', encoding='utf-8') as f:
                attachment = MIMEApplication(f.read(), _subtype='html')
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(report_file))
                msg.attach(attachment)
            
            # メール送信
            with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
            
            print(f"レポートメールを送信しました: {report_file}")
            return True
        
        except Exception as e:
            print(f"メール送信エラー: {e}")
            return False