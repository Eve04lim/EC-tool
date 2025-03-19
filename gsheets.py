# gsheets.py - Google Sheets連携モジュール
import logging
import os.path
import json
import pandas as pd
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config import GSHEETS_CREDENTIALS_FILE, GSHEETS_TOKEN_FILE, GSHEETS_SPREADSHEET_ID

logger = logging.getLogger(__name__)

# 必要なスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsExporter:
    """Google Sheetsにデータをエクスポートするクラス"""
    
    def __init__(self):
        """初期化"""
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Google APIの認証を行う"""
        creds = None
        
        # 既存のトークンがあれば読み込む
        if os.path.exists(GSHEETS_TOKEN_FILE):
            creds = Credentials.from_authorized_user_info(
                json.loads(open(GSHEETS_TOKEN_FILE).read()), SCOPES)
        
        # 有効な認証情報がない、または期限切れの場合は更新または新規取得
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GSHEETS_CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # トークンを保存
            with open(GSHEETS_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        # サービスを初期化
        self.service = build('sheets', 'v4', credentials=creds)
        logger.info("Authenticated with Google Sheets API")
    
    def export_products(self, db):
        """商品情報をエクスポートする"""
        try:
            # すべての製品を取得
            products = db.get_all_products()
            if not products:
                logger.warning("No products to export")
                return False
            
            # データフレームを作成
            rows = []
            for product in products:
                # 最新の価格情報を取得
                latest_price = db.get_latest_price(product['id'])
                
                # 日時処理の修正：すでに文字列ならそのまま使用、datetimeオブジェクトならフォーマット
                if latest_price:
                    if isinstance(latest_price['fetched_at'], str):
                        fetched_at = latest_price['fetched_at']
                    else:
                        fetched_at = latest_price['fetched_at'].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    fetched_at = None
                
                # 製品と価格情報をマージ
                product_data = {
                    'ID': product['id'],
                    '商品名': product['name'],
                    'プラットフォーム': product['platform'],
                    '商品コード': product['product_code'],
                    '通常価格': latest_price['regular_price'] if latest_price else None,
                    'セール価格': latest_price['sale_price'] if latest_price else None,
                    '在庫状況': '在庫あり' if latest_price and latest_price['in_stock'] else '在庫なし',
                    'レビュー数': latest_price['review_count'] if latest_price else None,
                    'レビュー評価': latest_price['review_rating'] if latest_price else None,
                    '最終更新日': fetched_at,
                    'URL': product['url'],
                    '画像URL': product['image_url']
                }
                rows.append(product_data)
            
            df = pd.DataFrame(rows)
            
            # スプレッドシートを更新
            self._update_sheet(df, 'Products', clear=True)
            logger.info(f"Exported {len(rows)} products to Google Sheets")
            
            # スプレッドシートのURLを表示（デバッグ用）
            print(f"スプレッドシートURL: https://docs.google.com/spreadsheets/d/{GSHEETS_SPREADSHEET_ID}/edit")
            
            return True
        except Exception as e:
            logger.error(f"Failed to export products: {e}")
            return False
    
    def export_price_history(self, db, days=30):
        """価格履歴をエクスポートする"""
        try:
            products = db.get_all_products()
            if not products:
                logger.warning("No products to export price history")
                return False
            
            # すべての製品の価格履歴を取得
            rows = []
            for product in products:
                price_history = db.get_product_price_history(product['id'], limit=days)
                
                for price in price_history:
                    # 日時処理の修正
                    if isinstance(price['fetched_at'], str):
                        fetched_at = price['fetched_at']
                    else:
                        fetched_at = price['fetched_at'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    history_data = {
                        '商品ID': product['id'],
                        '商品名': product['name'],
                        'プラットフォーム': product['platform'],
                        '通常価格': price['regular_price'],
                        'セール価格': price['sale_price'],
                        '在庫状況': '在庫あり' if price['in_stock'] else '在庫なし',
                        'レビュー数': price['review_count'],
                        'レビュー評価': price['review_rating'],
                        '取得日時': fetched_at
                    }
                    rows.append(history_data)
            
            df = pd.DataFrame(rows)
            
            # 日付で降順ソート
            if not df.empty:
                try:
                    if '取得日時' in df.columns:
                        df['取得日時'] = pd.to_datetime(df['取得日時'], errors='coerce')
                        df = df.sort_values('取得日時', ascending=False)
                except Exception as e:
                    logger.warning(f"Failed to sort by date: {e}")
            
            # スプレッドシートを更新
            self._update_sheet(df, 'PriceHistory', clear=True)
            logger.info(f"Exported price history for {len(products)} products to Google Sheets")
            
            return True
        except Exception as e:
            logger.error(f"Failed to export price history: {e}")
            return False
    
    def _update_sheet(self, df, sheet_name, clear=False):
        """指定したシートにデータフレームを書き込む"""
        # データが空の場合は処理しない
        if df.empty:
            logger.warning(f"No data to update in sheet: {sheet_name}")
            return
        
        # シートIDを取得
        sheet_id = self._get_or_create_sheet(sheet_name)
        
        # シートをクリアする（オプション）
        if clear:
            clear_request = self.service.spreadsheets().values().clear(
                spreadsheetId=GSHEETS_SPREADSHEET_ID,
                range=f"{sheet_name}!A:Z"
            )
            clear_request.execute()
        
        # データを準備し、特殊な値を処理
        # NaN, None, 複雑なオブジェクトなどを適切に変換
        df = df.fillna('')  # NaNを空文字に変換
        
        # 日付型を文字列に変換
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # データフレームをリストに変換
        values = [df.columns.tolist()]  # ヘッダー
        
        # 各行を処理して特殊な値を適切に変換
        for _, row in df.iterrows():
            row_data = []
            for val in row:
                if val is None:
                    row_data.append('')
                elif isinstance(val, (float, int)) and pd.isna(val):
                    row_data.append('')
                else:
                    try:
                        # オブジェクトを文字列に変換
                        row_data.append(str(val))
                    except:
                        row_data.append('')
            values.append(row_data)
        
        # シートに書き込む
        body = {
            'values': values
        }
        
        update_request = self.service.spreadsheets().values().update(
            spreadsheetId=GSHEETS_SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption='RAW',
            body=body
        )
        update_request.execute()
        
        logger.info(f"Updated sheet: {sheet_name} with {len(df)} rows")
    
    def _get_or_create_sheet(self, sheet_name):
        """指定した名前のシートを取得、なければ作成する"""
        # スプレッドシートの情報を取得
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=GSHEETS_SPREADSHEET_ID
        ).execute()
        
        # 既存のシートをチェック
        sheets = spreadsheet.get('sheets', [])
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        # シートが存在しない場合は新規作成
        request = {
            'addSheet': {
                'properties': {
                    'title': sheet_name
                }
            }
        }
        
        response = self.service.spreadsheets().batchUpdate(
            spreadsheetId=GSHEETS_SPREADSHEET_ID,
            body={'requests': [request]}
        ).execute()
        
        # 新しいシートのIDを返す
        return response['replies'][0]['addSheet']['properties']['sheetId']
    
    def create_new_spreadsheet(self, title="EC商品追跡データ"):
        """新しいスプレッドシートを作成する"""
        try:
            spreadsheet_body = {
                'properties': {
                    'title': title
                },
                'sheets': [
                    {'properties': {'title': 'Products'}},
                    {'properties': {'title': 'PriceHistory'}}
                ]
            }
            
            request = self.service.spreadsheets().create(body=spreadsheet_body)
            response = request.execute()
            
            spreadsheet_id = response['spreadsheetId']
            spreadsheet_url = response['spreadsheetUrl']
            
            print(f"新しいスプレッドシートを作成しました:")
            print(f"ID: {spreadsheet_id}")
            print(f"URL: {spreadsheet_url}")
            print(f".envファイルのGSHEETS_SPREADSHEET_IDにこのIDを設定してください")
            
            return spreadsheet_id
        except Exception as e:
            logger.error(f"Failed to create new spreadsheet: {e}")
            return None