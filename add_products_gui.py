import tkinter as tk
from tkinter import ttk  # このインポートを追加
from tkinter import messagebox, scrolledtext, filedialog
import subprocess
import threading
import os
import sys

def add_products():
    urls = urls_text.get("1.0", tk.END).strip().split('\n')
    urls = [url.strip() for url in urls if url.strip() and not url.strip().startswith('#')]
    
    if not urls:
        messagebox.showwarning("警告", "URLが入力されていません")
        return
    
    progress_label.config(text="追加中...")
    status_text.delete("1.0", tk.END)
    
    def run_process():
        success_count = 0
        for i, url in enumerate(urls):
            status_text.insert(tk.END, f"処理中 ({i+1}/{len(urls)}): {url}\n")
            status_text.see(tk.END)
            status_text.update()
            
            # main.pyを呼び出して商品を追加
            result = subprocess.run(
                [sys.executable, "main.py", "add", url],
                capture_output=True,
                text=True
            )
            
            # 結果を表示
            if "商品を追加しました" in result.stdout:
                success_count += 1
                status = f"✓ 成功: {url}\n"
            else:
                status = f"✗ 失敗: {url}\n{result.stderr}\n"
            
            status_text.insert(tk.END, status)
            status_text.see(tk.END)
        
        progress_label.config(text=f"完了: {success_count}/{len(urls)}件の商品を追加しました")
    
    # 別スレッドで実行
    thread = threading.Thread(target=run_process)
    thread.daemon = True
    thread.start()

def load_from_file():
    filename = filedialog.askopenfilename(
        title="URLリストファイルを選択",
        filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
    )
    
    if not filename:
        return
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        urls_text.delete("1.0", tk.END)
        urls_text.insert("1.0", "\n".join(urls))
        messagebox.showinfo("情報", f"{len(urls)}件のURLを読み込みました")
    except Exception as e:
        messagebox.showerror("エラー", f"ファイル読み込みエラー: {e}")

def run_amazon_collector():
    def launch_collector():
        progress_label.config(text="Amazon商品収集ツールを起動中...")
        status_text.delete("1.0", tk.END)
        status_text.insert(tk.END, "Amazon商品収集ツールを実行中...\n")
        status_text.see(tk.END)
        
        try:
            # 収集モードを取得
            mode = collector_mode_var.get()
            
            # 各モードに応じたパラメータを設定
            cmd = [sys.executable, "amazon_collector.py", "--mode", mode]
            
            if mode == "search":
                term = search_term_entry.get().strip()
                if not term:
                    status_text.insert(tk.END, "エラー: 検索キーワードが入力されていません\n")
                    progress_label.config(text="エラー: 検索キーワードが必要です")
                    return
                cmd.extend(["--term", term])
            
            elif mode == "category":
                term = category_url_entry.get().strip()
                if not term:
                    status_text.insert(tk.END, "エラー: カテゴリURLが入力されていません\n")
                    progress_label.config(text="エラー: カテゴリURLが必要です")
                    return
                cmd.extend(["--term", term])
            
            elif mode == "bestsellers":
                category = bestseller_category_entry.get().strip()
                if category:
                    cmd.extend(["--category", category])
            
            # 最大件数を追加
            max_items = max_items_spinbox.get()
            cmd.extend(["--max", max_items])
            
            # サブプロセスを実行
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 出力を読み取り
            for line in process.stdout:
                status_text.insert(tk.END, line)
                status_text.see(tk.END)
                
                # 確認メッセージが来たら自動的に「y」を入力
                if "これらの商品を追跡リストに追加しますか？" in line:
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    status_text.insert(tk.END, "自動応答: y (はい)\n")
                    status_text.see(tk.END)
            
            # エラー出力を確認
            for line in process.stderr:
                status_text.insert(tk.END, f"エラー: {line}")
                status_text.see(tk.END)
            
            process.wait()
            
            if process.returncode == 0:
                progress_label.config(text="Amazon商品収集が完了しました")
            else:
                progress_label.config(text=f"Amazon商品収集中にエラーが発生しました (コード: {process.returncode})")
        
        except Exception as e:
            status_text.insert(tk.END, f"エラー: {e}\n")
            progress_label.config(text="エラーが発生しました")
            
    # 別スレッドで実行
    thread = threading.Thread(target=launch_collector)
    thread.daemon = True
    thread.start()

# GUIの作成
root = tk.Tk()
root.title("EC商品追跡ツール - 商品登録")
root.geometry("700x700")

notebook = tk.ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# 手動追加タブ
manual_frame = tk.Frame(notebook)
notebook.add(manual_frame, text="手動追加")

manual_label = tk.Label(manual_frame, text="追加したい商品のURLを1行に1つずつ入力してください:")
manual_label.pack(anchor="w", pady=(10, 5))

urls_text = scrolledtext.ScrolledText(manual_frame, height=10)
urls_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

button_frame = tk.Frame(manual_frame)
button_frame.pack(fill=tk.X, pady=(0, 10))

load_button = tk.Button(button_frame, text="ファイルから読み込む", command=load_from_file)
load_button.pack(side=tk.LEFT, padx=(0, 10))

add_button = tk.Button(button_frame, text="商品を追加", command=add_products)
add_button.pack(side=tk.LEFT)

# Amazon収集タブ
amazon_frame = tk.Frame(notebook)
notebook.add(amazon_frame, text="Amazon商品収集")

collector_frame = tk.ttk.LabelFrame(amazon_frame, text="Amazon商品収集設定")
collector_frame.pack(fill=tk.X, padx=10, pady=10)

# 収集モード選択
mode_frame = tk.Frame(collector_frame)
mode_frame.pack(fill=tk.X, padx=10, pady=5)

mode_label = tk.Label(mode_frame, text="収集モード:")
mode_label.pack(side=tk.LEFT, padx=(0, 10))

collector_mode_var = tk.StringVar(value="bestsellers")
bestsellers_radio = tk.Radiobutton(mode_frame, text="ベストセラー", variable=collector_mode_var, value="bestsellers")
bestsellers_radio.pack(side=tk.LEFT, padx=(0, 10))

search_radio = tk.Radiobutton(mode_frame, text="検索", variable=collector_mode_var, value="search")
search_radio.pack(side=tk.LEFT, padx=(0, 10))

category_radio = tk.Radiobutton(mode_frame, text="カテゴリ", variable=collector_mode_var, value="category")
category_radio.pack(side=tk.LEFT)

# 検索キーワード
search_frame = tk.Frame(collector_frame)
search_frame.pack(fill=tk.X, padx=10, pady=5)

search_label = tk.Label(search_frame, text="検索キーワード:")
search_label.pack(side=tk.LEFT, padx=(0, 10))

search_term_entry = tk.Entry(search_frame)
search_term_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

# カテゴリURL
category_frame = tk.Frame(collector_frame)
category_frame.pack(fill=tk.X, padx=10, pady=5)

category_label = tk.Label(category_frame, text="カテゴリURL:")
category_label.pack(side=tk.LEFT, padx=(0, 10))

category_url_entry = tk.Entry(category_frame)
category_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

# ベストセラーカテゴリ
bestseller_frame = tk.Frame(collector_frame)
bestseller_frame.pack(fill=tk.X, padx=10, pady=5)

bestseller_label = tk.Label(bestseller_frame, text="ベストセラーカテゴリ:")
bestseller_label.pack(side=tk.LEFT, padx=(0, 10))

bestseller_category_entry = tk.Entry(bestseller_frame)
bestseller_category_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
bestseller_category_entry.insert(0, "electronics")  # デフォルト値

# 最大収集数
max_items_frame = tk.Frame(collector_frame)
max_items_frame.pack(fill=tk.X, padx=10, pady=5)

max_items_label = tk.Label(max_items_frame, text="最大収集数:")
max_items_label.pack(side=tk.LEFT, padx=(0, 10))

max_items_spinbox = tk.Spinbox(max_items_frame, from_=1, to=50, width=5)
max_items_spinbox.delete(0, tk.END)
max_items_spinbox.insert(0, "10")  # デフォルト値
max_items_spinbox.pack(side=tk.LEFT)

# 実行ボタン
run_button = tk.Button(collector_frame, text="Amazon商品収集実行", command=run_amazon_collector)
run_button.pack(pady=10)

# 共通のステータス表示領域
status_frame = tk.Frame(root)
status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

# 進捗表示
progress_label = tk.Label(status_frame, text="")
progress_label.pack(pady=(0, 5))

# ステータス表示エリア
status_label = tk.Label(status_frame, text="処理ステータス:")
status_label.pack(anchor="w")
status_text = scrolledtext.ScrolledText(status_frame, height=15)
status_text.pack(fill=tk.BOTH, expand=True)

root.mainloop()