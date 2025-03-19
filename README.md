# ECサイト価格・在庫追跡ツール

このツールは、Amazon.co.jp、楽天市場、Yahoo!ショッピングの商品価格と在庫状況を自動的に追跡し、価格変動や在庫状況の変化があった場合に通知を送信するPythonアプリケーションです。

## 機能

- 複数ECサイト（Amazon.co.jp、楽天市場、Yahooショッピング）の商品情報を追跡
- 定期的に商品データを自動収集し、データベースに保存
- 価格変動（10%以上）や在庫状況の変化を検知して通知（メール・Slack）
- 収集データをGoogle Spreadsheetに自動エクスポート
- 商品の一括登録と管理

## システム要件

- Python 3.7以上
- Google SheetsへのエクスポートにはGoogle Cloud Platform（GCP）アカウントとAPIキーが必要
- Slack通知にはSlack APIのWebhook URLが必要
- メール通知にはSMTPサーバーへのアクセス情報が必要

## インストール

1. リポジトリをクローンまたはダウンロード:

```
git clone [リポジトリURL]
cd ec-tracker
```

2. セットアップスクリプトを実行:

```
python setup.py
```

セットアップスクリプトは以下を実行します:
- 必要なPythonパッケージのインストール
- 環境設定ファイル(.env)の作成
- Google Sheets、Slack、メール通知、定期実行の設定手順の表示

## 設定

`.env` ファイルを編集して、以下の設定を行います:

- データベース設定（SQLiteまたはPostgreSQL）
- 通知設定（メール・Slack）
- Google Sheets連携設定
- ロギング設定
- プロキシ設定（オプション）

## 使用方法

### 商品の追加

単一商品の追加:

```
python main.py add https://www.amazon.co.jp/dp/XXXXXXXXXX
```

複数商品の一括追加:

```
python main.py add-bulk products.txt
```

`products.txt` は各行に1つの商品URLを含むテキストファイルです。

### 商品情報の更新

すべての商品を更新:

```
python main.py update
```

特定の商品を更新:

```
python main.py update --id 1
```

### Google Sheetsへのエクスポート

```
python main.py export
```

### 定期実行の設定

指定した間隔で自動的に更新を実行:

```
python main.py schedule --interval 12  # 12時間ごとに更新
```

## 定期実行の設定（cron）

Linuxサーバーでcronを使用して定期実行する場合の例:

```
# 6時間ごとに実行（0時、6時、12時、18時）
0 */6 * * * cd /path/to/ec-tracker && /usr/bin/python3 main.py update
```

## Google Sheets連携のセットアップ

1. Google Cloud Platform (GCP)でプロジェクトを作成
2. Google Sheets APIを有効化
3. OAuth 2.0クライアントIDを作成
4. 認証情報（credentials.json）をダウンロードし、プロジェクトディレクトリに配置
5. `.env`ファイルの`ENABLE_GSHEETS`を`True`に設定し、`GSHEETS_SPREADSHEET_ID`にスプレッドシートIDを設定

## 注意事項

- ECサイトの利用規約に違反しないよう、リクエスト間隔を適切に設定してください
- スクレイピングの際はサーバーに負荷をかけないよう配慮してください
- 個人利用の範囲内でお使いください

## ファイル構成

- `main.py` - メインアプリケーション
- `config.py` - 設定モジュール
- `database.py` - データベース操作モジュール
- `scrapers.py` - ECサイトスクレイピングモジュール
- `notifier.py` - 通知モジュール
- `gsheets.py` - Google Sheets連携モジュール
- `setup.py` - セットアップスクリプト
- `.env.example` - 環境変数設定例
- `products.txt` - 商品URLリスト例

## 開発・貢献

バグ報告や機能リクエストは、Issueを作成してください。プルリクエストも歓迎します。

## ライセンス

[適切なライセンス情報]