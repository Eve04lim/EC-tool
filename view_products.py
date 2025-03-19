# view_products.py
import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

def load_products():
    try:
        conn = sqlite3.connect('ec_tracker.db')
        products_df = pd.read_sql_query("SELECT * FROM products", conn)
        
        # 表示を更新
        tree.delete(*tree.get_children())
        for idx, row in products_df.iterrows():
            tree.insert("", "end", values=(
                row['id'], 
                row['name'], 
                row['platform'], 
                row['product_code'], 
                row['url']
            ))
        
        status_label.config(text=f"商品数: {len(products_df)}")
        
        conn.close()
    except Exception as e:
        status_label.config(text=f"エラー: {e}")

def view_price_history():
    selected = tree.selection()
    if not selected:
        return
    
    item = tree.item(selected[0])
    product_id = item['values'][0]
    
    try:
        conn = sqlite3.connect('ec_tracker.db')
        
        # 商品情報を取得
        product_df = pd.read_sql_query(f"SELECT * FROM products WHERE id = {product_id}", conn)
        
        # 価格履歴を取得
        history_df = pd.read_sql_query(
            f"SELECT * FROM price_history WHERE product_id = {product_id} ORDER BY fetched_at DESC", 
            conn
        )
        
        # ポップアップウィンドウを作成
        popup = tk.Toplevel()
        popup.title(f"商品詳細 - {product_df.iloc[0]['name']}")
        popup.geometry("600x400")
        
        # 商品情報の表示
        info_frame = ttk.LabelFrame(popup, text="商品情報")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        for col in product_df.columns:
            if col not in ['id', 'created_at', 'updated_at']:
                frame = ttk.Frame(info_frame)
                frame.pack(fill="x", padx=5, pady=2)
                ttk.Label(frame, text=f"{col}:", width=15).pack(side="left")
                ttk.Label(frame, text=str(product_df.iloc[0][col])).pack(side="left")
        
        # 価格履歴の表示
        history_frame = ttk.LabelFrame(popup, text="価格履歴")
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        history_tree = ttk.Treeview(history_frame, columns=(
            "fetched_at", "regular_price", "sale_price", "in_stock"
        ))
        history_tree.heading("fetched_at", text="取得日時")
        history_tree.heading("regular_price", text="通常価格")
        history_tree.heading("sale_price", text="セール価格")
        history_tree.heading("in_stock", text="在庫状況")
        history_tree["show"] = "headings"  # 最初の列（ID）を非表示
        
        for idx, row in history_df.iterrows():
            history_tree.insert("", "end", values=(
                row['fetched_at'],
                f"¥{row['regular_price']:,.0f}" if pd.notna(row['regular_price']) else "-",
                f"¥{row['sale_price']:,.0f}" if pd.notna(row['sale_price']) else "-",
                "在庫あり" if row['in_stock'] else "在庫なし"
            ))
        
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        history_tree.pack(side="left", fill="both", expand=True)
        
        conn.close()
    except Exception as e:
        status_label.config(text=f"エラー: {e}")

# GUIの作成
root = tk.Tk()
root.title("EC商品追跡ツール - 商品一覧")
root.geometry("800x500")

# ツールバー
toolbar = ttk.Frame(root)
toolbar.pack(fill="x", padx=5, pady=5)

refresh_btn = ttk.Button(toolbar, text="更新", command=load_products)
refresh_btn.pack(side="left", padx=5)

# 商品リスト
tree_frame = ttk.Frame(root)
tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

tree = ttk.Treeview(tree_frame, columns=("id", "name", "platform", "product_code", "url"))
tree.heading("id", text="ID")
tree.heading("name", text="商品名")
tree.heading("platform", text="プラットフォーム")
tree.heading("product_code", text="商品コード")
tree.heading("url", text="URL")
tree.column("id", width=50)
tree.column("name", width=300)
tree.column("platform", width=100)
tree.column("product_code", width=100)
tree.column("url", width=250)

tree["show"] = "headings"  # 最初の列（ID）を非表示

scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
tree.pack(side="left", fill="both", expand=True)

# 商品詳細表示ボタン
detail_btn = ttk.Button(root, text="価格履歴を表示", command=view_price_history)
detail_btn.pack(pady=5)

# ダブルクリックでも詳細表示
tree.bind("<Double-1>", lambda e: view_price_history())

# ステータスバー
status_label = ttk.Label(root, text="")
status_label.pack(anchor="w", padx=10, pady=5)

# 初期データ読み込み
load_products()

root.mainloop()