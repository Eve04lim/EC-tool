# ECサイト価格・在庫追跡ツール

![バージョン](https://img.shields.io/badge/バージョン-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.7%2B-brightgreen)
![ライセンス](https://img.shields.io/badge/ライセンス-MIT-green)

ECサイト価格・在庫追跡ツールは、Amazon、楽天市場、Yahoo!ショッピングなどの主要ECサイトの商品価格と在庫状況を自動的に追跡し、分析するWebアプリケーションです。価格変動や在庫状況の変化を通知し、最適な購入タイミングを提案します。

## 主な機能

- **マルチECサイト対応**: Amazon、楽天市場、Yahoo!ショッピングの商品を一元管理
- **自動価格・在庫追跡**: 定期的に最新情報を取得し、データベースに保存
- **価格変動アラート**: 価格が10%以上変動した場合に通知
- **在庫アラート**: 在庫状況に変化があった場合に通知
- **価格推移グラフ**: 商品ごとの価格推移を視覚化
- **価格予測**: 機械学習を活用した将来価格の予測
- **買い時判定**: 現在が購入に適した時期かを分析
- **マーケットインサイト**: ECサイト間の価格比較や市場傾向の分析
- **Google Sheets連携**: 収集データを自動的にスプレッドシートに転送

## 使用技術

- **バックエンド**:
  - Python 3.7+
  - Flask (Webフレームワーク)
  - SQLite/PostgreSQL (データベース)
  - Beautiful Soup/Selenium (Webスクレイピング)
  - Pandas/NumPy (データ分析)
  - scikit-learn (機械学習)
  - Google Sheets API (スプレッドシート連携)

- **フロントエンド**:
  - HTML5/CSS3
  - Bootstrap 5 (UIフレームワーク)
  - JavaScript
  - Chart.js (グラフ描画)

- **その他**:
  - Schedule (自動化)
  - SMTP/Slack API (通知)
  - Matplotlib/Seaborn (データ可視化)

## インストール方法

### 前提条件
- Python 3.7以上
- pip (Pythonパッケージマネージャー)
- Chrome/Chromium (Seleniumで使用)

### セットアップ手順

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/ec-tracker.git
cd ec-tracker