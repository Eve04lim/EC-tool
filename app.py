# app.py - スレッドセーフ版 Webダッシュボード（拡張機能搭載）
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g, send_file
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import subprocess
import threading
from database import Database

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'ec-tracker-secret-key'

# リクエストごとにデータベース接続を取得する関数
def get_db():
    if not hasattr(g, 'db'):
        g.db = Database()
    return g.db

# リクエスト終了時にデータベース接続を閉じる
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

# テンプレートで使用するヘルパー関数
@app.context_processor
def utility_processor():
    def get_latest_price(product_id):
        db = get_db()
        return db.get_latest_price(product_id)
    
    return dict(get_latest_price=get_latest_price)

@app.route('/')
def index():
    db = get_db()
    products = db.get_all_products()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    
    product = db.get_product_by_id(product_id)
    if not product:
        flash('商品が見つかりません', 'error')
        return redirect(url_for('index'))
    
    history = db.get_product_price_history(product_id, limit=30)
    
    # 価格推移グラフを生成
    from analysis import PriceAnalyzer
    analyzer = PriceAnalyzer(db)
    chart_file = analyzer.generate_price_trend_chart(product_id)
    chart_url = f'/static/reports/price_trend_{product_id}.png' if chart_file else None
    
    return render_template(
        'product_detail.html', 
        product=product, 
        history=history,
        chart_url=chart_url
    )

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            result = subprocess.run(
                ['python', 'main.py', 'add', url],
                capture_output=True,
                text=True
            )
            if "商品を追加しました" in result.stdout:
                flash('商品を追加しました', 'success')
            else:
                flash(f'追加に失敗しました: {result.stderr}', 'error')
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

@app.route('/update')
def update_products():
    result = subprocess.run(
        ['python', 'main.py', 'update'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        flash('商品情報を更新しました', 'success')
    else:
        flash(f'更新に失敗しました: {result.stderr}', 'error')
    return redirect(url_for('index'))

@app.route('/export')
def export_to_sheets():
    result = subprocess.run(
        ['python', 'main.py', 'export'],
        capture_output=True,
        text=True
    )
    
    # スプレッドシートURLを抽出
    sheet_url = None
    for line in result.stdout.split('\n'):
        if "スプレッドシートURL" in line:
            sheet_url = line.split(': ')[1]
    
    if result.returncode == 0:
        if sheet_url:
            flash(f'Google Sheetsにエクスポートしました: <a href="{sheet_url}" target="_blank">スプレッドシートを開く</a>', 'success')
        else:
            flash('Google Sheetsにエクスポートしました', 'success')
    else:
        flash(f'エクスポートに失敗しました: {result.stderr}', 'error')
    return redirect(url_for('index'))

@app.route('/reports')
def reports():
    db = get_db()
    
    # 価格変動アラートレポート
    from analysis import PriceAnalyzer
    analyzer = PriceAnalyzer(db)
    alert_report = analyzer.generate_price_alerts_report(threshold_percent=5)
    
    # 商品価格比較
    products = db.get_all_products()
    product_ids = [p['id'] for p in products[:5]] if products else []  # 最初の5商品を比較
    comparison_report = analyzer.generate_price_comparison(product_ids) if product_ids else None
    
    return render_template(
        'reports.html',
        products=products,
        alert_report=alert_report[0] if alert_report else None,
        alert_count=alert_report[1] if alert_report else 0,
        comparison_report=comparison_report
    )

@app.route('/api/products')
def api_products():
    db = get_db()
    products = db.get_all_products()
    result = []
    for p in products:
        price = db.get_latest_price(p['id'])
        p_dict = dict(p)
        if price:
            p_dict['price'] = price['sale_price'] or price['regular_price']
            p_dict['in_stock'] = price['in_stock']
        result.append(p_dict)
    return jsonify(result)

# リポートファイルをダウンロード
@app.route('/reports/download/<path:filename>')
def download_report(filename):
    reports_dir = os.path.join(app.static_folder, 'reports')
    return send_file(os.path.join(reports_dir, filename))

# 価格予測機能
@app.route('/prediction/<int:product_id>')
def price_prediction(product_id):
    db = get_db()
    product = db.get_product_by_id(product_id)
    if not product:
        flash('商品が見つかりません', 'error')
        return redirect(url_for('index'))
    
    from prediction import PriceForecast
    forecaster = PriceForecast(db)
    
    # 14日間の価格予測
    success, result = forecaster.predict_future_prices(product_id, days=14)
    
    prediction_data = None
    if success:
        prediction_data = result
    
    return render_template(
        'price_prediction.html',
        product=product,
        prediction=prediction_data,
        chart_url=f'/static/reports/price_prediction_{product_id}.png' if success else None
    )

# 買い時分析
@app.route('/buy-timing/<int:product_id>')
def buy_timing(product_id):
    db = get_db()
    product = db.get_product_by_id(product_id)
    if not product:
        flash('商品が見つかりません', 'error')
        return redirect(url_for('index'))
    
    from buy_timing import BuyTimingAdvisor
    advisor = BuyTimingAdvisor(db)
    
    # 買い時分析
    analysis = advisor.analyze_product(product_id)
    
    return render_template(
        'buy_timing.html',
        product=product,
        analysis=analysis,
        chart_url=f'/static/reports/buy_timing_{product_id}.png' if analysis['success'] else None
    )

# マーケットインサイト
@app.route('/market-insights')
def market_insights():
    db = get_db()
    
    from market_insight import MarketInsight
    insight = MarketInsight(db)
    
    # プラットフォーム比較
    platform_success, platform_data = insight.generate_platform_comparison()
    
    # 価格トレンド（7日間、30日間）
    trend7_success, trend7_data = insight.generate_price_trend_overview(days=7)
    trend30_success, trend30_data = insight.generate_price_trend_overview(days=30)
    
    return render_template(
        'market_insights.html',
        platform_data=platform_data if platform_success else None,
        trend7_data=trend7_data if trend7_success else None,
        trend30_data=trend30_data if trend30_success else None
    )

# 在庫アラート登録
@app.route('/stock-alert/<int:product_id>', methods=['GET', 'POST'])
def stock_alert(product_id):
    db = get_db()
    product = db.get_product_by_id(product_id)
    if not product:
        flash('商品が見つかりません', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        from stock_alert import StockAlertSystem
        import config
        alert_system = StockAlertSystem(db, config)
        
        success = alert_system.subscribe(product_id, email, phone)
        if success:
            flash('在庫アラートに登録しました。商品が入荷したらお知らせします。', 'success')
        else:
            flash('登録に失敗しました。入力内容を確認してください。', 'error')
        
        return redirect(url_for('product_detail', product_id=product_id))
    
    return render_template('stock_alert.html', product=product)

# スケジュール管理画面
@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler_management():
    if request.method == 'POST':
        action = request.form.get('action')
        task_id = request.form.get('task_id')
        
        from scheduler import TaskScheduler
        import config
        scheduler = TaskScheduler(get_db(), config)
        
        if action == 'run':
            result = scheduler.run_task_now(task_id)
            if result:
                flash(f'タスク「{task_id}」を実行しました', 'success')
            else:
                flash(f'タスク「{task_id}」の実行に失敗しました', 'error')
        
        elif action == 'toggle':
            enabled = request.form.get('enabled') == 'true'
            result = scheduler.enable_task(task_id, enabled)
            if result:
                status = '有効' if enabled else '無効'
                flash(f'タスク「{task_id}」を{status}にしました', 'success')
            else:
                flash(f'タスク「{task_id}」の設定変更に失敗しました', 'error')
        
        return redirect(url_for('scheduler_management'))
    
    # タスク一覧を取得
    from scheduler import TaskScheduler
    import config
    scheduler = TaskScheduler(get_db(), config)
    tasks = scheduler.get_task_status()
    
    return render_template('scheduler.html', tasks=tasks)

# バックグラウンドサービス開始
def start_background_services():
    """バックグラウンドサービスを開始"""
    try:
        # 在庫アラートサービスを開始
        from stock_alert import StockAlertSystem
        import config
        
        db = Database()
        alert_system = StockAlertSystem(db, config)
        alert_system.start(interval_minutes=60)
        
        # スケジューラーを開始
        from scheduler import TaskScheduler
        scheduler = TaskScheduler(db, config)
        scheduler.start()
        
        print("バックグラウンドサービスを開始しました")
    except Exception as e:
        print(f"バックグラウンドサービスの開始に失敗しました: {e}")

# Flaskサーバー起動時にバックグラウンドサービスを開始
if __name__ == '__main__':
    # 別スレッドでバックグラウンドサービスを開始
    bg_thread = threading.Thread(target=start_background_services)
    bg_thread.daemon = True
    bg_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)