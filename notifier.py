# notifier.py - 通知モジュール
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from config import (
    ENABLE_EMAIL, EMAIL_SERVER, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO,
    ENABLE_SLACK, SLACK_WEBHOOK_URL, NOTIFICATION_PRICE_THRESHOLD
)

logger = logging.getLogger(__name__)

class Notifier:
    """通知を送信するクラス"""
    
    def __init__(self, db):
        """初期化"""
        self.db = db
        logger.info("Notifier initialized")
    
    def check_price_change(self, product_id, new_price, old_price):
        """価格変動をチェックし、閾値を超えていれば通知する"""
        if not old_price or not new_price:
            return False
        
        # 価格差の割合を計算
        price_diff_percent = abs((new_price - old_price) / old_price * 100)
        
        # 閾値を超えているかチェック
        if price_diff_percent >= NOTIFICATION_PRICE_THRESHOLD:
            product = self.db.get_product_by_id(product_id)
            if not product:
                logger.error(f"Product not found for ID: {product_id}")
                return False
            
            message = self._create_price_change_message(
                product, 
                old_price, 
                new_price, 
                price_diff_percent
            )
            
            self._send_notification(product_id, "price_change", message)
            return True
        
        return False
    
    def check_stock_change(self, product_id, new_stock, old_stock):
        """在庫状況の変化をチェックし、変化があれば通知する"""
        if new_stock is None or old_stock is None:
            return False
        
        if new_stock != old_stock:
            product = self.db.get_product_by_id(product_id)
            if not product:
                logger.error(f"Product not found for ID: {product_id}")
                return False
            
            message = self._create_stock_change_message(
                product, 
                old_stock, 
                new_stock
            )
            
            self._send_notification(product_id, "stock_change", message)
            return True
        
        return False
    
    def _create_price_change_message(self, product, old_price, new_price, price_diff_percent):
        """価格変動の通知メッセージを作成する"""
        direction = "上昇" if new_price > old_price else "下落"
        
        message = f"""
商品: {product['name']}
価格{direction}: ¥{old_price:,} → ¥{new_price:,} ({price_diff_percent:.1f}% {direction})
URL: {product['url']}
        """
        
        return message.strip()
    
    def _create_stock_change_message(self, product, old_stock, new_stock):
        """在庫状況変化の通知メッセージを作成する"""
        status_text = {
            True: "在庫あり",
            False: "在庫なし"
        }
        
        message = f"""
商品: {product['name']}
在庫状況変化: {status_text[old_stock]} → {status_text[new_stock]}
URL: {product['url']}
        """
        
        return message.strip()
    
    def _send_notification(self, product_id, notification_type, message):
        """通知を送信する"""
        logger.info(f"Sending notification for product {product_id}: {notification_type}")
        
        # 通知履歴をデータベースに保存
        self.db.add_notification(product_id, notification_type, message)
        
        # Eメール通知
        if ENABLE_EMAIL:
            try:
                self._send_email_notification(message)
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
        
        # Slack通知
        if ENABLE_SLACK:
            try:
                self._send_slack_notification(message)
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_email_notification(self, message):
        """Eメール通知を送信する"""
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ", ".join(EMAIL_TO)
        msg['Subject'] = "EC商品追跡ツール通知"
        
        body = MIMEText(message, 'plain')
        msg.attach(body)
        
        try:
            with smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info("Email notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
    
    def _send_slack_notification(self, message):
        """Slack通知を送信する"""
        payload = {
            "text": f"*EC商品追跡ツール通知*\n```{message}```"
        }
        
        try:
            response = requests.post(
                SLACK_WEBHOOK_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            logger.info("Slack notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            raise