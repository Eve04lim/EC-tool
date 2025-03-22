# EC商品価格追跡ツール

## 概要

このプロジェクトは、ECサイト（Amazon、楽天市場、Yahoo!ショッピング）の商品価格と在庫状況を自動的に追跡し、価格変動を分析するシステムです。ユーザーは関心のある商品のURLを登録するだけで、価格変動の通知や最適な購入タイミングの提案を受けることができます。

## 主な機能

- 複数のECサイト（Amazon、楽天、Yahoo!ショッピング）の商品情報収集
- 価格履歴のグラフ表示と分析
- 在庫状況の追跡と通知
- 価格予測と「買い時」分析
- プラットフォーム比較分析
- Google Sheetsへのデータエクスポート機能
- メール・Slack・LINE通知機能

## 技術スタック

- **バックエンド**: Python、Flask
- **データベース**: PostgreSQL (Supabase)、SQLite (開発環境)
- **データ収集**: Selenium、BeautifulSoup4、Requests
- **データ分析**: Pandas、NumPy、Scikit-learn
- **可視化**: Matplotlib、Seaborn
- **デプロイ**: Heroku

## アーキテクチャ

本システムは以下の2つの主要コンポーネントで構成されています：

1. **ウェブアプリケーション**: ユーザーインターフェース、データ分析、通知管理を担当
2. **データ収集スクリプト**: ECサイトから商品情報を収集（別プロセスとして実行）

この設計により、リソース消費の大きいスクレイピング処理をメインアプリケーションから分離し、Herokuのスラグサイズ制限に対応しています。

## データベース

当初はSQLiteを使用していましたが、拡張性と信頼性の向上のためSupabase（PostgreSQL）に移行しました。これにより：

- クラウド上の安定したデータ管理
- リアルタイムデータ更新
- 複数デバイスからのアクセス
- 自動バックアップ

が実現できました。

## インストール方法

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/ec-price-tracker.git
cd ec-price-tracker

# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して必要な情報を入力

# アプリケーションの実行
python app.py