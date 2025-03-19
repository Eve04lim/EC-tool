# stock_alert.py - 在庫アラート・再入荷通知システム
import time
import threading
import schedule
import logging
from datetime import datetime, timedelta
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

class StockAlertSystem:
    """在庫アラート・再入荷通知システム"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.running = False
        self.thread = None
        self.alert_subscriptions = self._load_subscriptions()
        self.logger = logging.getLogger(__name__)
    
    def _load_subscriptions(self):
        """商品ごとの通知登録者を読み込む"""
        try:
            with open('stock_subscriptions.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_subscriptions(self):
        """通知登録情報を保存"""
        with open('stock_subscriptions.json', 'w') as f:
            json.dump(self.alert_subscriptions, f)
    
    def subscribe(self, product_id, email, phone=None):
        """在庫アラート登録"""
        product_id = str(product_id)
        if product_id not in self.alert_subscriptions:
            self.alert_subscriptions[product_id] = {'emails': [], 'phones': []}
        
        # メールアドレスを検証
        if email and re.match(r"[^@]+@[^@]+\.[^@]+", email):
            if email not in self.alert_subscriptions[product_id]['emails']:
                self.alert_subscriptions[product_id]['emails'].append(email)
        
        # 電話番号を検証 (SMSやLINE通知用)
        if phone and re.match(r"^\d{10,11}$", phone.replace('-', '')):
            if phone not in self.alert_subscriptions[product_id]['phones']:
                self.alert_subscriptions[product_id]['phones'].append(phone)
        
        self._save_subscriptions()
        self.logger.info(f"Stock alert subscription added for product {product_id}")
        return True
    
    def unsubscribe(self, product_id, email=None, phone=None):
        """在庫アラート登録解除"""
        product_id = str(product_id)
        if product_id not in self.alert_subscriptions:
            return False
        
        if email and email in self.alert_subscriptions[product_id]['emails']:
            self.alert_subscriptions[product_id]['emails'].remove(email)
        
        if phone and phone in self.alert_subscriptions[product_id]['phones']:
            self.alert_subscriptions[product_id]['phones'].remove(phone)
        
        # 登録者がいなくなった場合は商品自体を削除
        if not self.alert_subscriptions[product_id]['emails'] and not self.alert_subscriptions[product_id]['phones']:
            del self.alert_subscriptions[product_id]
        
        self._save_subscriptions()
        self.logger.info(f"Stock alert subscription removed for product {product_id}")
        return True
    
    def check_stock_changes(self):
        """在庫変更をチェックして通知"""
        self.logger.info("Checking stock changes...")
        products = self.db.get_all_products()
        
        for product in products:
            product_id = str(product['id'])
            
            # 登録者がいない商品はスキップ
            if product_id not in self.alert_subscriptions:
                continue
            
            # 過去の在庫状況
            history = self.db.get_product_price_history(product['id'], limit=5)
            
            if len(history) < 2:
                continue
            
            current_stock = history[0]['in_stock']
            previous_stock = history[1]['in_stock']
            
            # 在庫状況が変わった場合（特に在庫切れ→在庫あり）
            if current_stock != previous_stock and current_stock:
                # 再入荷通知
                self._send_restock_alerts(product, self.alert_subscriptions[product_id])
    
    def _send_restock_alerts(self, product, subscribers):
        """再入荷通知を送信"""
        product_name = product['name']
        product_url = product['url']
        
        # メール通知
        for email in subscribers['emails']:
            self._send_restock_email(email, product_name, product_url)
        
        # SMS/LINE通知
        for phone in subscribers['phones']:
            self._send_restock_sms(phone, product_name, product_url)
        
        # 通知履歴を記録
        self.db.add_notification(
            product_id=product['id'],
            notification_type='restock',
            message=f"再入荷通知: {len(subscribers['emails'])}件のメールと{len(subscribers['phones'])}件のSMSを送信"
        )
    
    def _send_restock_email(self, email, product_name, product_url):
        """再入荷メールを送信"""
        try:
            message = MIMEMultipart()
            message['From'] = self.config.EMAIL_USER
            message['To'] = email
            message['Subject'] = f"【再入荷通知】{product_name}"
            
            body = f"""
            <html>
            <body>
                <h2>商品が再入荷しました！</h2>
                <p>以下の商品の在庫が確認されました。</p>
                <p><strong>{product_name}</strong></p>
                <p><a href="{product_url}">商品ページを開く</a></p>
                <p>※在庫状況は変動する場合があります。お早めにご確認ください。</p>
                <hr>
                <p><small>EC商品追跡ツールからの自動通知です。配信停止をご希望の場合はこのメールにご返信ください。</small></p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.config.EMAIL_SERVER, self.config.EMAIL_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(message)
            
            self.logger.info(f"Restock email sent to {email}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send restock email: {e}")
            return False
    
    def _send_restock_sms(self, phone, product_name, product_url):
        """再入荷SMSを送信"""
        # 外部SMS APIを使用
        # ここでは例としてTwilioのAPIに似た実装を示す
        try:
            # 実際にはTwilioやその他のSMS APIを使用する
            message = f"【再入荷通知】{product_name}の在庫が確認されました。{product_url}"
            
            # APIを呼び出す代わりにログ出力
            self.logger.info(f"SMS message would be sent to {phone}: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send restock SMS: {e}")
            return False
    
    def start(self, interval_minutes=60):
        """定期チェックを開始"""
        if self.running:
            return False
        
        self.running = True
        
        def run_scheduler():
            # スケジュール設定
            schedule.every(interval_minutes).minutes.do(self.check_stock_changes)
            
            # 最初は即実行
            self.check_stock_changes()
            
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        # 別スレッドでスケジューラーを実行
        self.thread = threading.Thread(target=run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        
        self.logger.info(f"Stock alert system started with {interval_minutes} minutes interval")
        return True
    
    def stop(self):
        """定期チェックを停止"""
        if not self.running:
            return False
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
            self.thread = None
        
        self.logger.info("Stock alert system stopped")
        return True