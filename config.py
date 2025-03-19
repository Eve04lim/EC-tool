# config.py - 設定ファイル
import os
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

# データベース設定
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite または postgresql
DB_NAME = os.getenv("DB_NAME", "ec_tracker.db")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = os.getenv("DB_PORT", "")

# EC サイト設定
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
REQUEST_TIMEOUT = 30
REQUEST_RETRY = 3
REQUEST_INTERVAL = 5  # 秒

# Selenium 設定
SELENIUM_TIMEOUT = 30
SELENIUM_WAIT = 5  # 秒

# 通知設定
NOTIFICATION_PRICE_THRESHOLD = 10  # パーセント
ENABLE_EMAIL = os.getenv("ENABLE_EMAIL", "False").lower() == "true"
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")

ENABLE_SLACK = os.getenv("ENABLE_SLACK", "False").lower() == "true"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Google スプレッドシート設定
ENABLE_GSHEETS = os.getenv("ENABLE_GSHEETS", "False").lower() == "true"
GSHEETS_CREDENTIALS_FILE = os.getenv("GSHEETS_CREDENTIALS_FILE", "credentials.json")
GSHEETS_TOKEN_FILE = os.getenv("GSHEETS_TOKEN_FILE", "token.json")
GSHEETS_SPREADSHEET_ID = os.getenv("GSHEETS_SPREADSHEET_ID", "")

# ロギング設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "ec_tracker.log")

# プロキシ設定（オプション）
ENABLE_PROXY = os.getenv("ENABLE_PROXY", "False").lower() == "true"
PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []

# CHROME_DRIVER_PATHの設定
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH", "C:\\chromedriver\\chromedriver.exe")