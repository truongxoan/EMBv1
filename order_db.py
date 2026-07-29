import sqlite3
import os
import sys
import csv
from datetime import datetime

def get_db_path():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, 'order_history.db')

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            product_name TEXT,
            variant_info TEXT,
            thread_color TEXT,
            bg_color TEXT,
            file_type TEXT,
            size TEXT,
            dims TEXT,
            status TEXT DEFAULT 'Completed',
            export_folder TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_order(order_data, status="Completed", export_folder=""):
    init_db()
    if not isinstance(order_data, dict):
        return
    oid = order_data.get('order_id', 'Unknown')
    if not oid or oid == 'Unknown':
        return

    p_name = order_data.get('product_name', '')
    variant = order_data.get('variant_info', '')
    t_color = order_data.get('thread_color', '-')
    bg_color = order_data.get('bg_color', '-')
    f_type = order_data.get('file_type', '-')
    size = order_data.get('size', '-')
    dims = order_data.get('dims', '')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO order_history (order_id, product_name, variant_info, thread_color, bg_color, file_type, size, dims, status, export_folder, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (oid, p_name, variant, t_color, bg_color, f_type, size, dims, status, export_folder, created_at))
    conn.commit()
    conn.close()

def get_orders(query="", limit=200):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if query:
        q = f"%{query}%"
        cursor.execute('''
            SELECT id, order_id, product_name, variant_info, thread_color, bg_color, file_type, size, dims, status, export_folder, created_at
            FROM order_history
            WHERE order_id LIKE ? OR product_name LIKE ? OR variant_info LIKE ? OR file_type LIKE ? OR thread_color LIKE ?
            ORDER BY id DESC LIMIT ?
        ''', (q, q, q, q, q, limit))
    else:
        cursor.execute('''
            SELECT id, order_id, product_name, variant_info, thread_color, bg_color, file_type, size, dims, status, export_folder, created_at
            FROM order_history
            ORDER BY id DESC LIMIT ?
        ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for r in rows:
        orders.append({
            "id": r[0],
            "order_id": r[1],
            "product_name": r[2],
            "variant_info": r[3],
            "thread_color": r[4],
            "bg_color": r[5],
            "file_type": r[6],
            "size": r[7],
            "dims": r[8],
            "status": r[9],
            "export_folder": r[10],
            "created_at": r[11]
        })
    return orders

def delete_order(order_db_id):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM order_history WHERE id = ?", (order_db_id,))
    conn.commit()
    conn.close()

def get_today_count():
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d") + "%"
    cursor.execute("SELECT COUNT(*) FROM order_history WHERE created_at LIKE ?", (today_str,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def export_to_csv(filepath):
    orders = get_orders(limit=1000)
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Mã Đơn', 'Sản Phẩm', 'Biến Thể', 'Màu Chỉ', 'Màu Nền', 'Loại File', 'Size', 'Kích Thước', 'Trạng Thái', 'Thời Gian'])
        for o in orders:
            writer.writerow([o['id'], o['order_id'], o['product_name'], o['variant_info'], o['thread_color'], o['bg_color'], o['file_type'], o['size'], o['dims'], o['status'], o['created_at']])
    return len(orders)
