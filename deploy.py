# deploy.py - デプロイスクリプト
import os
import subprocess
import argparse
import sys
import shutil
import stat

def create_dirs():
    """必要なディレクトリを作成"""
    dirs = ["logs", "reports", "static", "templates"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("✅ ディレクトリ作成完了")

def install_packages():
    """必要なパッケージをインストール"""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ パッケージインストール完了")

def create_service_file(is_systemd):
    """サービスファイルを作成"""
    if is_systemd:
        # Systemdサービスファイルを作成（Linuxサーバー用）
        service_content = f"""[Unit]
Description=EC Price Tracker Service
After=network.target

[Service]
User={os.getlogin()}
WorkingDirectory={os.getcwd()}
ExecStart={sys.executable} app.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ec-tracker

[Install]
WantedBy=multi-user.target
"""
        service_file = "/tmp/ec-tracker.service"
        with open(service_file, "w") as f:
            f.write(service_content)
        
        print(f"サービスファイルを作成しました: {service_file}")
        print("以下のコマンドでサービスをインストールできます:")
        print(f"sudo cp {service_file} /etc/systemd/system/")
        print("sudo systemctl daemon-reload")
        print("sudo systemctl enable ec-tracker")
        print("sudo systemctl start ec-tracker")
    else:
        # Windowsバッチファイルを作成
        batch_content = f"""@echo off
cd {os.getcwd()}
{sys.executable} app.py
"""
        batch_file = "start_service.bat"
        with open(batch_file, "w") as f:
            f.write(batch_content)
        
        print(f"✅ 起動スクリプト作成完了: {batch_file}")

def create_cron_jobs(is_linux):
    """定期実行のcronジョブを設定"""
    if is_linux:
        # Linuxのcrontab用
        cron_content = f"""# EC Price Tracker 定期実行設定
# 毎日6時に商品情報を更新
0 6 * * * cd {os.getcwd()} && {sys.executable} main.py update

# 毎週月曜日の朝9時にレポートを生成
0 9 * * 1 cd {os.getcwd()} && {sys.executable} -c "from assistant import ECAssistant; from database import Database; assistant = ECAssistant(Database()); assistant.generate_weekly_report(); print('週次レポート生成完了')"
"""
        cron_file = "crontab.txt"
        with open(cron_file, "w") as f:
            f.write(cron_content)
        
        print(f"✅ crontab設定ファイル作成完了: {cron_file}")
        print("以下のコマンドでcrontabに追加できます:")
        print(f"crontab {cron_file}")
    else:
        # Windowsのタスクスケジューラ用バッチファイル
        update_batch = "update_data.bat"
        with open(update_batch, "w") as f:
            f.write(f"""@echo off
cd {os.getcwd()}
{sys.executable} main.py update
""")
        
        report_batch = "generate_report.bat"
        with open(report_batch, "w") as f:
            f.write(f"""@echo off
cd {os.getcwd()}
{sys.executable} -c "from assistant import ECAssistant; from database import Database; assistant = ECAssistant(Database()); assistant.generate_weekly_report(); print('週次レポート生成完了')"
""")
        
        print(f"✅ スケジュールタスク用バッチファイル作成完了:")
        print(f"  - {update_batch} (毎日の更新用)")
        print(f"  - {report_batch} (週次レポート用)")
        print("Windowsのタスクスケジューラで上記バッチファイルを定期実行するよう設定してください。")

def main():
    parser = argparse.ArgumentParser(description="EC価格追跡ツール デプロイスクリプト")
    parser.add_argument("--platform", choices=["linux", "windows"], default="windows", help="デプロイプラットフォーム")
    args = parser.parse_args()
    
    is_linux = args.platform == "linux"
    
    print("EC価格追跡ツール デプロイを開始します...")
    
    # 必要なディレクトリを作成
    create_dirs()
    
    # パッケージをインストール
    install_packages()
    
    # サービスファイルを作成
    create_service_file(is_linux)
    
    # crontabを設定
    create_cron_jobs(is_linux)
    
    print("\nデプロイが完了しました！")
    print("Webダッシュボードを起動するには:")
    if is_linux:
        print(f"  {sys.executable} app.py")
    else:
        print("  start_service.bat をダブルクリックするか、コマンドプロンプトから実行してください。")
    
    print("\nお疲れ様でした！")

if __name__ == "__main__":
    main()