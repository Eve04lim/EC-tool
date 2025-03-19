# scheduler.py - 自動化・バッチ処理機能
import time
import threading
import schedule
import logging
import os
from datetime import datetime, timedelta
import pandas as pd
import shutil
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import sqlite3
import zipfile

class TaskScheduler:
    """自動化・バッチ処理機能"""
    
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)
        self.tasks = {}
        self.last_run = {}
        
        # デフォルトタスクの設定
        self._setup_default_tasks()
    
    def _setup_default_tasks(self):
        """デフォルトタスクを設定"""
        self.add_task("update_all", self._update_all_products, "daily", "09:00")
        self.add_task("export_sheets", self._export_to_sheets, "daily", "09:30")
        self.add_task("backup_db", self._backup_database, "weekly", "monday 01:00")
        self.add_task("clean_old_reports", self._clean_old_reports, "weekly", "sunday 03:00")
        self.add_task("generate_weekly_report", self._generate_weekly_report, "weekly", "monday 10:00")
    
    def add_task(self, task_id, func, frequency, time_spec, *args, **kwargs):
        """タスクを追加"""
        if task_id in self.tasks:
            self.logger.warning(f"Task {task_id} already exists. Updating.")
        
        self.tasks[task_id] = {
            "function": func,
            "frequency": frequency,
            "time_spec": time_spec,
            "args": args,
            "kwargs": kwargs,
            "enabled": True
        }
        
        self.logger.info(f"Task added: {task_id} ({frequency} at {time_spec})")
        return True
    
    def remove_task(self, task_id):
        """タスクを削除"""
        if task_id not in self.tasks:
            return False
        
        del self.tasks[task_id]
        self.logger.info(f"Task removed: {task_id}")
        return True
    
    def enable_task(self, task_id, enabled=True):
        """タスクの有効/無効を切り替え"""
        if task_id not in self.tasks:
            return False
        
        self.tasks[task_id]["enabled"] = enabled
        status = "enabled" if enabled else "disabled"
        self.logger.info(f"Task {task_id} {status}")
        return True
    
    def start(self):
        """スケジューラを開始"""
        if self.running:
            return False
        
        self.running = True
        
        def run_scheduler():
            # スケジュール設定
            for task_id, task in self.tasks.items():
                if not task["enabled"]:
                    continue
                
                job_func = lambda t=task_id: self._run_task(t)
                
                if task["frequency"] == "hourly":
                    schedule.every().hour.at(task["time_spec"]).do(job_func)
                elif task["frequency"] == "daily":
                    schedule.every().day.at(task["time_spec"]).do(job_func)
                elif task["frequency"] == "weekly":
                    day, time_value = task["time_spec"].split()
                    getattr(schedule.every(), day).at(time_value).do(job_func)
                elif task["frequency"] == "monthly":
                    schedule.every().month.at(task["time_spec"]).do(job_func)
            
            self.logger.info("Scheduler started")
            
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        # 別スレッドでスケジューラーを実行
        self.thread = threading.Thread(target=run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        
        return True
    
    def stop(self):
        """スケジューラを停止"""
        if not self.running:
            return False
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
            self.thread = None
        
        # 全てのジョブをクリア
        schedule.clear()
        
        self.logger.info("Scheduler stopped")
        return True
    
    def _run_task(self, task_id):
        """タスクを実行"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if not task["enabled"]:
            return False
        
        self.logger.info(f"Running task: {task_id}")
        
        try:
            result = task["function"](*task["args"], **task["kwargs"])
            self.last_run[task_id] = {
                "time": datetime.now(),
                "success": True,
                "result": result
            }
            self.logger.info(f"Task {task_id} completed successfully")
            return result
        except Exception as e:
            self.last_run[task_id] = {
                "time": datetime.now(),
                "success": False,
                "error": str(e)
            }
            self.logger.error(f"Error running task {task_id}: {e}")
            return False
    
    def get_task_status(self, task_id=None):
        """タスクのステータスを取得"""
        if task_id:
            if task_id not in self.tasks:
                return None
            
            status = {
                "id": task_id,
                "enabled": self.tasks[task_id]["enabled"],
                "frequency": self.tasks[task_id]["frequency"],
                "time_spec": self.tasks[task_id]["time_spec"]
            }
            
            if task_id in self.last_run:
                status.update({
                    "last_run": self.last_run[task_id]["time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "success": self.last_run[task_id]["success"]
                })
            
            return status
        else:
            # 全タスクのステータスを返す
            return [self.get_task_status(t) for t in self.tasks]
    
    def run_task_now(self, task_id):
        """タスクを即時実行"""
        if task_id not in self.tasks:
            return False
        
        return self._run_task(task_id)
    
    # タスク実装
    def _update_all_products(self):
        """全商品の情報を更新"""
        try:
            import subprocess
            result = subprocess.run(
                ['python', 'main.py', 'update'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error(f"Update failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error updating products: {e}")
            return False
    
    def _export_to_sheets(self):
        """Google Sheetsにエクスポート"""
        try:
            import subprocess
            result = subprocess.run(
                ['python', 'main.py', 'export'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.logger.error(f"Export failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error exporting to sheets: {e}")
            return False
    
    def _backup_database(self):
        """データベースのバックアップ"""
        try:
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # 日付をファイル名に含める
            today = datetime.now().strftime("%Y%m%d")
            db_file = "ec_tracker.db"
            backup_file = os.path.join(backup_dir, f"ec_tracker_{today}.db")
            
            # データベースのバックアップ
            if os.path.exists(db_file):
                shutil.copy2(db_file, backup_file)
                
                # バックアップファイルを圧縮
                with zipfile.ZipFile(f"{backup_file}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(backup_file, os.path.basename(backup_file))
                
                # 圧縮後に元のバックアップを削除
                os.remove(backup_file)
                
                self.logger.info(f"Database backup created: {backup_file}.zip")
                
                # 古いバックアップを削除（30日以上前）
                self._clean_old_backups(30)
                
                return True
            else:
                self.logger.error(f"Database file not found: {db_file}")
                return False
        except Exception as e:
            self.logger.error(f"Error creating database backup: {e}")
            return False
    
    def _clean_old_backups(self, days=30):
        """古いバックアップを削除"""
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                return False
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for filename in os.listdir(backup_dir):
                if filename.endswith(".zip") and filename.startswith("ec_tracker_"):
                    # ファイル名から日付を抽出 (ec_tracker_20230401.db.zip)
                    try:
                        date_str = filename.split("_")[2].split(".")[0]
                        file_date = datetime.strptime(date_str, "%Y%m%d")
                        
                        if file_date < cutoff_date:
                            file_path = os.path.join(backup_dir, filename)
                            os.remove(file_path)
                            self.logger.info(f"Removed old backup: {filename}")
                    except (IndexError, ValueError):
                        continue
            
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning old backups: {e}")
            return False
    
    def _clean_old_reports(self, days=30):
        """古いレポートファイルを削除"""
        try:
            reports_dir = os.path.join("static", "reports")
            if not os.path.exists(reports_dir):
                return False
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for filename in os.listdir(reports_dir):
                file_path = os.path.join(reports_dir, filename)
                
                # ファイルの最終更新時間をチェック
                if os.path.isfile(file_path):
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if mod_time < cutoff_date:
                        # ただし、重要なファイルは削除しない
                        if not (filename.startswith("platform_comparison") or 
                                filename.startswith("price_trends_")):
                            os.remove(file_path)
                            self.logger.info(f"Removed old report: {filename}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning old reports: {e}")
            return False
    
    def _generate_weekly_report(self):
        """週次レポートを生成して送信"""
        try:
            from analysis import PriceAnalyzer
            
            # 価格アラートレポート
            analyzer = PriceAnalyzer(self.db)
            alert_report = analyzer.generate_price_alerts_report(threshold_percent=5)
            
            # レポートファイルの準備
            report_dir = os.path.join("static", "reports")
            os.makedirs(report_dir, exist_ok=True)
            
            today = datetime.now().strftime("%Y%m%d")
            report_file = os.path.join(report_dir, f"weekly_report_{today}.html")
            
            # HTMLレポートの内容
            html = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
                    .section {{ margin: 20px 0; padding: 15px; border: 1px solid #eee; border-radius: 5px; }}
                    .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; font-size: 0.8em; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>EC商品追跡 週次レポート</h1>
                    <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
                </div>
                
                <div class="section">
                    <h2>サマリー</h2>
                    <p>
                        過去7日間の価格変動をまとめたレポートです。
                        このレポートは毎週月曜日に自動生成されます。
                    </p>
                </div>
            """
            
            # 価格アラートセクション
            if alert_report:
                alert_file, alert_count = alert_report
                html += f"""
                <div class="section">
                    <h2>価格変動アラート</h2>
                    <p>過去7日間で5%以上の価格変動があった商品が{alert_count}件あります。</p>
                    <p><a href="{alert_file}">詳細レポートを表示</a></p>
                </div>
                """
            
            # フッター
            html += """
                <div class="footer">
                    <p>このレポートはEC商品追跡ツールにより自動生成されました。</p>
                </div>
            </body>
            </html>
            """
            
            # ファイルに保存
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            # メールで送信
            self._send_report_email(report_file)
            
            self.logger.info(f"Weekly report generated: {report_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating weekly report: {e}")
            return False
    
    def _send_report_email(self, report_file):
        """レポートをメールで送信"""
        try:
            if not os.path.exists(report_file):
                return False
            
            # メール設定が不足している場合はスキップ
            if not hasattr(self.config, 'EMAIL_USER') or not self.config.EMAIL_USER:
                self.logger.warning("Email settings are missing, skipping email sending")
                return False
            
            message = MIMEMultipart()
            message['From'] = self.config.EMAIL_USER
            message['To'] = ", ".join(self.config.EMAIL_TO) if isinstance(self.config.EMAIL_TO, list) else self.config.EMAIL_TO
            message['Subject'] = f"EC商品追跡 週次レポート {datetime.now().strftime('%Y-%m-%d')}"
            
            # HTML本文
            with open(report_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            message.attach(MIMEText(html_content, 'html'))
            
            # 添付ファイル（HTMLレポートも添付）
            with open(report_file, 'r', encoding='utf-8') as f:
                attachment = MIMEApplication(f.read(), _subtype='html')
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(report_file))
                message.attach(attachment)
            
            # メール送信
            with smtplib.SMTP(self.config.EMAIL_SERVER, self.config.EMAIL_PORT) as server:
                server.starttls()
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(message)
            
            self.logger.info(f"Weekly report email sent")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending report email: {e}")
            return False