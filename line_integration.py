# line_integration.py - LINE通知機能
import requests
import json
from datetime import datetime
import os
from database import Database

class LineNotifier:
    """LINE通知機能"""
    
    def __init__(self, channel_access_token=None, user_id=None):
        self.channel_access_token = channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.user_id = user_id or os.getenv("LINE_USER_ID")
        self.api_url = "https://api.line.me/v2/bot/message/push"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
    
    def send_price_alert(self, product, old_price, new_price, change_percent):
        """価格変動通知"""
        if not self.channel_access_token or not self.user_id:
            print("LINE設定が不足しています")
            return False
            
        direction = "上昇" if new_price > old_price else "下落"
        color = "#FF0000" if direction == "上昇" else "#00B900"
        
        message = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "flex",
                    "altText": f"価格変動通知: {product['name']}",
                    "contents": {
                        "type": "bubble",
                        "header": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "価格変動通知",
                                    "weight": "bold",
                                    "size": "xl",
                                    "color": "#ffffff"
                                }
                            ],
                            "backgroundColor": color
                        },
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": product['name'],
                                    "weight": "bold",
                                    "size": "md",
                                    "wrap": True
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"価格{direction}: {abs(change_percent):.1f}%",
                                            "size": "lg",
                                            "color": color,
                                            "weight": "bold"
                                        },
                                        {
                                            "type": "text",
                                            "text": f"¥{int(old_price):,} → ¥{int(new_price):,}",
                                            "size": "sm",
                                            "margin": "md"
                                        }
                                    ],
                                    "margin": "md"
                                }
                            ]
                        },
                        "footer": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "button",
                                    "action": {
                                        "type": "uri",
                                        "label": "商品ページを開く",
                                        "uri": product['url']
                                    },
                                    "style": "primary"
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(message)
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"LINE通知エラー: {e}")
            return False
    
    def send_stock_alert(self, product, in_stock):
        """在庫状況変化通知"""
        if not self.channel_access_token or not self.user_id:
            print("LINE設定が不足しています")
            return False
            
        status = "在庫あり" if in_stock else "在庫なし"
        color = "#00B900" if in_stock else "#FF0000"
        
        message = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "flex",
                    "altText": f"在庫状況通知: {product['name']}",
                    "contents": {
                        "type": "bubble",
                        "header": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "在庫状況通知",
                                    "weight": "bold",
                                    "size": "xl",
                                    "color": "#ffffff"
                                }
                            ],
                            "backgroundColor": color
                        },
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": product['name'],
                                    "weight": "bold",
                                    "size": "md",
                                    "wrap": True
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": status,
                                            "size": "lg",
                                            "color": color,
                                            "weight": "bold"
                                        },
                                        {
                                            "type": "text",
                                            "text": f"{datetime.now().strftime('%Y-%m-%d %H:%M')}現在",
                                            "size": "sm",
                                            "margin": "md"
                                        }
                                    ],
                                    "margin": "md"
                                }
                            ]
                        },
                        "footer": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "button",
                                    "action": {
                                        "type": "uri",
                                        "label": "商品ページを開く",
                                        "uri": product['url']
                                    },
                                    "style": "primary"
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                data=json.dumps(message)
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"LINE通知エラー: {e}")
            return False