# EC-tool

このツールは、Amazon（US）とAmazon（JP）の商品の価格を比較するためのPythonツールです。

## 使用方法

### 必要な環境

- Python 3.x
- Google Sheets API
- Selenium、BeautifulSoup

### インストール

以下のコマンドでライブラリをインストールしてください。

```bash
pip install -r requirements.txt
```

### 実行手順

1. リポジトリをクローンします。

```bash
git clone https://github.com/yourusername/EC-tool.git
```

1. 必要なライブラリをインストールします。

```bash
pip install -r requirements.txt
```

1. Seleniumで使用する`chromedriver.exe`を配置します。

```bash
EC-tool/
├── chromedriver.exe
└── main.py
```

1. スクリプトを実行します。

```bash
python main.py
```

## 設定

`config.py`を作成し、Google Sheetsの情報を記入します。

```python
# config.py
SHEET_ID = 'あなたのGSHEETSのID'
SHEET_NAME = 'あなたのGSHEETSのシート名'
```

## 出力

ツールを実行すると、以下の情報が`output.json`に保存されます。

- 商品名
- ASINコード
- 価格（US、JP）
- 最安値
- 競合数

```json
{
  "asin": "B00EXAMPLE",
  "title": "サンプル商品",
  "price": "$20.00",
  "rating": "4.5",
  "url": "https://www.amazon.com/sample-product",
  "bought_in_past_month": "200",
  "image_url": "https://images.amazon.com/sample-product.jpg",
  "last_updated": "2024-08-19",
  "amazon_fee": "$3.00",
  "fba_fee": "$4.00",
  "weight": "0.5kg",
  "category": "Electronics",
  "competitors": "15",
  "lowest_price": "$18.00"
}
```

## Excel出力

取得したJSONデータをExcelにエクスポートする方法:

```bash
python export_to_excel.py
```

Excelに出力されたデータは、カテゴリごとにフィルターや並び替えが可能です。

## 注意事項

- 頻繁にリクエストを行うとIPがブロックされる可能性があります。
- 必ず適度な間隔をあけて使用してください。
