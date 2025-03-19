#!/usr/bin/env python3
# setup.py - セットアップスクリプト
import os
import sys
import subprocess
import shutil
import argparse

def check_python_version():
    """Pythonバージョンをチェック（3.7以上）"""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        print(f"Python 3.7以上が必要です。現在のバージョン: {major}.{minor}")
        sys.exit(1)
    print(f"Python {major}.{minor} ✓")

def install_requirements():
    """必要なパッケージをインストール"""
    print("必要なパッケージをインストールしています...")
    requirements = [
        "requests",
        "beautifulsoup4",
        "selenium",
        "webdriver-manager",
        "pandas",
        "python-dotenv",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "schedule",
        "psycopg2-binary"
    ]
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install"] + requirements, check=True)
        print("パッケージのインストールが完了しました ✓")
    except subprocess.CalledProcessError as e:
        print(f"パッケージのインストールに失敗しました: {e}")
        sys.exit(1)

def create_env_file():
    """環境設定ファイルを作成"""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print(".env ファイルを作成しました。必要に応じて設定を変更してください ✓")
        else:
            print(".env.example ファイルが見つかりません。手動で .env ファイルを作成してください")
    else:
        print(".env ファイルは既に存在します ✓")

def setup_google_sheets():
    """Google Sheets APIの設定ガイド"""
    print("\nGoogle Sheets連携のセットアップ手順:")
    print("1. Google Cloud Consoleで新しいプロジェクトを作成")
    print("2. Google Sheets APIを有効化")
    print("3. 認証情報を作成（OAuthクライアントID）")
    print("4. credentials.jsonをダウンロードし、このディレクトリに配置")
    print("5. .envファイルのENABLE_GSHEETSをTrueに設定")
    print("6. .envファイルのGSHEETS_SPREADSHEET_IDにスプレッドシートIDを設定")
    print("   （スプレッドシートURLの https://docs.google.com/spreadsheets/d/[ここの部分]/edit から取得）")

def setup_slack():
    """Slack Webhookの設定ガイド"""
    print("\nSlack通知のセットアップ手順:")
    print("1. Slackワークスペースでアプリを作成（https://api.slack.com/apps）")
    print("2. 「Incoming Webhooks」機能を有効化")
    print("3. Webhook URLを作成し、コピー")
    print("4. .envファイルのENABLE_SLACKをTrueに設定")
    print("5. .envファイルのSLACK_WEBHOOK_URLにWebhook URLを設定")

def setup_email():
    """メール通知の設定ガイド"""
    print("\nメール通知のセットアップ手順:")
    print("1. .envファイルのENABLE_EMAILをTrueに設定")
    print("2. .envファイルのEMAIL_*設定を更新")
    print("   - GmailをSMTPサーバーとして使用する場合、「アプリパスワード」の設定が必要")
    print("   - Googleアカウントで2段階認証を有効にし、アプリパスワードを生成")
    print("   - 生成したパスワードをEMAIL_PASSWORDに設定")

def setup_cron():
    """Cronジョブの設定ガイド"""
    script_path = os.path.abspath("main.py")
    
    print("\nCron定期実行のセットアップ手順:")
    print("1. crontabを編集: crontab -e")
    print("2. 以下の行を追加（例: 6時間ごとに実行）")
    print(f"   0 */6 * * * cd {os.getcwd()} && {sys.executable} {script_path} update")
    print("")
    print("Windowsの場合はタスクスケジューラを使用してください")

def main():
    parser = argparse.ArgumentParser(description="ECサイト価格・在庫追跡ツールのセットアップ")
    parser.add_argument("--skip-install", action="store_true", help="パッケージのインストールをスキップ")
    args = parser.parse_args()
    
    print("ECサイト価格・在庫追跡ツールのセットアップを開始します")
    print("-" * 60)
    
    check_python_version()
    
    if not args.skip_install:
        install_requirements()
    else:
        print("パッケージのインストールをスキップします")
    
    create_env_file()
    
    print("\n追加の設定ガイド:")
    setup_google_sheets()
    setup_slack()
    setup_email()
    setup_cron()
    
    print("-" * 60)
    print("セットアップが完了しました！")
    print("使用方法: python main.py --help")

if __name__ == "__main__":
    main()