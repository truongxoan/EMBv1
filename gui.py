from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QPushButton, QFrame, QApplication, QCheckBox, QGridLayout, QDialog, QScrollArea, QSystemTrayIcon, QMenu, QLineEdit, QLayout, QProgressBar, QComboBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QPropertyAnimation, QRect, QPoint, QByteArray, QEvent
from PySide6.QtGui import QColor, QPalette, QLinearGradient, QPainter, QPen, QPixmap, QImage, QAction, QConicalGradient, QBrush, QIcon, QFont
import os
import sys
import random
import string
import socket
import logic
import keyboard
import time
import math
import order_db
from ui_components import HackerLabel, ScrollingLabel, FireworkParticle

import security
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except:
    HAS_WIN32 = False
    print("Warning: pywin32 not installed, window features disabled")

class ImagePreviewDialog(QDialog):
    """Sleek live-updating overlay window to display all details of the current order"""
    def __init__(self, order_data, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.parent_app = parent
        self._drag_pos = None
        
        # Central layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)
        
        # Outer border frame
        self.frame = QFrame(self)
        self.frame.setObjectName("MainFrame")
        self.frame.setStyleSheet("""
            #MainFrame {
                background: transparent;
                border: none;
            }
        """)
        self.layout.addWidget(self.frame)
        
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(10)
        
        # 1. Custom Title Bar
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 4)
        
        self.lbl_title = QLabel("◆ CHI TIẾT ĐƠN HÀNG ◆")
        self.lbl_title.setStyleSheet("color: #00ff41; font-family: 'Consolas', sans-serif; font-size: 12px; font-weight: bold;")
        title_layout.addWidget(self.lbl_title)
        
        title_layout.addStretch()
        
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(18, 18)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ff3333;
                font-size: 16px;
                font-weight: bold;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                color: #ff5555;
                background: rgba(255, 50, 50, 30);
                border-radius: 4px;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        title_layout.addWidget(self.btn_close)
        
        frame_layout.addLayout(title_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333; max-height: 1px; border: none;")
        frame_layout.addWidget(line)
        
        # 2. Main Content Splitter (Left: Info Grid, Right: Image)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        
        # Left Panel (Info Grid)
        info_widget = QWidget()
        info_layout = QGridLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)
        
        label_style = "color: #888888; font-family: 'Consolas', 'Segoe UI'; font-size: 11px; font-weight: bold;"
        value_style = "color: #ffffff; font-family: 'Consolas', 'Segoe UI'; font-size: 11px;"
        value_highlight = "color: #00ff41; font-family: 'Consolas', 'Segoe UI'; font-size: 12px; font-weight: bold;"
        
        # Labels and Values setup
        info_layout.addWidget(QLabel("Mã Đơn Hàng:", info_widget), 0, 0)
        self.val_oid = QLabel("-", info_widget)
        self.val_oid.setStyleSheet(value_highlight)
        info_layout.addWidget(self.val_oid, 0, 1)
        
        info_layout.addWidget(QLabel("Sản Phẩm:", info_widget), 1, 0)
        self.val_prod = QLabel("-", info_widget)
        self.val_prod.setStyleSheet(value_style)
        self.val_prod.setWordWrap(True)
        info_layout.addWidget(self.val_prod, 1, 1)
        
        info_layout.addWidget(QLabel("Size / Kiểu:", info_widget), 2, 0)
        self.val_size_mode = QLabel("-", info_widget)
        self.val_size_mode.setStyleSheet(value_style)
        info_layout.addWidget(self.val_size_mode, 2, 1)
        
        info_layout.addWidget(QLabel("Vị Trí Thêu:", info_widget), 3, 0)
        self.val_pos = QLabel("-", info_widget)
        self.val_pos.setStyleSheet(value_highlight)
        info_layout.addWidget(self.val_pos, 3, 1)
        
        info_layout.addWidget(QLabel("Màu Chỉ:", info_widget), 4, 0)
        self.val_color = QLabel("-", info_widget)
        self.val_color.setStyleSheet(value_style)
        info_layout.addWidget(self.val_color, 4, 1)
        
        info_layout.addWidget(QLabel("Màu Nền:", info_widget), 5, 0)
        self.val_bg_color = QLabel("-", info_widget)
        self.val_bg_color.setStyleSheet(value_style)
        info_layout.addWidget(self.val_bg_color, 5, 1)
        
        info_layout.addWidget(QLabel("Kích Thước:", info_widget), 6, 0)
        self.val_dims = QLabel("-", info_widget)
        self.val_dims.setStyleSheet(value_style)
        info_layout.addWidget(self.val_dims, 6, 1)
        
        # Style all label children in info_layout (column 0)
        for r in range(7):
            item = info_layout.itemAtPosition(r, 0)
            if item and item.widget():
                item.widget().setStyleSheet(label_style)
                item.widget().setFixedWidth(85)
                
        content_layout.addWidget(info_widget, 1)
        
        # Right Panel (Image Container)
        image_frame = QFrame()
        image_frame.setStyleSheet("background-color: #030305; border: 1px solid #222; border-radius: 4px;")
        image_frame_layout = QVBoxLayout(image_frame)
        image_frame_layout.setContentsMargins(4, 4, 4, 4)
        
        self.lbl_image = QLabel(image_frame)
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setFixedSize(220, 220)
        self.lbl_image.setStyleSheet("border: none; color: #777; font-family: 'Consolas'; font-size: 10px;")
        image_frame_layout.addWidget(self.lbl_image)
        
        content_layout.addWidget(image_frame)
        frame_layout.addLayout(content_layout)
        
        # 3. Footer text
        self.lbl_footer = QLabel("◆ Nhấn & giữ chuột để kéo di chuyển | Phím ESC để tắt ◆")
        self.lbl_footer.setAlignment(Qt.AlignCenter)
        self.lbl_footer.setStyleSheet("color: #555555; font-family: 'Consolas'; font-size: 9px;")
        frame_layout.addWidget(self.lbl_footer)
        
        # Pulse animation and border color setup
        self.border_color = QColor("#00ff41") # default cyber green
        self.pulse_val = 0.0
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_timer.start(50)  # 20 FPS refresh rate
        
        # Load initial data and restore position
        self.setFixedSize(560, 320)
        self.update_order_data(order_data)
        self.restore_position()
        
    def update_order_data(self, order_data):
        """Update window text fields and design image dynamically without closing"""
        if not order_data:
            self.val_oid.setText("-")
            self.val_prod.setText("-")
            self.val_size_mode.setText("-")
            self.val_pos.setText("-")
            self.val_color.setText("-")
            self.val_bg_color.setText("-")
            self.val_dims.setText("-")
            self.lbl_image.setText("Không có dữ liệu đơn hàng")
            return
            
        oid = order_data.get('order_id', 'Unknown')
        prod = order_data.get('product_name', '-')
        size = order_data.get('size', '-')
        mode = order_data.get('mode', '-')
        pos = ", ".join(order_data.get('positions', ['4']))
        color = order_data.get('thread_color', '-')
        bg_color = order_data.get('bg_color', '-')
        dims = order_data.get('dims', '-')
        image_url = order_data.get('image_url', '')
        
        # Update text labels
        self.val_oid.setText(oid)
        self.val_prod.setText(prod)
        self.val_size_mode.setText(f"{size} / {mode}")
        self.val_pos.setText(pos)
        self.val_color.setText(color)
        self.val_bg_color.setText(bg_color)
        self.val_dims.setText(dims)
        
        # Ambient color resolution (thread color prioritized, fallback to background color)
        t_col = self.resolve_color(color)
        bg_col = self.resolve_color(bg_color)
        self.border_color = t_col or bg_col or QColor("#00ff41")
        
        # Update title text color to match border for cohesive high-tech branding
        self.lbl_title.setStyleSheet(f"color: {self.border_color.name()}; font-family: 'Consolas', sans-serif; font-size: 12px; font-weight: bold;")
        
        # Load image (remote URL or fallback to local files)
        self.load_design_image(image_url)

    def load_design_image(self, image_url):
        """Load and display the design image from a URL or local path"""
        self.lbl_image.setText("Đang tải ảnh...")
        
        # Try local fallback paths first if url is empty
        img_path = image_url
        if not img_path:
            # Look for local 1.png in order folder
            if self.parent_app and self.parent_app.current_folder:
                p1 = os.path.join(self.parent_app.current_folder, '1.png')
                if os.path.exists(p1):
                    img_path = p1
            if not img_path:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                p_desk = os.path.join(desktop, '1.png')
                if os.path.exists(p_desk):
                    img_path = p_desk
                    
        if not img_path:
            self.lbl_image.setText("Không tìm thấy ảnh")
            return
            
        if os.path.exists(img_path):
            pixmap = QPixmap()
            if pixmap.load(img_path):
                self.display_pixmap(pixmap)
            else:
                self.lbl_image.setText("Lỗi định dạng ảnh")
        elif img_path.startswith(('http://', 'https://')):
            import threading
            def download():
                try:
                    import urllib.request
                    req = urllib.request.Request(img_path, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        img_data = response.read()
                    qimg = QImage.fromData(img_data)
                    px = QPixmap.fromImage(qimg)
                    QTimer.singleShot(0, lambda: self.display_pixmap(px))
                except Exception as e:
                    print(f"Error loading viewer image: {e}")
                    QTimer.singleShot(0, lambda: self.lbl_image.setText("Lỗi tải ảnh web"))
            threading.Thread(target=download, daemon=True).start()
        else:
            self.lbl_image.setText("Không tìm thấy ảnh")
            
    def display_pixmap(self, pixmap):
        if pixmap.isNull():
            self.lbl_image.setText("Ảnh lỗi")
            return
        scaled = pixmap.scaled(self.lbl_image.width() - 8, self.lbl_image.height() - 8, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_image.setPixmap(scaled)
        
    def restore_position(self):
        """Restore window position from configuration file"""
        if self.parent_app and os.path.exists(self.parent_app._config_path):
            import json
            try:
                with open(self.parent_app._config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                x = cfg.get('viewer_x')
                y = cfg.get('viewer_y')
                if x is not None and y is not None:
                    # Validate position fits on screen
                    screen = QApplication.primaryScreen().geometry()
                    if 0 <= x < screen.width() - 50 and 0 <= y < screen.height() - 50:
                        self.move(x, y)
                        return
            except Exception as e:
                print(f"Error restoring viewer position: {e}")
                
        # Center if no stored position
        screen_geom = QApplication.primaryScreen().geometry()
        self.move((screen_geom.width() - self.width()) // 2, (screen_geom.height() - self.height()) // 2)

    def save_position(self):
        """Save current window position to configuration file"""
        if not self.parent_app:
            return
        import json
        try:
            cfg = {}
            if os.path.exists(self.parent_app._config_path):
                with open(self.parent_app._config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            cfg['viewer_x'] = self.pos().x()
            cfg['viewer_y'] = self.pos().y()
            with open(self.parent_app._config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f"[VIEWER] Saved position: x={self.pos().x()}, y={self.pos().y()}")
        except Exception as e:
            print(f"Error saving viewer position: {e}")
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            self.save_position() # Save on release
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
            
    def resolve_color(self, color_name):
        """Map English/Vietnamese color names to HEX values for ambient border indicator"""
        if not color_name or color_name == '-':
            return None
        name_lower = color_name.strip().lower()
        
        mapping = {
            'black': '#555555',     # Grey instead of pure black for visibility
            'white': '#ffffff',
            'red': '#ff3333',
            'blue': '#0099ff',
            'green': '#33ff33',
            'yellow': '#ffff33',
            'pink': '#ff66cc',
            'purple': '#b833ff',
            'orange': '#ff9900',
            'navy': '#0033aa',
            'grey': '#888888',
            'gray': '#888888',
            'brown': '#a0522d',
            'cream': '#fffdd0',
            'beige': '#f5f5dc',
            'gold': '#ffd700',
            'silver': '#c0c0c0',
            
            # Vietnamese names
            'đen': '#555555',
            'trắng': '#ffffff',
            'đỏ': '#ff3333',
            'xanh dương': '#0099ff',
            'xanh lá': '#33ff33',
            'vàng': '#ffff33',
            'hồng': '#ff66cc',
            'tím': '#b833ff',
            'cam': '#ff9900',
            'xám': '#888888',
            'nâu': '#a0522d',
            'kem': '#fffdd0'
        }
        
        for key, hex_val in mapping.items():
            if key in name_lower:
                return QColor(hex_val)
        return None

    def update_pulse(self):
        """Update pulse phase for breathing LED border effect and request repaint"""
        self.pulse_val += 0.12 # Speed of pulsation
        if self.pulse_val > 2 * math.pi:
            self.pulse_val -= 2 * math.pi
        self.update()

    def paintEvent(self, event):
        """Render custom dialog background and pulsating ambient color border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate alpha for breathing effect (oscillating between 120 and 255)
        alpha = int(120 + 135 * abs(math.sin(self.pulse_val)))
        
        border_color_with_alpha = QColor(self.border_color)
        border_color_with_alpha.setAlpha(alpha)
        
        # Draw translucent background panel
        painter.setBrush(QBrush(QColor(6, 6, 9, 248)))
        
        # Draw border
        pen = QPen(border_color_with_alpha, 2)
        painter.setPen(pen)
        
        # Draw rounded rectangle (offset by 1px to prevent clipping)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()

    def closeEvent(self, event):
        self.pulse_timer.stop()
        self.save_position()
        super().closeEvent(event)

class TextUtilityDialog(QDialog):
    """Small sleek popup for text transformations"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cong cu van ban")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setStyleSheet("""
            QDialog { background: #020005; border: 2px solid #00ff41; color: #00ff41; }
            QLineEdit { background: #000; color: #00ff41; border: 1px solid #00ff41; padding: 5px; font-family: 'Consolas'; }
            QPushButton { background: #002200; color: #00ff41; border: 1px solid #00ff41; padding: 4px; border-radius: 3px; font-size: 10px; }
            QPushButton:hover { background: #004400; color: #00f3ff; border: 1px solid #00f3ff; }
            QLabel { color: #ff00ff; font-weight: bold; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        layout = QVBoxLayout(self)
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Nhap noi dung can xu ly...")
        layout.addWidget(self.input_text)
        
        btn_grid = QGridLayout()
        
        btns = [
            ("HOA/THUONG", self.toggle_case),
            ("SO LA MA", self.to_roman),
            ("SO THUONG", self.to_num),
            ("DAO CHU", self.reverse_text),
            ("XOA", self.clear_text),
            ("DONG", self.close)
        ]
        
        for i, (name, func) in enumerate(btns):
            btn = QPushButton(name)
            btn.clicked.connect(func)
            btn_grid.addWidget(btn, i // 3, i % 3)
            
        layout.addLayout(btn_grid)
        self.setFixedWidth(180)

    def toggle_case(self):
        t = self.input_text.text()
        self.input_text.setText(t.swapcase() if t else "")
        
    def reverse_text(self):
        t = self.input_text.text()
        self.input_text.setText(t[::-1] if t else "")

    def clear_text(self):
        self.input_text.clear()

    def to_roman(self):
        t = self.input_text.text().strip()
        if t.isdigit():
            try:
                val = int(t)
                roman = {1000: 'M', 900: 'CM', 500: 'D', 400: 'CD', 100: 'C', 90: 'XC', 50: 'L', 40: 'XL', 10: 'X', 9: 'IX', 5: 'V', 4: 'IV', 1: 'I'}
                res = ""
                for v, r in roman.items():
                    while val >= v:
                        res += r
                        val -= v
                self.input_text.setText(res)
            except Exception:
                self.input_text.setText("")
        else:
            # Not a number, do nothing or clear
            pass

    def to_num(self):
        t = self.input_text.text().upper().strip()
        roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
        res = 0
        try:
            for i in range(len(t)):
                ch = t[i]
                if ch not in roman:
                    # Ignore non-roman characters instead of crashing
                    continue
                if i > 0 and roman[ch] > roman.get(t[i-1], 0):
                    res += roman[ch] - 2 * roman.get(t[i-1], 0)
                else:
                    res += roman[ch]
            self.input_text.setText(str(res) if res > 0 else "")
        except Exception:
            self.input_text.setText("")  # fail silently on bad input

class HackMenuDialog(QDialog):
    """Bảng menu phím tắt phong cách Hacker (Hack Menu)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bang phim tat")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background: #020005; border: 2px solid #00ff41; color: #00ff41; }
            QLabel { color: #00ff41; font-family: 'Consolas'; font-size: 10px; }
            .header { color: #ff00ff; font-weight: bold; font-size: 12px; }
            .key { color: #00f3ff; font-weight: bold; }
        """)
        
        layout = QVBoxLayout(self)
        
        header = QLabel("--- [ HUONG DAN PHIM TAT ] ---")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #ff00ff; font-weight: bold; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        shortcuts = [
            ("INSERT", "PHIM TAT", "Bat/tat bang huong dan phim tat"),
            ("CTRL+H", "PHIM TAT", "Bat/tat bang huong dan (phim phu)"),
            ("ALT+V", "COPY PATH", "Sao chep duong dan thu muc don hien tai"),
            ("ALT+E", "MO THU MUC", "Mo nhanh thu muc dang xu ly"),
            ("ALT+C", "COPY MA", "Sao chep ma don"),
            ("ALT+B", "CHUP ANH", "Chup cua so theu"),
            ("ALT+I", "XEM ANH", "Hiển thị ảnh của đơn trực tiếp trên màn hình"),
            ("CTRL+B", "CHAY AUTO", "Chay quy trinh tu dong 3 buoc"),
            ("CTRL+SHIFT+B", "AUTO NHANH", "Chay auto nhanh bang phim phu"),
            ("CTRL+SHIFT+V", "COPY MIX", "Copy ID kem vi tri da tick"),
            ("CTRL+R", "RESET", "Dat lai du lieu hien tai"),
            ("CTRL+SPACE", "TU DONG", "Chay quy trinh 3 buoc"),
            ("CTRL+X", "DONG APP", "Tat nhanh Ultimate"),
            ("CTRL+ALT+E", "MO THU MUC", "Mo thu muc da tao (phim phu)"),
            ("CTRL+M", "XEM ANH", "Mo anh chup gan nhat"),
            ("Q", "DUNG", "Dung quy trinh khan cap")
        ]
        
        for key, func, desc in shortcuts:
            row = QHBoxLayout()
            lbl_key = QLabel(f"[{key}]")
            lbl_key.setFixedWidth(80)
            lbl_key.setStyleSheet("color: #00f3ff; font-weight: bold;")
            
            lbl_func = QLabel(f"{func}")
            lbl_func.setFixedWidth(80)
            lbl_func.setStyleSheet("color: #00ff41; font-weight: bold;")
            
            lbl_desc = QLabel(f"- {desc}")
            lbl_desc.setStyleSheet("color: #008800;")
            
            row.addWidget(lbl_key)
            row.addWidget(lbl_func)
            row.addWidget(lbl_desc)
            layout.addLayout(row)
        
        footer = QLabel("\nNhan INSERT hoac CTRL+H de dong bang huong dan")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #444; font-size: 8px;")
        layout.addWidget(footer)
        
        self.setFixedWidth(350)

class OrderHistoryDialog(QDialog):
    """Dialog displaying SQLite order history with search, load, open folder, and export CSV features"""
    def __init__(self, parent_app=None):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(700, 420)
        self.setStyleSheet("""
            QDialog { background: #0b0c10; border: 2px solid #00f3ff; border-radius: 8px; color: #ffffff; }
            QLabel { font-family: 'Consolas', 'Segoe UI'; color: #c5c6c7; font-size: 11px; }
            QLineEdit { background: #1f2833; border: 1px solid #45a29e; color: #66fcf1; border-radius: 4px; padding: 4px; font-family: 'Consolas'; }
            QPushButton { background: #1f2833; border: 1px solid #45a29e; color: #66fcf1; border-radius: 4px; font-family: 'Consolas'; font-size: 10px; padding: 4px 8px; font-weight: bold; }
            QPushButton:hover { background: #45a29e; color: #0b0c10; }
            QTableWidget { background: #1f2833; color: #ffffff; gridline-color: #333333; border: 1px solid #45a29e; font-size: 10px; font-family: 'Consolas'; }
            QHeaderView::section { background: #0b0c10; color: #66fcf1; border: 1px solid #45a29e; font-weight: bold; padding: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header bar
        header_box = QHBoxLayout()
        title = QLabel("📜 LỊCH SỬ ĐƠN HÀNG (SQLITE DATABASE)")
        title.setStyleSheet("color: #00f3ff; font-weight: bold; font-size: 13px;")
        header_box.addWidget(title)
        
        header_box.addStretch()

        self.lbl_today = QLabel("Hôm nay: 0 đơn")
        self.lbl_today.setStyleSheet("color: #00ff41; font-weight: bold;")
        header_box.addWidget(self.lbl_today)

        btn_close = QPushButton("✕ Đóng")
        btn_close.clicked.connect(self.close)
        header_box.addWidget(btn_close)
        layout.addLayout(header_box)

        # Search bar & Export row
        search_box = QHBoxLayout()
        search_label = QLabel("🔍 Tìm kiếm:")
        search_box.addWidget(search_label)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Nhập mã đơn, tên sản phẩm, loại file, màu chỉ...")
        self.txt_search.textChanged.connect(self.load_data)
        search_box.addWidget(self.txt_search, 1)

        btn_export = QPushButton("📊 Xuất CSV")
        btn_export.clicked.connect(self.on_export_csv)
        search_box.addWidget(btn_export)
        layout.addLayout(search_box)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID Đơn", "Sản Phẩm", "Loại File", "Màu Chỉ", "Kích Thước", "Thời Gian", "Thao Tác"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.load_data()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def load_data(self):
        query = self.txt_search.text().strip() if hasattr(self, 'txt_search') else ""
        orders = order_db.get_orders(query, limit=200)
        today_count = order_db.get_today_count()
        self.lbl_today.setText(f"Hôm nay: {today_count} đơn")

        self.table.setRowCount(0)
        for row_idx, o in enumerate(orders):
            self.table.insertRow(row_idx)
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(o.get('order_id', ''))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(o.get('product_name', ''))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(o.get('file_type', ''))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(o.get('thread_color', ''))))
            
            dims_text = str(o.get('dims', '')) or str(o.get('size', ''))
            self.table.setItem(row_idx, 4, QTableWidgetItem(dims_text))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(o.get('created_at', ''))))

            # Action buttons cell
            btn_cell = QWidget()
            btn_layout = QHBoxLayout(btn_cell)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)

            btn_load = QPushButton("🔄 Load")
            btn_load.setToolTip("Nạp đơn này lên giao diện chính")
            btn_load.clicked.connect(lambda checked, order=o: self.on_load_order(order))
            btn_layout.addWidget(btn_load)

            folder_path = o.get('export_folder', '')
            if folder_path and os.path.exists(folder_path):
                btn_folder = QPushButton("📁 Folder")
                btn_folder.setToolTip("Mở thư mục chứa file")
                btn_folder.clicked.connect(lambda checked, f=folder_path: os.startfile(f))
                btn_layout.addWidget(btn_folder)

            self.table.setCellWidget(row_idx, 6, btn_cell)

    def on_load_order(self, order_data):
        if self.parent_app:
            parsed = {
                'order_id': order_data.get('order_id'),
                'product_name': order_data.get('product_name'),
                'variant_info': order_data.get('variant_info'),
                'thread_color': order_data.get('thread_color'),
                'bg_color': order_data.get('bg_color'),
                'file_type': order_data.get('file_type'),
                'size': order_data.get('size'),
                'dims': order_data.get('dims'),
                'positions': []
            }
            self.parent_app.update_data(parsed)
            self.parent_app.flash_status("LOADED OK", "#00ff41")
            self.close()

    def on_export_csv(self):
        default_name = f"Order_History_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Xuất file CSV Lịch Sử Đơn", default_name, "CSV Files (*.csv)")
        if path:
            count = order_db.export_to_csv(path)
            QMessageBox.information(self, "Thành Công", f"Đã xuất thành công {count} đơn hàng ra file:\n{path}")

class LicenseDialog(QDialog):
    """Dialog shown when access is denied"""
    def __init__(self, hwid, pc_name, reason="Machine Unauthorized", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(300, 200)
        self.setStyleSheet("""
            QDialog { background: #0c0c0e; border: 2px solid #ff4444; color: white; }
            QLabel { font-family: 'Consolas'; font-size: 10px; color: #aaa; }
            .header { color: #ff4444; font-weight: bold; font-size: 13px; }
            .hwid { color: #00ff41; font-weight: bold; font-size: 11px; background: #1a1a1a; padding: 5px; border-radius: 4px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel("ACCESS DENIED")
        header.setProperty("class", "header")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(10)
        
        msg = QLabel(reason)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)
        
        layout.addSpacing(15)
        
        lbl_info = QLabel("Please send this ID to provider:")
        layout.addWidget(lbl_info)
        
        self.lbl_hwid = QLabel(hwid)
        self.lbl_hwid.setProperty("class", "hwid")
        self.lbl_hwid.setAlignment(Qt.AlignCenter)
        self.lbl_hwid.setCursor(Qt.PointingHandCursor)
        self.lbl_hwid.mousePressEvent = lambda e: self.copy_hwid()
        layout.addWidget(self.lbl_hwid)
        
        layout.addSpacing(10)
        
        lbl_pc = QLabel(f"PC: {pc_name}")
        lbl_pc.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_pc)
        
        layout.addStretch()
        
        btn_close = QPushButton("CLOSE")
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("background: #222; border: 1px solid #444; color: white; padding: 5px;")
        layout.addWidget(btn_close)

    def copy_hwid(self):
        QApplication.clipboard().setText(self.lbl_hwid.text())
        self.lbl_hwid.setText("COPIED!")
        QTimer.singleShot(1000, lambda: self.lbl_hwid.setText(security.get_hwid()))

class SuccessToast(QDialog):
    """Sleek auto-disappearing toast notification"""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #051a05, stop:1 #003300);
                border: 2px solid #00ff41;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', 'Consolas', sans-serif;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        self.adjust_position()
        QTimer.singleShot(2500, self.close)
        
    def adjust_position(self):
        screen = QApplication.primaryScreen().geometry()
        self.setFixedSize(220, 42)
        x = (screen.width() - self.width()) // 2
        y = 40  # Top center of the screen
        self.move(x, y)

class InfoOverlay(QWidget):
    """Transparent overlay to show info on top of Ultimate app"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        
        common_style = """
            color: red; 
            font-family: 'Consolas', 'Courier New', monospace; 
            font-weight: bold; 
            font-size: 10px;
            background: rgba(0, 0, 0, 150);
            padding: 1px 6px;
            border-radius: 2px;
        """
        
        self.lbl_info = QLabel("TX READY")
        self.lbl_info.setStyleSheet("""
            color: #00ff41; 
            font-family: 'Consolas', 'Courier New', monospace; 
            font-weight: bold; 
            font-size: 11px;
            background: rgba(0, 5, 0, 180);
            padding: 2px 10px;
            border: 1px solid #00ff41;
            border-radius: 3px;
        """)
        self.lbl_info.setAlignment(Qt.AlignCenter)
        
        self.lbl_line1 = QLabel("TX READY")
        self.lbl_line1.setStyleSheet(common_style)
        self.lbl_line1.setAlignment(Qt.AlignCenter)
        
        self.lbl_line2 = QLabel("-")
        self.lbl_line2.setStyleSheet(common_style)
        self.lbl_line2.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.lbl_line1)
        layout.addWidget(self.lbl_line2)
        self.setFixedSize(550, 42)
        
    def update_info(self, id_val, name, size, f_type, dims, thread_color="-"):
        self.lbl_line1.setText(f"◆ MÃ: {id_val}  |  LOẠI: {f_type}  |  MÀU CHỈ: {thread_color} ◆")
        detail = f"➤ TÊN: {name}  |  SIZE: {size}"
        if dims and dims != "-":
            detail += f"  ({dims})"
        self.lbl_line2.setText(detail)

class HelpTooltip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame {
                background: rgba(5, 10, 5, 240);
                border: 2px solid #00ff41;
                border-radius: 6px;
            }
            QLabel {
                color: #00ff41;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 9px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        
        title = QLabel("=== BẢNG HƯỚNG DẪN ===")
        title.setStyleSheet("font-weight: bold; font-size: 10px; color: #00ff41; border-bottom: 1px solid rgba(0, 255, 65, 80); padding-bottom: 2px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        guide_text = (
            "⚡ <b>Auto Run:</b> Ctrl+Space<br>"
            "📁 <b>Thư mục:</b> Alt+E (Tạo/Mở)<br>"
            "📸 <b>Chụp ảnh:</b> Alt+B (Chụp cửa sổ thêu)<br>"
            "📋 <b>MIX:</b> Ctrl+Shift+V (Copy đ.dẫn PO)<br>"
            "↻ <b>Reset:</b> Ctrl+R (Đặt lại dữ liệu)<br>"
            "👁️ <b>HUD:</b> Click mắt để ẩn/hiện chỉ số<br>"
            "📌 <b>Ghim:</b> Ghim tool luôn nổi<br>"
            "⌨️ <b>Insert:</b> Ẩn/Hiện tool (khay hệ thống)<br>"
            "❌ <b>Ctrl+Alt+X:</b> Tắt khẩn cấp công cụ"
        )
        
        content = QLabel(guide_text)
        layout.addWidget(content)
        self.setFixedSize(220, 160)

class HelpButton(QPushButton):
    def __init__(self, parent_app, parent=None):
        super().__init__("❓", parent)
        self.parent_app = parent_app
        self.setFixedSize(12, 12)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #00ff41;
                border: none;
                font-size: 8px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.tooltip = None
        
    def enterEvent(self, event):
        if not self.tooltip:
            self.tooltip = HelpTooltip(self.parent_app)
        # Position to the left of the button
        pos = self.mapToGlobal(QPoint(-225, -50))
        self.tooltip.move(pos)
        self.tooltip.show()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if self.tooltip:
            self.tooltip.hide()
            self.tooltip.deleteLater()
            self.tooltip = None
        super().leaveEvent(event)

# Music player functionality removed per user request

class MiniApp(QMainWindow):
    # Define Signal for Thread-Safe Updates
    update_status_signal = Signal(str, str)
    status_signal = Signal(str, str) 
    progress_signal = Signal(int)
    show_success_toast_signal = Signal(str)
    hotkey_triggered_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(165, 192)
        self.setAcceptDrops(True) # Enable drag-and-drop for PNG files
        
        self.current_data = {}
        self.order_queue = []     # Queue of accumulated orders
        self.order_history = []   # History of completed orders
        self.current_folder = None
        self._drag_pos = None
        self.last_copied = ""  # Store for screenshot naming
        self.last_screenshot_path = None # Track for Ctrl+M preview
        self.last_detected_export_hwnd = None
        
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        self._config_path = os.path.join(app_dir, 'tx_config.json')
        self._save_folder = self._load_save_folder()
        
        # Folder button click tracking for double-click detection
        self._folder_clicks = 0
        self._folder_click_timer = QTimer()
        self._folder_click_timer.setSingleShot(True)
        self._folder_click_timer.timeout.connect(self._handle_folder_single_click)
        
        # State flags
        self.is_expanded = True
        self.is_pinned = True
        self.auto_trigger_enabled = False  # Auto-trigger when data arrives (DEFAULT OFF)
        self.preview_window = None
        
        # Docking state
        self.is_docked = False
        self.target_window_hwnd = None
        self.dock_offset_x = -170  # X offset from target window (negative = left of right edge)
        self.dock_offset_y = 10    # Y offset from target window top
        self.dock_search_attempts = 0  # Counter for reconnection attempts
        
        # Checkbox references
        self.chk_groups = {} 
        
        # Fireworks
        self.fireworks = []
        
        # RGB Border Animation
        self.border_hue = 0
        self.border_angle = 0  
        self.border_timer = QTimer()
        self.border_timer.timeout.connect(self.update_border)
        self.border_timer.start(30)  # Update every 30ms for smooth animation

        # Docking timer
        self.dock_timer = QTimer()
        self.dock_timer.timeout.connect(self.update_dock_position)
        
        # FPS Counter State
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000) # Update FPS label every second
        
        # Screenshot Timer (for single/double click detection)
        self.screenshot_clicks = 0
        self.screenshot_timer = QTimer()
        self.screenshot_timer.setSingleShot(True)
        self.screenshot_timer.timeout.connect(self.handle_screenshot_single)
        
        self.setup_ui()
        self.setup_tray_icon()
        self.setup_hotkeys()

        # Server status polling (green/red indicator button)
        self.server_status_timer = QTimer(self)
        self.server_status_timer.timeout.connect(self._cap_nhat_nut_server)
        self.server_status_timer.start(1500)
        self._cap_nhat_nut_server()
        
        # Info Overlay Setup
        self.overlay_enabled = True
        self.info_overlay = InfoOverlay()
        if self.is_pinned:
             self.info_overlay.show()
        
        self.overlay_timer = QTimer()
        self.overlay_timer.timeout.connect(self.update_overlay_position)
        self.overlay_timer.start(50) # Very fast sync for "glued" feel
        
        # Connect Signal to Slot
        self.update_status_signal.connect(self._flash_status_safe)
        self.status_signal.connect(self._update_status_strip)
        self.progress_signal.connect(self.set_progress)
        self.show_success_toast_signal.connect(self.show_success_toast)
        self.hotkey_triggered_signal.connect(self._handle_hotkey_on_main_thread)

        # Auto Folder Dialog Detector Thread
        self.is_closing = False
        import threading
        threading.Thread(target=self.auto_folder_dialog_detector, daemon=True).start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def update_fps(self):
        """Calculate FPS for the hack-menu feel"""
        now = time.time()
        dt = now - self.fps_start_time
        if dt > 0:
            self.current_fps = int(self.fps_frame_count / dt)
            if hasattr(self, 'lbl_fps'):
                # Simulate high-fps "flicker" common in hack menus
                flicker = random.randint(-2, 2)
                self.lbl_fps.setText(f"FPS: {self.current_fps + flicker}")
        
        self.fps_start_time = now
        self.fps_frame_count = 0

    @Slot(int)
    def set_progress(self, value):
        if hasattr(self, 'prog_bar'):
            self.prog_bar.setValue(value)
            self.prog_bar.setVisible(value > 0 and value <= 100)
            self.prog_bar.repaint()  # Force immediate UI redraw
            if value >= 100:
                self.lbl_status_strip.setText("Hoan tat")
                QTimer.singleShot(3000, lambda: self.prog_bar.setVisible(False))

    @Slot(str, str)
    def _update_status_strip(self, text, color="#f6de95"):
        if hasattr(self, 'lbl_status_strip'):
            self.lbl_status_strip.setText(text)
            self.lbl_status_strip.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 700;")

    def update_border(self):
        """Update RGB border color and rotation + Fireworks + Frame Counter"""
        self.fps_frame_count += 1
        self.border_hue = (self.border_hue + 3) % 360
        self.border_angle = (self.border_angle + 2) % 360  # Rotation angle
        
        # Spawn Fireworks (Low chance)
        if random.random() < 0.05: 
             cx = random.randint(20, 140)
             cy = random.randint(20, 140)
             color = QColor.fromHsv(random.randint(0, 360), 255, 255)
             for _ in range(15): # Particles
                 self.fireworks.append(FireworkParticle(cx, cy, color))
                 
        # Update Fireworks
        self.fireworks = [p for p in self.fireworks if p.update()]
        
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Custom paint for black-glass overlay panel with rotating rainbow border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        panel_rect = rect.adjusted(3, 3, -3, -3)

        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0.0, QColor(8, 8, 12, 245))
        gradient.setColorAt(1.0, QColor(4, 4, 6, 250))
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(panel_rect, 10, 10)

        # Paint purple grid background
        painter.setPen(QPen(QColor(80, 20, 100, 35), 1, Qt.DashLine))
        grid_size = 12
        for x in range(panel_rect.left(), panel_rect.right(), grid_size):
            painter.drawLine(x, panel_rect.top(), x, panel_rect.bottom())
        for y in range(panel_rect.top(), panel_rect.bottom(), grid_size):
            painter.drawLine(panel_rect.left(), y, panel_rect.right(), y)

        # Paint rotating rainbow border
        conical = QConicalGradient(panel_rect.center().x(), panel_rect.center().y(), self.border_angle)
        for i in range(13):
            hue = (self.border_hue + i * 30) % 360
            conical.setColorAt(i / 12.0, QColor.fromHsv(hue, 255, 255))
        
        pen_border = QPen(QBrush(conical), 3)
        painter.setPen(pen_border)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(panel_rect, 10, 10)

        # Keep subtle particle effects
        painter.setPen(Qt.NoPen)
        for p in self.fireworks:
            alpha = int(p.life * 255)
            color = p.color
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.drawEllipse(p.x, p.y, 2, 2)
            
        painter.end()

    def setup_ui(self):
        self.container = QWidget()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            #Container {
                background-color: rgba(8, 8, 10, 230);
                border: none;
                border-radius: 8px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
                font-size: 9px;
                background: transparent;
            }
        """)
        self.setCentralWidget(self.container)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(2)

        # 1. Title Bar
        title_bar = QHBoxLayout()
        title_bar.setSpacing(1)
        
        self.lbl_chu_chay = ScrollingLabel("AI LÀ VUA LÌ ĐÒN ⚡ BEYOND ALL BORDERS ⚡")
        self.lbl_chu_chay.setStyleSheet("color: #00ff41; font-family: 'Consolas'; font-weight: bold; font-size: 8px; background: transparent;")
        self.lbl_chu_chay.setFixedHeight(12)
        title_bar.addWidget(self.lbl_chu_chay, 1)

        self.btn_dock_title = QPushButton("🔗")
        self.btn_dock_title.setFixedSize(12, 12)
        self.btn_dock_title.setStyleSheet("background: transparent; color: #777; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_dock_title.clicked.connect(self.on_toggle_dock)
        self.btn_dock_title.setToolTip("Dock to Ultimate Window")
        title_bar.addWidget(self.btn_dock_title)

        self.btn_overlay_title = QPushButton("👁️")
        self.btn_overlay_title.setFixedSize(12, 12)
        self.btn_overlay_title.setStyleSheet("background: transparent; color: #00ff41; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_overlay_title.clicked.connect(self.on_toggle_overlay)
        self.btn_overlay_title.setToolTip("Toggle HUD Overlay")
        title_bar.addWidget(self.btn_overlay_title)

        self.btn_history_title = QPushButton("📜")
        self.btn_history_title.setFixedSize(12, 12)
        self.btn_history_title.setStyleSheet("background: transparent; color: #00f3ff; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_history_title.clicked.connect(self.on_show_history)
        self.btn_history_title.setToolTip("Xem Lịch sử Đơn hàng (DB)")
        title_bar.addWidget(self.btn_history_title)

        self.btn_mini_mode = QPushButton("🗗")
        self.btn_mini_mode.setFixedSize(12, 12)
        self.btn_mini_mode.setStyleSheet("background: transparent; color: #ff00ff; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_mini_mode.clicked.connect(self.on_toggle_mini_widget)
        self.btn_mini_mode.setToolTip("Thu nhỏ thành Mini Floating Widget")
        title_bar.addWidget(self.btn_mini_mode)

        self.btn_pin_title = QPushButton("📌")
        self.btn_pin_title.setFixedSize(12, 12)
        self.btn_pin_title.setStyleSheet("background: transparent; color: #ff3333; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_pin_title.clicked.connect(self.on_toggle_pin)
        self.btn_pin_title.setToolTip("Toggle Always on Top")
        title_bar.addWidget(self.btn_pin_title)

        self.btn_min = QPushButton("-")
        self.btn_min.setFixedSize(12, 12)
        self.btn_min.setStyleSheet("background: transparent; color: #00ff41; font-size: 10px; font-weight: bold; border: none; padding: 0;")
        self.btn_min.clicked.connect(self.on_minimize_to_tray)
        self.btn_min.setToolTip("Minimize to Tray")
        title_bar.addWidget(self.btn_min)

        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(12, 12)
        self.btn_close.setStyleSheet("background: transparent; color: #00ff41; font-size: 8px; font-weight: bold; border: none; padding: 0;")
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setToolTip("Close App")
        title_bar.addWidget(self.btn_close)

        # Help Button
        self.btn_help = HelpButton(self)
        title_bar.addWidget(self.btn_help)

        self.lbl_server_status = QLabel()
        self.lbl_server_status.setFixedSize(8, 8)
        self.lbl_server_status.setStyleSheet("background-color: #ff3333; border-radius: 4px;")
        self.lbl_server_status.setToolTip("Server Connection Status")
        title_bar.addWidget(self.lbl_server_status)

        main_layout.addLayout(title_bar)

        # 2. Order ID row
        id_layout = QHBoxLayout()
        id_layout.setContentsMargins(0, 0, 0, 0)
        id_layout.setSpacing(4)

        self.lbl_id = ScrollingLabel("WAITING DATA...")
        self.lbl_id.setStyleSheet("color: #ffffff; font-family: 'Consolas', 'Segoe UI'; font-weight: bold; font-size: 13px; background: transparent;")
        self.lbl_id.setFixedHeight(18)
        id_layout.addWidget(self.lbl_id, 1)

        main_layout.addLayout(id_layout)

        # 3. Product / Mode
        self.btn_mode = QPushButton("WAITING...")
        self.btn_mode.setStyleSheet("background: transparent; border: none; color: #00f3ff; font-family: 'Segoe UI', 'Bahnschrift'; font-size: 9px; font-weight: bold; text-align: left; padding: 0;")
        self.btn_mode.setFixedHeight(14)
        self.btn_mode.clicked.connect(lambda: self.copy_data("mode"))
        main_layout.addWidget(self.btn_mode)

        # 4. Badge (DST | Size)
        self.btn_badge = QPushButton("DST | 2x2 inches")
        self.btn_badge.setFixedHeight(20)
        self.btn_badge.setStyleSheet("""
            background: #440000;
            color: #ff003c;
            border: 1px solid #ff003c;
            border-radius: 6px;
            font-weight: bold;
            font-size: 10px;
            padding: 2px;
        """)
        self.btn_badge.clicked.connect(lambda: self.copy_data("badge"))
        main_layout.addWidget(self.btn_badge)

        # 5. Position Indicators (Dynamic Layout)
        self.positions_container = QWidget()
        self.positions_container.setFixedHeight(18)
        self.positions_layout = QHBoxLayout(self.positions_container)
        self.positions_layout.setContentsMargins(0, 0, 0, 0)
        self.positions_layout.setSpacing(4)

        # Create QCheckBoxes and add to horizontal layout
        self.chk_groups = {}
        self.all_keys = [
            '1','3','4','5','6','8','9','V','T',
            'I','O','P','B','G','H','S','E','C','D','F','L','R'
        ]

        checkbox_style = """
            QCheckBox {
                color: #00f3ff;
                font-family: 'Consolas';
                font-size: 9px;
                font-weight: bold;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 8px;
                height: 8px;
                border: 1px solid #00f3ff;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background: #00f3ff;
            }
        """

        for k in self.all_keys:
            chk = QCheckBox(k)
            chk.setStyleSheet(checkbox_style)
            chk.setVisible(False)
            chk.clicked.connect(lambda checked, key=k: self.on_checkbox_clicked(key))
            self.chk_groups[k] = chk
            self.positions_layout.addWidget(chk)

        self.positions_layout.addStretch()
        main_layout.addWidget(self.positions_container)

        # 6. Alt Text tips
        self.lbl_alt_tips = QLabel("C:ID | V:Folder | S:Shot")
        self.lbl_alt_tips.setStyleSheet("color: #00ff41; font-family: 'Consolas'; font-size: 8px; font-weight: bold; background: transparent;")
        self.lbl_alt_tips.setFixedHeight(10)
        main_layout.addWidget(self.lbl_alt_tips)

        # Real Neon Progress Bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(12)  # Increased from 8 to 12 for text readability
        self.prog_bar.setTextVisible(True)
        self.prog_bar.setAlignment(Qt.AlignCenter)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00ff41;
                border-radius: 3px;
                background: #020502;
                color: #ffffff; /* White text for contrast on both dark background and green chunk */
                font-family: 'Consolas', sans-serif;
                font-size: 9px;
                font-weight: bold;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #00ff41;
            }
        """)
        self.prog_bar.setVisible(False)
        main_layout.addWidget(self.prog_bar)

        # 7. Button Grid (4x2)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(3)
        grid.setContentsMargins(0, 0, 0, 0)

        # Auto Button
        self.btn_auto = QPushButton("⚡")
        self.btn_auto.setFixedSize(36, 28)
        self.btn_auto.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ff9900; font-size: 14px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_auto.clicked.connect(self.on_auto_click)
        self.btn_auto.setToolTip("Auto run (Ctrl+Space)")

        # Folder Button
        self.btn_folder = QPushButton("📁")
        self.btn_folder.setFixedSize(36, 28)
        self.btn_folder.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ffcc00; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_folder.clicked.connect(self.on_create_folder)
        self.btn_folder.setToolTip("Open folder (Alt+E)")

        # Screenshot Button
        self.btn_ss = QPushButton("📸")
        self.btn_ss.setFixedSize(36, 28)
        self.btn_ss.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #cc66ff; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_ss.clicked.connect(self.on_screenshot_click)
        self.btn_ss.setToolTip("Take screenshot (Alt+B)")

        # Copy Mix Button
        self.btn_mix = QPushButton("📋\nMIX")
        self.btn_mix.setFixedSize(36, 28)
        self.btn_mix.setStyleSheet("QPushButton { background: #020502; border: 1px solid #d4af37; border-radius: 4px; color: #d4af37; font-size: 8px; font-weight: bold; text-align: center; } QPushButton:hover { background: #1a1a00; }")
        self.btn_mix.clicked.connect(lambda: self.copy_data("mix"))
        self.btn_mix.setToolTip("Copy đường dẫn PO (Ctrl+Shift+V)")

        # Reset Button (compact)
        self.btn_reset = QPushButton("↻")
        self.btn_reset.setFixedSize(24, 24)
        self.btn_reset.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ff6600; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_reset.setToolTip("Reset data (Ctrl+R)")

        # In Button (auto function placeholder / DXF export)
        self.btn_in = QPushButton("🖨️")
        self.btn_in.setFixedSize(24, 24)
        self.btn_in.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #00ff41; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #003300; color: #ffffff; }")
        self.btn_in.clicked.connect(self.on_in_click)
        self.btn_in.setToolTip("Xuất file cắt DXF từ ảnh trong thư mục")

        # Download Image Button
        self.btn_download_img = QPushButton("⬇️")
        self.btn_download_img.setFixedSize(24, 24)
        self.btn_download_img.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ffcc00; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_download_img.clicked.connect(lambda: self.on_download_image_clicked("f11"))
        self.btn_download_img.setToolTip("Tải ảnh từ Web và chạy action f11.atn")

        # Download Pet Button
        self.btn_download_pet = QPushButton("🐾")
        self.btn_download_pet.setFixedSize(24, 24)
        self.btn_download_pet.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ff99ff; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        self.btn_download_pet.clicked.connect(lambda: self.on_download_image_clicked("pet"))
        self.btn_download_pet.setToolTip("Tải ảnh từ Web và chạy action pet.atn")

        # View Image Button
        self.btn_view_image = QPushButton("👁️")
        self.btn_view_image.setFixedSize(24, 24)
        self.btn_view_image.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #00e5ff; font-size: 11px; font-weight: bold; } QPushButton:hover { background: #002233; color: #ffffff; }")
        self.btn_view_image.clicked.connect(self.on_view_image_clicked)
        self.btn_view_image.setToolTip("Xem ảnh đơn hàng trực tiếp (Alt+I)")

        # QHBoxLayout for the bottom row
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.addWidget(self.btn_reset)
        row2_layout.addWidget(self.btn_in)
        row2_layout.addWidget(self.btn_download_img)
        row2_layout.addWidget(self.btn_download_pet)
        row2_layout.addWidget(self.btn_view_image)
        row2_layout.addStretch()
        
        row2_widget = QWidget()
        row2_widget.setLayout(row2_layout)

        # Add to grid
        grid.addWidget(self.btn_auto, 0, 0)
        grid.addWidget(self.btn_folder, 0, 1)
        grid.addWidget(self.btn_ss, 0, 2)
        grid.addWidget(self.btn_mix, 0, 3)
        grid.addWidget(row2_widget, 1, 0, 1, 4)

        main_layout.addWidget(grid_widget)

        # Create dummy references so existing functions don't fail
        self.lbl_fps = QLabel()
        self.lbl_status_strip = QLabel()
        self.lbl_goi_y = QLabel()

        # Update hover helps
        self._dang_ky_goi_y_hover(
            self.btn_min,
            self.btn_close,
            self.btn_auto,
            self.btn_folder,
            self.btn_ss,
            self.btn_mix,
        )

        self.setup_hotkeys()

    def _dang_ky_goi_y_hover(self, *widgets):
        for widget in widgets:
            if widget:
                widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if hasattr(self, "lbl_goi_y") and isinstance(watched, QPushButton):
            if event.type() == QEvent.Enter:
                tip = watched.toolTip().strip()
                if tip:
                    self.lbl_goi_y.setText(f"Goi y: {tip}")
            elif event.type() == QEvent.Leave:
                self.lbl_goi_y.setText("Re chuot vao nut de xem chuc nang")
        return super().eventFilter(watched, event)

    def _server_dang_ket_noi(self):
        """Quick TCP probe to Flask server port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.35)
        try:
            s.connect(("127.0.0.1", 5000))
            return True
        except OSError:
            return False
        finally:
            try:
                s.close()
            except OSError:
                pass

    def _cap_nhat_nut_server(self):
        if not hasattr(self, "lbl_server_status"):
            return

        self.lbl_server_status.setStyleSheet("background-color: #ffff00; border-radius: 4px;")
        QApplication.processEvents()

        if self._server_dang_ket_noi():
            self.lbl_server_status.setStyleSheet("background-color: #00ff41; border-radius: 4px;")
        else:
            self.lbl_server_status.setStyleSheet("background-color: #ff3333; border-radius: 4px;")

    def toggle_section(self, container, header_btn):
        is_visible = container.isVisible()
        container.setVisible(not is_visible)
        text = header_btn.text().strip()
        if text.startswith((">", "▼", "∨")):
            text = text[1:].strip()

        if is_visible:
            header_btn.setText(f"> {text}")
        else:
            header_btn.setText(f"▼ {text}")
        
        # Adjust window height based on content
        QTimer.singleShot(10, self.adjust_window_size)

    def adjust_window_size(self):
        pass
    
    def setup_tray_icon(self):
        """Setup system tray icon for minimize to tray"""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon from emoji/text
        icon_pixmap = QPixmap(64, 64)
        icon_pixmap.fill(Qt.transparent)
        
        painter = QPainter(icon_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background circle
        painter.setBrush(QColor("#080018"))  # Dark purple
        painter.setPen(QPen(QColor("#00ff41"), 3))  # Neon green border
        painter.drawEllipse(4, 4, 56, 56)
        
        # Draw "TX" text
        painter.setPen(QColor("#00ff41"))
        font = QFont("Consolas", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(icon_pixmap.rect(), Qt.AlignCenter, "TX")
        
        painter.end()
        
        self.tray_icon.setIcon(QIcon(icon_pixmap))
        self.tray_icon.setToolTip("Bang dieu khien theu TX")
        
        # Create context menu
        tray_menu = QMenu()
        
        show_action = QAction("Hien cua so", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Thoat", self)
        exit_action.triggered.connect(self.close)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        
        # Double-click to restore
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        
        # Show tray icon immediately and keep it visible
        self.tray_icon.show()
    
    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation (click/double-click)"""
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show_from_tray()
    
    def show_from_tray(self):
        """Show window from system tray"""
        self.showNormal()
        self.activateWindow()
        self.raise_()
    
    def on_minimize_to_tray(self):
        """Minimize window to system tray"""
        self.hide()
        
    def on_instance_requested(self):
        """Called when a new instance is started"""
        self.on_reset() # Reset all data
        self.show_from_tray() # Show and activate window
        self.flash_status("INST RESET", "#00ffff")

    def changeEvent(self, event):
        """Handle window state changes (minimize, etc.)"""
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                # If minimized via OS taskbar button
                self.on_minimize_to_tray()
                return
        super().changeEvent(event)

    def _handle_hotkey_on_main_thread(self, action):
        try:
            if action == 'alt+v':
                self.hotkey_copy_path()
            elif action == 'alt+e':
                self.hotkey_open_folder()
            elif action == 'alt+c':
                self.hotkey_copy_name()
            elif action == 'alt+b':
                self.on_screenshot_v4()
            elif action == 'ctrl+b':
                self.hotkey_run_auto()
            elif action == 'ctrl+shift+b':
                self.hotkey_run_auto_fast()
            elif action == 'ctrl+shift+v':
                self.hotkey_copy_mix()
            elif action == 'ctrl+r':
                self.hotkey_reset_data()
            elif action == 'ctrl+space':
                self.on_auto_click()
            elif action == 'ctrl+x':
                self.on_close_ultimate_app()
            elif action == 'ctrl+alt+e':
                self.hotkey_open_folder()
            elif action == 'ctrl+m':
                self.hotkey_open_last_screenshot()
            elif action == 'ctrl+alt+x':
                self.exit_all_apps()
            elif action == 'ctrl+h':
                self.hotkey_show_hack_menu()
            elif action == 'ctrl+q':
                self.emergency_stop()
            elif action == 'insert':
                self.hotkey_toggle_visibility()
            elif action == 'alt+i':
                self.on_view_image_clicked()
        except Exception as e:
            print(f"Error handling hotkey {action} on main thread: {e}")

    def safe_trigger_event(self, event):
        """Handle key event safely on main thread and filter out keypad 0"""
        if event.name == 'insert' and not event.is_keypad:
            self.hotkey_triggered_signal.emit('insert')

    def setup_hotkeys(self):
        """Setup global hotkeys for the application"""
        # Prevent duplicate registration
        if hasattr(self, '_hotkeys_registered'):
            print("Hotkeys already registered, skipping...")
            return
            
        try:
            keyboard.add_hotkey('alt+v', lambda: self.hotkey_triggered_signal.emit('alt+v'))
            keyboard.add_hotkey('alt+e', lambda: self.hotkey_triggered_signal.emit('alt+e'))
            keyboard.add_hotkey('alt+c', lambda: self.hotkey_triggered_signal.emit('alt+c'))
            keyboard.add_hotkey('alt+b', lambda: self.hotkey_triggered_signal.emit('alt+b'))
            keyboard.add_hotkey('ctrl+b', lambda: self.hotkey_triggered_signal.emit('ctrl+b'))
            keyboard.add_hotkey('ctrl+shift+b', lambda: self.hotkey_triggered_signal.emit('ctrl+shift+b'))
            keyboard.add_hotkey('ctrl+shift+v', lambda: self.hotkey_triggered_signal.emit('ctrl+shift+v'))
            keyboard.add_hotkey('ctrl+r', lambda: self.hotkey_triggered_signal.emit('ctrl+r'))
            keyboard.add_hotkey('ctrl+space', lambda: self.hotkey_triggered_signal.emit('ctrl+space'))
            keyboard.add_hotkey('ctrl+x', lambda: self.hotkey_triggered_signal.emit('ctrl+x'))
            keyboard.add_hotkey('ctrl+alt+e', lambda: self.hotkey_triggered_signal.emit('ctrl+alt+e'))
            keyboard.add_hotkey('ctrl+m', lambda: self.hotkey_triggered_signal.emit('ctrl+m'))
            keyboard.add_hotkey('ctrl+alt+x', lambda: self.hotkey_triggered_signal.emit('ctrl+alt+x'))
            keyboard.add_hotkey('ctrl+h', lambda: self.hotkey_triggered_signal.emit('ctrl+h'))
            keyboard.add_hotkey('ctrl+q', lambda: self.hotkey_triggered_signal.emit('ctrl+q'))
            keyboard.add_hotkey('alt+i', lambda: self.hotkey_triggered_signal.emit('alt+i'))
            
            # Use on_press_key for 'insert' key to hook events with event argument to filter out Numpad 0
            keyboard.on_press_key('insert', self.safe_trigger_event)
            
            self._hotkeys_registered = True
            print("Hotkeys registered safely with main-thread marshalling. Insert key NumPad 0 filter active.")
        except Exception as e:
            print(f"Hotkey registration error: {e}")

    def emergency_stop(self):
        """Emergency stop of automated workflow (Ctrl+Q)"""
        if hasattr(self, 'current_workflow') and self.current_workflow:
            self.current_workflow.abort_flag = True
        self.flash_status("STOPPED", "#ff3333")
        print("[GUI] Emergency stop triggered via Ctrl+Q")

    def _ensure_current_folder_for_hotkey(self):
        """Ensure current order folder exists for hotkey actions."""
        if self.current_folder and os.path.exists(self.current_folder):
            return self.current_folder

        oid = self.current_data.get('order_id', 'Unknown')
        if not oid or oid == 'Unknown':
            return None

        path, _ = logic.create_order_folder(self._save_folder, oid)
        if path:
            self.current_folder = path
            self.btn_folder.setStyleSheet("QPushButton { background: #153126; border: 1px solid #00ff41; border-radius: 4px; color: #00ff41; font-size: 16px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        return path

    def hotkey_copy_path(self):
        target_folder = self._ensure_current_folder_for_hotkey()
        if target_folder:
            logic.copy_to_clipboard(target_folder)
            self.flash_status("PATH")
        else:
            self.flash_status("Chua co thu muc", "#ffc172")
    
    def hotkey_copy_name(self):
        self.copy_data("id")

    def hotkey_run_auto(self):
        """Run auto workflow (Ctrl+B)."""
        self.on_auto_click()

    def hotkey_run_auto_fast(self):
        """Run auto workflow using alternate key (Ctrl+Shift+B)."""
        self.on_auto_click()

    def hotkey_copy_mix(self):
        """Copy mixed ID with checked positions (Ctrl+Shift+V)."""
        self.copy_data("mix")

    def hotkey_reset_data(self):
        """Quick reset current data (Ctrl+R)."""
        self.on_reset()
        self.flash_status("RESET", "#b7c2ca")

    def hotkey_open_folder(self):
        """Open current folder in Explorer (Alt+E / Ctrl+Alt+E)."""
        target_folder = self._ensure_current_folder_for_hotkey()
        if target_folder and os.path.exists(target_folder):
            os.startfile(target_folder)
            self.flash_status("Mo thu muc", "#58d7a1")
        else:
            self.flash_status("Chua co thu muc", "#ffc172")

    def hotkey_open_last_screenshot(self):
        """Open last captured screenshot (Ctrl+M)"""
        if self.last_screenshot_path and os.path.exists(self.last_screenshot_path):
            os.startfile(self.last_screenshot_path)
            self.flash_status("Mo anh chup", "#58d7a1")
        else:
            self.flash_status("Chua co anh chup", "#ffc172")
            
    def hotkey_toggle_shortcut_panel(self):
        """Toggle shortcuts panel (Insert)."""
        self.hotkey_show_hack_menu()

    def hotkey_toggle_visibility(self):
        """Toggle visibility of the main tool window (Insert)"""
        if self.isVisible():
            self.on_minimize_to_tray()
        else:
            self.show_from_tray()

    def hotkey_show_hack_menu(self):
        """Show/Hide Hack Menu (Ctrl+H)"""
        if hasattr(self, '_hack_menu_win') and self._hack_menu_win and self._hack_menu_win.isVisible():
            self._hack_menu_win.close()
            self._hack_menu_win = None
            return
            
        self._hack_menu_win = HackMenuDialog(self)
        # Position at center of screen or near main window
        if self.isVisible():
            self._hack_menu_win.move(self.x() - 100, self.y() - 50)
        self._hack_menu_win.show()
    
    def on_checkbox_clicked(self, selected_key):
        """Exclusive checkbox selection - only one can be checked"""
        # Uncheck all others when one is checked
        for key, chk in self.chk_groups.items():
            if key != selected_key and chk.isVisible():
                chk.setChecked(False)

    def copy_data(self, field):
        text = "-"
        base_id = self.current_data.get('order_id', '')
        
        if field == "id":
             # Just ID
             text = base_id
                     
        elif field == "mix":
             target_folder = self._ensure_current_folder_for_hotkey()
             if target_folder:
                 text = target_folder
             else:
                 text = "-"
        
        elif field == "mode":
             text = self.current_data.get('mode', '')
        elif field == "badge":
            text = self.current_data.get('size', '')

    def find_wilcom_hwnd(self):
        """Find the Wilcom window HWND, searching by keywords or child class name."""
        if not HAS_WIN32:
            return None
        search_keywords = ["Ultimate Special", "[Ultimate", "Embroid", "Wilcom", "Tajima", "Pulse"]
        hwnd = None
        
        # 1. Search by title keywords
        def enum_handler(h, _):
            nonlocal hwnd
            if hwnd:
                return
            if not win32gui.IsWindowVisible(h):
                return
            title = win32gui.GetWindowText(h)
            if title and any(kw in title for kw in search_keywords):
                if 'TX Embroider' not in title and 'TX EMBROIDER' not in title:
                    hwnd = h
        win32gui.EnumWindows(enum_handler, None)
        if hwnd:
            return hwnd
            
        # 2. Fallback: Search for any window that has a child of class "AfxFrameOrView140u"
        def find_child_class(parent_h):
            found = False
            def check_child(child_h, _):
                nonlocal found
                cls = win32gui.GetClassName(child_h)
                if "AfxFrameOrView140u" in cls or cls.lower() == "afxframeorview140u":
                    found = True
                return not found # stop if found
            try:
                win32gui.EnumChildWindows(parent_h, check_child, None)
            except:
                pass
            return found

        def enum_handler_fallback(h, _):
            nonlocal hwnd
            if hwnd:
                return
            if not win32gui.IsWindowVisible(h):
                return
            if find_child_class(h):
                hwnd = h
                
        win32gui.EnumWindows(enum_handler_fallback, None)
        return hwnd

    def find_wilcom_view_hwnd(self, parent_hwnd):
        """Find child control of class AfxFrameOrView140u (Instance 1)"""
        if not HAS_WIN32:
            return None
        children = []
        def enum_child(hwnd, _):
            cls = win32gui.GetClassName(hwnd)
            if "AfxFrameOrView140u" in cls or cls.lower() == "afxframeorview140u":
                children.append(hwnd)
            return True
        try:
            win32gui.EnumChildWindows(parent_hwnd, enum_child, None)
        except Exception as e:
            print(f"Error enumerating child windows: {e}")
        if children:
            print(f"Found AfxFrameOrView140u view windows: {children}")
            return children[0]  # First instance (AfxFrameOrView140u1)
        return None

    def focus_wilcom_window(self):
        """Find and force-foreground the Ultimate Special Edition window."""
        import ctypes
        hwnd = self.find_wilcom_hwnd()
        if not hwnd:
            return False
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.15)
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_tid, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
            tgt_tid, _ = win32process.GetWindowThreadProcessId(hwnd)
            if fg_tid != tgt_tid:
                ctypes.windll.user32.AttachThreadInput(fg_tid, tgt_tid, True)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            if fg_tid != tgt_tid:
                ctypes.windll.user32.AttachThreadInput(fg_tid, tgt_tid, False)
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f'[DRAG] focus error: {e}')
            return False

    def drop_file_wm(self, hwnd, file_path):
        """Send WM_DROPFILES directly — fastest drag-drop simulation, no mouse needed."""
        import ctypes, struct
        WM_DROPFILES = 0x0233
        GMEM_MOVEABLE = 0x0002
        file_path = os.path.abspath(file_path)
        data = struct.pack('IIIII', 20, 0, 0, 0, 1) + (file_path + '\x00\x00').encode('utf-16-le')

        # Allocate a fresh HDROP for every target we try
        def make_hdrop():
            hg = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not hg:
                return None
            pg = ctypes.windll.kernel32.GlobalLock(hg)
            ctypes.memmove(pg, data, len(data))
            ctypes.windll.kernel32.GlobalUnlock(hg)
            return hg

        # Build target list: main window + all children
        targets = [hwnd]
        def collect(h, lst):
            lst.append(h)
        try:
            win32gui.EnumChildWindows(hwnd, collect, targets)
        except:
            pass

        for t in targets:
            hg = make_hdrop()
            if hg:
                ctypes.windll.user32.SendMessageW(t, WM_DROPFILES, hg, 0)
        return True

    def drop_file_mouse(self, file_path, target_hwnd):
        """Drag a file into a window using real mouse movement (pyautogui)."""
        import subprocess
        try:
            rect = win32gui.GetWindowRect(target_hwnd)
            dst_x = (rect[0] + rect[2]) // 2
            dst_y = (rect[1] + rect[3]) // 2

            # Open Explorer showing the file (selected) so we have a drag source
            subprocess.Popen(f'explorer /select,"{os.path.abspath(file_path)}"', shell=True)
            time.sleep(1.0)

            # Find the Explorer window
            exp_hwnd = None
            fname = os.path.basename(file_path)
            def find_exp(h, _):
                nonlocal exp_hwnd
                if exp_hwnd or not win32gui.IsWindowVisible(h):
                    return
                t = win32gui.GetWindowText(h)
                cls = win32gui.GetClassName(h)
                if ('Desktop' in t or fname in t) and 'Cabinet' in cls:
                    exp_hwnd = h
            win32gui.EnumWindows(find_exp, None)

            if not exp_hwnd:
                return False

            erect = win32gui.GetWindowRect(exp_hwnd)
            src_x = (erect[0] + erect[2]) // 2
            src_y = (erect[1] + erect[3]) // 2

            win32gui.SetForegroundWindow(exp_hwnd)
            time.sleep(0.3)

            pyautogui.moveTo(src_x, src_y, duration=0.05)
            pyautogui.mouseDown()
            time.sleep(0.1)
            pyautogui.moveTo(dst_x, dst_y, duration=0.25)
            time.sleep(0.1)
            pyautogui.mouseUp()
            time.sleep(0.2)

            try:
                win32gui.PostMessage(exp_hwnd, 0x0010, 0, 0)  # WM_CLOSE
            except:
                pass
            return True
        except Exception as e:
            print(f'[DRAG] mouse drag error: {e}')
            return False

    def on_view_image_clicked(self):
        """Display or update the live Order Details Viewer window"""
        if not hasattr(self, 'preview_window') or self.preview_window is None:
            # Create a new non-modal dialog passing the whole current_data dict
            self.preview_window = ImagePreviewDialog(self.current_data, self)
            self.preview_window.finished.connect(self._on_preview_window_finished)
            self.preview_window.show()
        else:
            # Update the existing open window with the current data
            self.preview_window.update_order_data(self.current_data)
            self.preview_window.raise_()
            self.preview_window.activateWindow()

    def _on_preview_window_finished(self):
        # Clean up reference when closed
        self.preview_window = None

    def flash_status(self, text, color="#00ff41"):
        # Emit signal to update UI from Main Thread
        self.update_status_signal.emit(text, color)

    @Slot(str, str)
    def _flash_status_safe(self, text, color):
        # Actual UI Update (Must run on Main Thread)
        orig = getattr(self.lbl_id, 'original_text', 'WAITING...')
        self.lbl_id.scroll_timer.stop()
        self.lbl_id.setText(f"[{text}]")
        self.lbl_id.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
        QTimer.singleShot(800, lambda: self._reset_id_label(orig))
    
    def _reset_id_label(self, text):
        self.lbl_id.original_text = text
        self.lbl_id.setText(text)
        self.lbl_id.setStyleSheet("color: #f3fcff; font-size: 13px; font-weight: bold;")
        self.lbl_id.scroll_timer.start(150)
    
    def on_screenshot_click(self):
        """Handle screenshot button clicks - single or double"""
        self.screenshot_clicks += 1
        
        if self.screenshot_clicks == 1:
            # Start timer for double-click detection
            self.screenshot_timer.start(300)  # 300ms window
        elif self.screenshot_clicks == 2:
            # Double click detected
            self.screenshot_timer.stop()
            self.screenshot_clicks = 0
            self.handle_screenshot_region()
    
    def handle_screenshot_single(self):
        """Single click - capture focused window"""
        self.screenshot_clicks = 0
        self.on_screenshot_v4()  # Use existing window capture
    
    def handle_screenshot_region(self):
        """Double click - region selection"""
        if not self.current_folder:
            print("No folder created yet")
            return
        
        # Use pyautogui region selector
        import pyautogui
        try:
            # Hide window temporarily
            self.hide()
            time.sleep(0.5)
            
            # For now, capture full screen and user capture
            screenshot = pyautogui.screenshot()
            
            # Generate filename using last copied data
            name_base = getattr(self, 'last_copied', self.current_data.get('order_id', 'screenshot'))
            name_base = name_base.replace('/', '-').replace('\\', '-')[:50]
            
            timestamp = time.strftime("%H%M%S")
            filename = f"REGION_{name_base}_{timestamp}.png"
            filepath = os.path.join(self.current_folder, filename)
            
            screenshot.save(filepath)
            print(f"Region screenshot saved: {filepath}")
            
            self.show()
        except Exception as e:
            print(f"Region screenshot error: {e}")
            self.show()
    


    def on_reset(self):
        """Reset all data and checkboxes"""
        self.current_data = {}
        self.order_queue = []
        self.order_history = []
        self.lbl_id.original_text = "WAITING DATA..."
        self.lbl_id.setText("WAITING DATA...")
        self.btn_mode.setText("WAITING...")
        self.btn_badge.setText("DST | 2x2 inches")
        self.btn_badge.setStyleSheet("""
            background: #440000;
            color: #ff003c;
            border: 1px solid #ff003c;
            border-radius: 6px;
            font-weight: bold;
            font-size: 10px;
            padding: 2px;
        """)
        
        # Hide all checkboxes
        for chk in self.chk_groups.values():
            chk.setChecked(False)
            chk.setVisible(False)
        
        # Reset folder
        self.current_folder = None
        self.btn_folder.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ffcc00; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")

    def on_reload_db(self):
        count = logic.reload_dimensions_db()
        self.flash_status(f"DB:{count}", "#00ffff")

    def _load_save_folder(self):
        """Load saved folder path from config, default to Desktop"""
        import json
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                folder = cfg.get('save_folder', desktop)
                if os.path.isdir(folder):
                    return folder
        except Exception:
            pass
        return desktop

    def _save_save_folder(self, folder):
        """Persist the save folder path to config"""
        import json
        try:
            cfg = {}
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            cfg['save_folder'] = folder
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def _handle_folder_single_click(self):
        """Single-click: open/create folder as before"""
        self._folder_clicks = 0
        self._do_open_or_create_folder()

    def _launch_exe_silent(self, exe_path):
        """Launch an EXE without showing a black console window, keeping GUI visible"""
        import subprocess
        subprocess.Popen(
            [exe_path],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def on_in_click(self):
        """Chức năng xuất file cắt của in cho đơn hiện tại - mặc định lấy 2.png từ Desktop và xuất ra Desktop"""
        oid = self.current_data.get('order_id', 'Unknown') if hasattr(self, 'current_data') and self.current_data else 'Unknown'
        if not oid or oid == 'Unknown':
            self.flash_status("NO ORDER", "#ff3333")
            return
            
        # Find checked checkbox
        checked_pos = ""
        for key, chk in self.chk_groups.items():
            if chk.isVisible() and chk.isChecked():
                checked_pos = key
                break
                
        if not checked_pos:
            # Fallback to the first visible checkbox
            for key, chk in self.chk_groups.items():
                if chk.isVisible():
                    checked_pos = key
                    chk.setChecked(True)
                    break
                    
        if not checked_pos:
            # Last resort fallback: default to '4'
            checked_pos = '4'
            if '4' in self.chk_groups:
                self.chk_groups['4'].setVisible(True)
                self.chk_groups['4'].setChecked(True)
            
        # Mặc định lấy file 2.png ở desktop
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        src_png = os.path.join(desktop, '2.png')
        if not os.path.exists(src_png):
            src_png = os.path.join(desktop, '2.PNG')
            
        if not os.path.exists(src_png):
            self.flash_status("NO 2.PNG ON DESKTOP", "#ff3333")
            print(f"[IN] 2.png not found on Desktop.")
            return
            
        dxf_name = f"{oid}_({checked_pos}).dxf"
        dxf_name = dxf_name.replace('/', '-').replace('\\', '-')
        dxf_path = os.path.join(desktop, dxf_name)
        
        try:
            self.perform_png_to_dxf(src_png, dxf_path)
            
            # Backup to folder if it exists
            if self.current_folder and os.path.exists(self.current_folder):
                import shutil
                backup_path = os.path.join(self.current_folder, dxf_name)
                try:
                    shutil.copy2(dxf_path, backup_path)
                    print(f"[IN] Saved backup DXF to folder: {backup_path}")
                except Exception as eb:
                    print(f"[IN] Backup copy error: {eb}")
                    
            self.flash_status("DXF EXPORTED", "#00ff41")
            self.show_success_toast(f"Đã xuất file cắt: {dxf_name}")
            print(f"[IN] Exported DXF using Desktop 2.png to: {dxf_path}")
        except Exception as e:
            self.flash_status("CONV ERROR", "#ff3333")
            print(f"[IN] Conversion error: {e}")

    def exit_all_apps(self):
        """Emergency exit: terminates all related tools and python processes, then exits"""
        print("Ctrl+Alt+X pressed: Terminating all tools...")
        import subprocess
        import sys
        
        # Kill specific compiled executable names if running
        subprocess.run("taskkill /f /im PS_Auto_GUI.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("taskkill /f /im A-PatchPrint.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Kill python.exe which handles scripts (app.py, main.py, autoluuEMB.py, gui.py)
        # Note: this will also kill the current process since it runs via python.
        subprocess.run("taskkill /f /im python.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Fallback exit
        sys.exit(0)

    def on_open_color_reader(self):
        try:
            from color_reader import ColorReaderDialog
            if not hasattr(self, 'color_dialog') or not self.color_dialog:
                self.color_dialog = ColorReaderDialog(self)
            self.color_dialog.show()
            self.color_dialog.raise_()
            self.color_dialog.activateWindow()
            self.flash_status("Layer Reader", "#ff99ff")
        except Exception as e:
            print(f"Error opening color reader: {e}")
            self.flash_status("ERR COLORREADER", "#ff3333")

    def on_toggle_overlay(self):
        self.overlay_enabled = not getattr(self, 'overlay_enabled', True)
        if not self.overlay_enabled:
            if self.info_overlay.isVisible():
                self.info_overlay.hide()
            self.flash_status("HUD: OFF", "#ff3333")
            if hasattr(self, 'btn_overlay_title'):
                self.btn_overlay_title.setStyleSheet("background: transparent; color: #777; font-size: 8px; font-weight: bold; border: none; padding: 0;")
                self.btn_overlay_title.setToolTip("Enable HUD Overlay")
        else:
            self.flash_status("HUD: ON", "#00ff41")
            if hasattr(self, 'btn_overlay_title'):
                self.btn_overlay_title.setStyleSheet("background: transparent; color: #00ff41; font-size: 8px; font-weight: bold; border: none; padding: 0;")
                self.btn_overlay_title.setToolTip("Disable HUD Overlay")

    def on_show_history(self):
        dialog = OrderHistoryDialog(self)
        dialog.exec()

    def on_toggle_mini_widget(self):
        if not hasattr(self, 'is_mini_widget_mode'):
            self.is_mini_widget_mode = False
        
        if not self.is_mini_widget_mode:
            self.is_mini_widget_mode = True
            self.setFixedSize(165, 36)
            if hasattr(self, 'btn_badge'): self.btn_badge.hide()
            if hasattr(self, 'btn_mode'): self.btn_mode.hide()
            if hasattr(self, 'chk_box_container'): self.chk_box_container.hide()
            if hasattr(self, 'lbl_chu_chay'): self.lbl_chu_chay.setText("MINI WIDGET ⚡")
            self.flash_status("MINI MODE", "#ff00ff")
        else:
            self.is_mini_widget_mode = False
            self.setFixedSize(165, 192)
            if hasattr(self, 'btn_badge'): self.btn_badge.show()
            if hasattr(self, 'btn_mode'): self.btn_mode.show()
            if hasattr(self, 'chk_box_container'): self.chk_box_container.show()
            if hasattr(self, 'lbl_chu_chay'): self.lbl_chu_chay.setText("AI LÀ VUA LÌ ĐÒN ⚡ BEYOND ALL BORDERS ⚡")
            self.flash_status("NORMAL MODE", "#00ff41")

    def on_toggle_pin(self):
        flags = self.windowFlags()
        if self.is_pinned:
            flags &= ~Qt.WindowStaysOnTopHint
            self.is_pinned = False
            if hasattr(self, 'btn_pin') and self.btn_pin:
                self.btn_pin.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ff3333; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
            if hasattr(self, 'btn_pin_title'):
                self.btn_pin_title.setStyleSheet("background: transparent; color: #777; font-size: 8px; font-weight: bold; border: none; padding: 0;")
            if hasattr(self, 'btn_pin') and self.btn_pin:
                self.btn_pin.setToolTip("Pin Always on Top (OFF)")
        else:
            flags |= Qt.WindowStaysOnTopHint
            self.is_pinned = True
            if hasattr(self, 'btn_pin') and self.btn_pin:
                self.btn_pin.setStyleSheet("QPushButton { background: #153126; border: 1px solid #00ff41; border-radius: 4px; color: #ff3333; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
            if hasattr(self, 'btn_pin_title'):
                self.btn_pin_title.setStyleSheet("background: transparent; color: #ff3333; font-size: 8px; font-weight: bold; border: none; padding: 0;")
            if hasattr(self, 'btn_pin') and self.btn_pin:
                self.btn_pin.setToolTip("Pin Always on Top (ON)")
            
        self.setWindowFlags(flags)
        self.show()
    
    def on_toggle_pin_corner(self):
        self.on_toggle_pin()

    def auto_folder_dialog_detector(self):
        if not HAS_WIN32:
            return
            
        import win32gui
        import win32con
        import time
        import pyperclip
        import pyautogui

        handled_hwnds = set()
        
        while not getattr(self, 'is_closing', False):
            time.sleep(0.15) # Quick poll rate
            if not self.current_folder or not os.path.exists(self.current_folder):
                continue

            # Enum all visible #32770 dialogs
            def enum_windows_callback(hwnd, extra):
                if win32gui.GetClassName(hwnd) == "#32770" and win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    extra.append((hwnd, title))
                return True

            dialogs = []
            try:
                win32gui.EnumWindows(enum_windows_callback, dialogs)
            except Exception:
                continue

            for hwnd, title in dialogs:
                if hwnd in handled_hwnds:
                    continue

                title_lower = title.lower()
                
                # Case 1: Select Folder Dialog
                if "chọn thư mục" in title_lower or "select folder" in title_lower or "tải lên thư mục" in title_lower or "upload folder" in title_lower:
                    print(f"[DIALOG 1] Found Folder Dialog HWND: {hwnd}, Title: '{title}'")
                    handled_hwnds.add(hwnd)
                    try:
                        folder_path = os.path.abspath(self.current_folder)
                        pyperclip.copy(folder_path)
                        
                        # Bring dialog window to foreground
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.15)
                        
                        # Swift path entry: Ctrl+L -> Ctrl+V -> Enter
                        pyautogui.hotkey('ctrl', 'l')
                        time.sleep(0.1)
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(0.1)
                        pyautogui.press('enter')
                        time.sleep(0.3) # Wait for navigation inside the folder
                        
                        # Submit selection: press Enter again to choose the folder
                        pyautogui.press('enter')
                        print(f"[DIALOG 1] Navigation and selection submitted for HWND: {hwnd}")
                    except Exception as e:
                        print(f"[DIALOG 1] Error: {e}")
                        handled_hwnds.discard(hwnd)
                        
                # Case 2: Confirmation warning dialog (Tải các tệp lên?, Tải lên?, Upload tệp?, etc.)
                elif "tải" in title_lower or "upload" in title_lower or "confir" in title_lower or "xác nhận" in title_lower:
                    print(f"[DIALOG 2] Found Confirmation Dialog HWND: {hwnd}, Title: '{title}'")
                    handled_hwnds.add(hwnd)
                    try:
                        # Bring confirmation dialog to foreground
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.15)
                        
                        # Press Enter or Alt+T/Alt+U to confirm upload
                        pyautogui.press('enter')
                        time.sleep(0.1)
                        pyautogui.hotkey('alt', 't')
                        time.sleep(0.1)
                        pyautogui.hotkey('alt', 'u')
                        print(f"[DIALOG 2] Confirmation submitted for HWND: {hwnd}")
                    except Exception as e:
                        print(f"[DIALOG 2] Error: {e}")
                        handled_hwnds.discard(hwnd)

    # on_toggle_expand removed per user request for list style UI

    @Slot(dict)
    def update_data(self, data):
        try:
            parsed = logic.parse_details(data)
            oid = parsed.get('order_id', 'Unknown')
            if not oid or oid == 'Unknown':
                return

            # Replace the entire queue with this single active order
            self.order_queue = [parsed]
            print(f"[QUEUE] Loaded single active order {oid}.")
            order_db.add_order(parsed)
            self.show_order(parsed)
        except Exception as e:
            # Prevent entire app crash on bad incoming data from browser
            try:
                print(f"[GUI] update_data parse error (suppressed): {e}")
                self.flash_status("PARSE ERR", "#ff5555")
            except Exception:
                pass

    def show_order(self, order_data):
        self.current_data = order_data
        
        oid = self.current_data.get('order_id', 'Unknown')
        f_type = self.current_data.get('file_type', 'UNK')
        size = self.current_data.get('size', '-')
        mode = self.current_data.get('mode', '-')
        positions = self.current_data.get('positions', [])

        # Update ID label with scrolling
        self.lbl_id.original_text = oid
        self.lbl_id.setText(oid)
        self.lbl_id.scroll_pos = 0  # Reset scroll position
        
        thread_color = self.current_data.get('thread_color', '-')
        mode_text = mode if mode else "-"
        if thread_color and thread_color != "-":
            mode_text += f" ({thread_color})"
        self.btn_mode.setText(mode_text)
        
        # Add Dims if available
        dims = self.current_data.get('dims', '')
        badge_text = f"{f_type} | {size}"
        if dims:
            badge_text += f" | {dims}"
        if thread_color and thread_color != "-":
            badge_text += f" | {thread_color}"
            
        self.btn_badge.setText(badge_text)
        
        # Checkbox Logic: Only show (Visible) but DO NOT CHECK (Values=False)
        for chk in self.chk_groups.values():
            chk.setChecked(False) # All Unchecked by default
            chk.setVisible(False)
            
        # Show detected
        visible_keys = []
        for pos in positions:
            if pos in self.chk_groups:
                self.chk_groups[pos].setVisible(True)
                visible_keys.append(pos)
        
        # Bỏ chức năng chọn nhiều dữ liệu: Nếu có nhiều hơn 1 vị trí hiển thị, chỉ giữ lại vị trí đầu tiên
        if len(visible_keys) > 1:
            for k in visible_keys[1:]:
                self.chk_groups[k].setVisible(False)
            visible_keys = [visible_keys[0]]
        
        # Auto-check if only 1 checkbox is visible
        if len(visible_keys) == 1:
            self.chk_groups[visible_keys[0]].setChecked(True)
            print(f"[AUTO-CHECK] Only one option '{visible_keys[0]}' - auto-checked")
                
        # Badge Colors
        if "DST" in f_type:
            self.btn_badge.setStyleSheet("""
                background: #440000;
                color: #ff003c;
                border: 1px solid #ff003c;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10px;
                padding: 2px;
            """)
        elif "TBF" in f_type:
            self.btn_badge.setStyleSheet("""
                background: #002200;
                color: #00ff41;
                border: 1px solid #00ff41;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10px;
                padding: 2px;
            """)
        else:
            self.btn_badge.setStyleSheet("""
                background: #111111;
                color: #cccccc;
                border: 1px solid #cccccc;
                border-radius: 6px;
                font-weight: bold;
                font-size: 10px;
                padding: 2px;
            """)
        
        self.current_folder = None 
        self.btn_folder.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #ffcc00; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        
        # Auto-Create Folder when new data arrives (if valid order ID)
        if oid and oid != 'Unknown':
            path, created = logic.create_order_folder(self._save_folder, oid)
            if path:
                self.current_folder = path
                status = "CREATED" if created else "READY"
                print(f"[AUTO-FOLDER] {status}: {path}")
                self.btn_folder.setStyleSheet("QPushButton { background: #153126; border: 1px solid #00ff41; border-radius: 4px; color: #00ff41; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
        
        # Update Overlay Info
        self.info_overlay.update_info(oid, mode, size, f_type, dims, thread_color)
        
        # Update the live order details preview window if it is open
        if hasattr(self, 'preview_window') and self.preview_window is not None:
            self.preview_window.update_order_data(self.current_data)
            
        # Auto-Trigger: Run workflow immediately if enabled and data is valid
        if self.auto_trigger_enabled and oid and oid != 'Unknown':
            print(f"[AUTO-TRIGGER] New data detected: {oid} - Triggering workflow...")
            # Small delay to ensure UI updates complete
            QTimer.singleShot(100, self.on_auto_click)



    def on_download_image_clicked(self, action_type="f11"):
        """Download image directly to Desktop and run f11.atn or pet.atn in Photoshop"""
        image_url = self.current_data.get('image_url', '') if hasattr(self, 'current_data') and self.current_data else ''
        if image_url:
            import html
            image_url = html.unescape(image_url)
            import urllib.request
            try:
                # Save to Desktop using the Order ID as the filename
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                oid = self.current_data.get('order_id', 'Unknown')
                clean_oid = oid.replace('/', '-').replace('\\', '-').replace(':', '-')
                download_path = os.path.join(desktop, f"{clean_oid}.png")
                
                print(f"[DOWNLOAD] Downloading {image_url} to {download_path}")
                # Set user agent to avoid HTTP 403 Forbidden from cloud storage
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
                urllib.request.install_opener(opener)
                
                urllib.request.urlretrieve(image_url, download_path)
                print(f"[DOWNLOAD] Download complete. Running Photoshop ATN action: {action_type}...")
                
                # Run ATN action in Photoshop
                success = self.run_photoshop_processing(download_path, action_type=action_type)
                
                if success:
                    # Backup the downloaded image, 1.png, and 2.png to the folder if it exists
                    if self.current_folder and os.path.exists(self.current_folder):
                        import shutil
                        try:
                            shutil.copy2(download_path, os.path.join(self.current_folder, f"{clean_oid}.png"))
                            desktop_img1 = os.path.join(desktop, '1.png')
                            desktop_img2 = os.path.join(desktop, '2.png')
                            if os.path.exists(desktop_img1):
                                shutil.copy2(desktop_img1, os.path.join(self.current_folder, '1.png'))
                            if os.path.exists(desktop_img2):
                                shutil.copy2(desktop_img2, os.path.join(self.current_folder, '2.png'))
                            print(f"[DOWNLOAD] Backed up downloaded files to folder: {self.current_folder}")
                        except Exception as eb:
                            print(f"[DOWNLOAD] Backup copy error: {eb}")
                            
                    self.flash_status("D-LOAD OK", "#00ff41")
                    self.show_success_toast(f"Đã tải và chạy action {action_type}.atn thành công!")
                    return
                else:
                    raise Exception("Photoshop action automation failed")
                    
            except Exception as e:
                print(f"[DOWNLOAD] Direct download/process failed: {e}. Falling back to WS trigger.")
        
        # Fallback to WS trigger
        if hasattr(self, 'flask_thread') and self.flask_thread:
            self.flask_thread.send_to_ws_clients({"action": f"download_{action_type}"})
            self.flash_status("D-LOAD WS", "#00ffff")
        else:
            self.flash_status("NO WS CONN", "#ff3333")

    def run_photoshop_processing(self, image_path, action_type="f11"):
        """Open image in Photoshop and execute the f11.atn or pet.atn action set."""
        import win32com.client
        import time
        
        abs_image_path = os.path.abspath(image_path)
        if action_type == "pet":
            atn_path = r"c:\Users\Tx\Desktop\vibecoder\ChestEMB\pet.atn"
            action_set = "pet"
            action_name = "tif"
        else:
            atn_path = r"c:\Users\Tx\Desktop\vibecoder\ChestEMB\f11.atn"
            action_set = "f11"
            action_name = "patcher IN copy"
        
        print(f"[PHOTOSHOP] Target image: {abs_image_path}")
        print(f"[PHOTOSHOP] Target ATN: {atn_path} (Set: {action_set}, Action: {action_name})")
        
        try:
            # Connect to Photoshop COM object
            print("[PHOTOSHOP] Dispatching Photoshop.Application...")
            ps = win32com.client.Dispatch("Photoshop.Application")
            
            # Make Photoshop visible
            ps.Visible = True
            
            # Open the downloaded image in Photoshop
            print(f"[PHOTOSHOP] Opening document in Photoshop...")
            doc = ps.Open(abs_image_path)
            time.sleep(1.5) # Give Photoshop enough time to load the document
            
            # Escape path backslashes for JS string literal
            escaped_atn_path = atn_path.replace("\\", "\\\\")
            
            # Prepare Javascript code to play action from the ATN file
            jsx_code = f"""
            var actionSet = "{action_set}";
            var actionName = "{action_name}";
            var atnFilePath = "{escaped_atn_path}";

            try {{
                app.doAction(actionName, actionSet);
            }} catch (e) {{
                var atnFile = new File(atnFilePath);
                if (atnFile.exists) {{
                    app.load(atnFile);
                    app.doAction(actionName, actionSet);
                }} else {{
                    alert("Không tìm thấy file action " + actionSet + ".atn tại: " + atnFilePath);
                }}
            }}
            """
            
            print(f"[PHOTOSHOP] Executing ATN script via JavaScript...")
            ps.DoJavaScript(jsx_code)
            
            # Wait a moment for action to finish and save files
            time.sleep(2.5)
            
            # Close the opened document if it is still open
            try:
                if ps.Documents.Count > 0:
                    ps.ActiveDocument.Close(2) # 2 = PsSaveOptions.psDoNotSaveChanges
            except Exception as e:
                print(f"[PHOTOSHOP] Note when closing document: {e}")
                
            print("[PHOTOSHOP] ATN execution completed.")
            return True
            
        except Exception as ex:
            import traceback
            print(f"[PHOTOSHOP] COM Automation error: {ex}")
            traceback.print_exc()
            return False

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.png'):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.png'):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if filepath.lower().endswith('.png'):
                    self.handle_png_drop(filepath)
                    break

    def handle_png_drop(self, png_path):
        import re
        # Resolve target directory
        if self.current_folder and os.path.exists(self.current_folder):
            target_dir = self.current_folder
        else:
            # Fallback to the same folder as the dropped PNG file
            target_dir = os.path.dirname(png_path)
            
        oid = self.current_data.get('order_id', 'Unknown')
        if not oid or oid == 'Unknown':
            # Try to parse order ID from the dropped PNG file name
            base_name = os.path.splitext(os.path.basename(png_path))[0]
            oid_match = re.search(r'\d[\w\d]*-[\w\d-]+', base_name)
            if oid_match:
                oid = oid_match.group(0)
            else:
                parts = re.split(r'[_(\s]', base_name)
                if parts and parts[0]:
                    oid = parts[0]
                else:
                    oid = base_name
                    
        checked_pos = ""
        for key, chk in self.chk_groups.items():
            if chk.isVisible() and chk.isChecked():
                checked_pos = key
                break
                
        # If no checkbox is checked, try to guess or use the first visible one
        if not checked_pos:
            # Try to extract from the dropped filename
            filename_lower = os.path.basename(png_path).lower()
            for key, chk in self.chk_groups.items():
                if chk.isVisible() and (f"({key})" in filename_lower or f"_{key}" in filename_lower):
                    checked_pos = key
                    chk.setChecked(True)
                    break
                    
        if not checked_pos:
            # Fallback to the first visible checkbox
            for key, chk in self.chk_groups.items():
                if chk.isVisible():
                    checked_pos = key
                    chk.setChecked(True)
                    break
                    
        if not checked_pos:
            # Last resort fallback: default to '4'
            checked_pos = '4'
            if '4' in self.chk_groups:
                self.chk_groups['4'].setVisible(True)
                self.chk_groups['4'].setChecked(True)
                
        dxf_name = f"{oid}_({checked_pos}).dxf"
        dxf_name = dxf_name.replace('/', '-').replace('\\', '-')
        dxf_path = os.path.join(target_dir, dxf_name)
        
        try:
            self.perform_png_to_dxf(png_path, dxf_path)
            self.flash_status("DXF EXPORTED", "#00ff41")
            self.show_success_toast(f"Đã xuất file cắt: {dxf_name}")
            print(f"[DROP] Exported DXF to: {dxf_path}")
        except Exception as e:
            self.flash_status("CONV ERROR", "#ff3333")
            print(f"[DROP] Conversion error: {e}")

    def parse_target_dims(self):
        """Parse physical dimensions (width, height) in mm from the current order data"""
        import re
        if not hasattr(self, 'current_data') or not self.current_data:
            return None
            
        dims_str = self.current_data.get('dims', '')
        size_str = self.current_data.get('size', '')
        
        # 1. Try dims first (e.g. "80x80mm", "100x80", "40x50cm")
        if dims_str:
            m = re.search(r'([\d.]+)\s*[xX]\s*([\d.]+)\s*(mm|cm|inch|in|")?', dims_str)
            if m:
                val1 = float(m.group(1))
                val2 = float(m.group(2))
                unit = m.group(3)
                if not unit:
                    if "cm" in dims_str.lower(): unit = "cm"
                    elif "inch" in dims_str.lower() or "in" in dims_str.lower() or '"' in dims_str.lower(): unit = "inch"
                    else: unit = "mm"
                    
                if unit.lower() in ["inch", "in", '"']:
                    val1 *= 25.4
                    val2 *= 25.4
                elif unit.lower() == "cm":
                    val1 *= 10.0
                
                # In dimensions string (H x W), val1 is Height, val2 is Width
                # Return (width, height)
                return val2, val1
                
        # 2. Try size next (e.g. "3.5", "3.5 inches", "8cm")
        if size_str:
            m = re.search(r'([\d.]+)\s*(mm|cm|inch|in|")?', size_str)
            if m:
                val = float(m.group(1))
                unit = m.group(2)
                if not unit:
                    if "cm" in size_str.lower(): unit = "cm"
                    elif "inch" in size_str.lower() or "in" in size_str.lower() or '"' in size_str.lower(): unit = "inch"
                    else:
                        unit = "inch" if val < 15.0 else "mm"
                        
                if unit.lower() in ["inch", "in", '"']:
                    val_mm = val * 25.4
                elif unit.lower() == "cm":
                    val_mm = val * 10.0
                else:
                    val_mm = val
                    
                # Return width = height = val_mm (square/circle target)
                return val_mm, val_mm
                
        return None

    def perform_png_to_dxf(self, png_path, dxf_path):
        """Convert PNG outlines to DXF closed polylines (scaled to match physical dimensions in mm)"""
        import cv2
        import numpy as np
        import traceback
        
        try:
            print(f"[CONVERT] Reading PNG: {png_path}")
            # Unicode-safe read for Windows
            img_array = np.fromfile(png_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
            
            if img is None:
                raise Exception("Cannot read PNG image (imdecode returned None)")
                
            print(f"[CONVERT] Image shape: {img.shape}")
            # Extract binary contour mask
            has_transparency = False
            if img.shape[-1] == 4:
                alpha = img[:, :, 3]
                # Check if alpha channel actually has transparent/semi-transparent pixels
                if alpha.min() < 250 and (alpha.max() - alpha.min() > 10):
                    has_transparency = True
                    _, thresh = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
                    print("[CONVERT] Using alpha channel for transparency")
            
            if not has_transparency:
                print("[CONVERT] Using BGR grayscale thresholding")
                if img.shape[-1] == 4:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                else:
                    img_rgb = img
                    
                gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
                # Detect non-white pixels (the shape)
                _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
                if np.mean(thresh) > 127:
                    thresh = cv2.bitwise_not(thresh)
                    
            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"[CONVERT] Found {len(contours)} contours")
            
            # 1. Calculate bounding box of all contours in pixels
            all_pts = []
            for contour in contours:
                for pt in contour:
                    all_pts.append(pt[0])
            
            if all_pts:
                all_pts = np.array(all_pts)
                min_x, min_y = all_pts.min(axis=0)
                max_x, max_y = all_pts.max(axis=0)
                width_px = max_x - min_x
                height_px = max_y - min_y
                if width_px == 0: width_px = 1
                if height_px == 0: height_px = 1
            else:
                min_x, min_y = 0, 0
                max_x, max_y = 1, 1
                width_px, height_px = 1, 1
                
            # 2. Determine physical target size in mm
            target_dims = self.parse_target_dims()
            if target_dims:
                target_w, target_h = target_dims
                scale_w = target_w / width_px
                scale_h = target_h / height_px
                print(f"[CONVERT] Bounding box pixel size: {width_px}x{height_px}. Physical target: {target_w:.2f}mm x {target_h:.2f}mm. Scale factor: W={scale_w:.4f}, H={scale_h:.4f}")
            else:
                # Default scale fallback: 1 pixel = 0.1 mm
                scale_w = 0.1
                scale_h = 0.1
                print(f"[CONVERT] Warning: Could not parse physical dimensions. Defaulting to 1 px = 0.1 mm scale.")
            
            # Save to DXF format
            dxf_lines = [
                "  0", "SECTION",
                "  2", "HEADER",
                "  0", "ENDSEC",
                "  0", "SECTION",
                "  2", "ENTITIES"
            ]
            
            handle_val = 256
            for contour in contours:
                if len(contour) < 2:
                    continue
                    
                dxf_lines.extend([
                    "  0", "LWPOLYLINE",
                    "  5", f"{handle_val:X}",
                    "100", "AcDbEntity",
                    "  8", "0",
                    "100", "AcDbPolyline",
                    " 90", str(len(contour)),
                    " 70", "1"
                ])
                handle_val += 1
                
                for pt in contour:
                    x, y = pt[0]
                    # Map to positive quadrant and invert Y so top is higher Y
                    x_scaled = (x - min_x) * scale_w
                    y_scaled = (max_y - y) * scale_h
                    dxf_lines.extend([
                        " 10", f"{x_scaled:.4f}",
                        " 20", f"{y_scaled:.4f}"
                    ])
                    
            dxf_lines.extend([
                "  0", "ENDSEC",
                "  0", "EOF"
            ])
            
            print(f"[CONVERT] Writing DXF: {dxf_path}")
            # Ensure output folder exists
            out_dir = os.path.dirname(dxf_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
                
            with open(dxf_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(dxf_lines) + "\n")
            print("[CONVERT] DXF written successfully")
            
        except Exception as e:
            print(f"[CONVERT] Error: {e}")
            traceback.print_exc()
            raise e
        
        # If in collapsed mode, we might want to temporarily expand or flash?
        # For now, stay in current mode.

    def on_create_folder(self):
        """Handle folder button click — single=open/create, double=change save path"""
        self._folder_clicks += 1
        if self._folder_clicks == 1:
            self._folder_click_timer.start(350)
        elif self._folder_clicks >= 2:
            self._folder_click_timer.stop()
            self._folder_clicks = 0
            self._change_save_folder()

    def _change_save_folder(self):
        """Let user pick a new default save folder (persisted)"""
        new_folder = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục lưu mặc định", self._save_folder
        )
        if new_folder:
            self._save_folder = new_folder
            self._save_save_folder(new_folder)
            self.flash_status("Da doi thu muc luu", "#00ffcc")
            print(f"[SAVE FOLDER] Changed to: {new_folder}")

    def _do_open_or_create_folder(self):
        """Single-click logic: open existing folder or create new one"""
        # If we already have a path tracked, OPEN it
        if self.current_folder and os.path.exists(self.current_folder):
             logic.open_folder(self.current_folder)
             self.flash_status("OPENING...")
             return None

        # Otherwise CREATE/FIND it
        oid = self.current_data.get('order_id')
        if not oid: return None
        
        path, created = logic.create_order_folder(self._save_folder, oid)
        
        if path:
            self.current_folder = path
            self.flash_status("Da san sang thu muc", "#58d7a1")
            self.btn_folder.setStyleSheet("QPushButton { background: #153126; border: 1px solid #00ff41; border-radius: 4px; color: #00ff41; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
            return path
        return None

    def on_screenshot_v4(self):
        """Screenshot của cửa sổ Ultimate Special Edition ONLY"""
        # If folder not known, try to create it first
        oid = self.current_data.get('order_id', 'Unknown')
        
        target_folder = self.current_folder
        
        if not target_folder and oid != 'Unknown':
             # Try auto-create
             desktop = os.path.join(os.path.expanduser("~"), "Desktop")
             path, _ = logic.create_order_folder(desktop, oid)
             if path:
                 self.current_folder = path
                 target_folder = path
        
        # Screenshot cửa sổ embroidery ONLY
        try:
            from auto_workflow import AutoWorkflow
            # Create temp workflow just to use window capture function
            temp_workflow = AutoWorkflow(self, {})
            
            # Find and activate window
            if not temp_workflow.activate_embroidery_window():
                self.flash_status("Khong thay cua so", "#ff7d86")
                return
            
            # Capture window screenshot
            screenshot = temp_workflow.capture_window_screenshot()
            
            # Generate filename (OVERWRITE MODE - No timestamp)
            screenshot_name = self.last_copied if self.last_copied else oid
            screenshot_name = screenshot_name.replace('/', '-').replace('\\', '-')[:50]
            
            filename = f"{screenshot_name}.png"
            
            if target_folder:
                filepath = os.path.join(target_folder, filename)
            else:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                filepath = os.path.join(desktop, filename)
            
            screenshot.save(filepath)
            self.last_screenshot_path = filepath # Save for Ctrl+M preview
            print(f"Window screenshot saved (OVERWRITTEN): {filepath}")
            self.flash_status("Da chup anh", color="#ffffff")
        except Exception as e:
            print(f"Screenshot error: {e}")
            self.flash_status("Loi chup anh", "#ff7d86")

    def on_open_image(self):
        url = self.current_data.get('image_url')
        if not url: return

        # Try to download and show in ImageViewer
        try:
            import urllib.request
            self.flash_status("LOADING...")
            QApplication.processEvents() 
            
            # Simple sync download (fast enough for small images, ideally thread)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = response.read()
                
            # ImageViewer class is missing in provided snippets, assumed handled or not needed for this refactor
            # Since I didn't see ImageViewer in the file outline or content I read, I will omit the viewer part 
            # or assume it was imported but I missed it. 
            # Checking imports... logic doesn't have it. 
            # I will just fallback to browser logic as safety.
            logic.open_image_url(url)
            self.flash_status("VIEWING")
            
        except Exception as e:
            print(f"Image load error: {e}")
            self.flash_status("ERR IMG", "#ff0000")
            logic.open_image_url(url)
        
    def on_auto_click(self):
        """Run automated 3-step workflow"""
        try:
            from auto_workflow import AutoWorkflow
            
            oid = self.current_data.get('order_id', 'Unknown')
            if not oid or oid == 'Unknown':
                self.flash_status("Chua co du lieu", "#ffc172")
                return
            
            # PRE-FETCH DATA ON MAIN THREAD
            # Collect all data needed by the worker thread here
            # to avoid the worker thread accessing widgets (like checkboxes)
            
            # 1. Generate ID with Checkboxes logic
            base_id = oid
            checked = []
            for k in self.all_keys:
                if k in self.chk_groups and self.chk_groups[k].isChecked():
                    checked.append(k)
            
            final_id = base_id
            if checked:
                 checkbox_str = "_".join(checked)
                 final_id = f"{base_id}_({checkbox_str})"

            # 2. Pack Context
            context = {
                'order_id': oid,
                'final_id': final_id,
                'folder_path': self.current_folder,
                'file_type': self.current_data.get('file_type', 'TBF')
            }

            self.flash_status("Dang chay tu dong...", "#58d7a1")
            
            # Create workflow with SAFE context
            # Pass 'self' only for signal emission, NOT for reading widgets
            self.current_workflow = AutoWorkflow(self, context)
            
            import threading
            def run_async():
                time.sleep(0.3)  # Minimal delay for window switching
                self.current_workflow.run()
            
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
            
            # Workflow started: We can assume it finishes. 
            # (Checkbox locking removed per user request)
            
        except Exception as e:
            print(f"Auto workflow error: {e}")
            self.flash_status("Loi tu dong", "#ff7d86")
    
    @Slot(str)
    def show_success_toast(self, message):
        toast = SuccessToast(message, self)
        toast.show()
        # Also show OS system notification (tray message)
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage("TX Embroider Tool", message, QSystemTrayIcon.Information, 2500)

    def lock_checkboxes(self):
        """Black out/Lock checkboxes after auto-run"""
        for cb in self.chk_groups.values():
            cb.setEnabled(False)
            cb.setStyleSheet("QCheckBox { color: #222; font-size: 10px; font-weight: bold; }")
            
    def unlock_checkboxes(self):
        """Restore checkboxes for new data"""
        for cb in self.chk_groups.values():
            cb.setEnabled(True)
            cb.setStyleSheet("QCheckBox { color: #00f3ff; font-size: 10px; font-weight: bold; }")

    def check_export_window(self):
        if not HAS_WIN32:
            return
        
        # Look for window matching the title
        def enum_handler(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                title_lower = title.lower()
                if "export curent" in title_lower or "export current" in title_lower or "export multi-decoration" in title_lower:
                    results.append(hwnd)
        
        results = []
        try:
            win32gui.EnumWindows(enum_handler, results)
        except Exception:
            pass
            
        if results:
            found_hwnd = results[0]
            if getattr(self, 'last_detected_export_hwnd', None) != found_hwnd:
                self.last_detected_export_hwnd = found_hwnd
        else:
            self.last_detected_export_hwnd = None

    def update_overlay_position(self):
        """Sync info overlay with Ultimate window position - ONLY when Active"""
        if not HAS_WIN32: return
        
        # Detect active export window to auto-copy PO folder
        self.check_export_window()
        
        if not getattr(self, 'overlay_enabled', True):
            if self.info_overlay.isVisible():
                self.info_overlay.hide()
            return
        
        target_hwnd = self.find_ultimate_window()
        foreground_hwnd = win32gui.GetForegroundWindow()
        
        # ONLY show if Ultimate is active OR we are active OR tool is active
        # CRITICAL: If Main window is hidden (in tray), only check Ultimate
        our_hwnd = int(self.winId()) if self.isVisible() else 0
        overlay_hwnd = int(self.info_overlay.winId())
        
        is_target_active = (foreground_hwnd == target_hwnd or 
                           (our_hwnd and foreground_hwnd == our_hwnd) or 
                           foreground_hwnd == overlay_hwnd)

        # If docked, we show even if Main App is hidden!
        if not target_hwnd or not is_target_active or (not self.isVisible() and not self.is_docked):
            if self.info_overlay.isVisible(): 
                self.info_overlay.hide()
            return
            
        if not self.info_overlay.isVisible():
            self.info_overlay.show()
            
        try:
            rect = win32gui.GetWindowRect(target_hwnd)
            target_x, target_y, target_x2, target_y2 = rect
            
            # Use smaller fixed width for the overlay to fit narrow windows too
            width = target_x2 - target_x
            overlay_width = 600 # Reduced from 800 for better fit
            self.info_overlay.setFixedWidth(overlay_width)
            
            # Center horizontally
            new_x = target_x + (width - overlay_width) // 2
            # Position for 2-line overlay (42px height)
            new_y = target_y2 - 50 
            
            self.info_overlay.move(new_x, new_y)
        except:
            pass

    def on_close_ultimate_app(self):
        """Tìm và đóng ứng dụng Ultimate Special Edition"""
        hwnd = self.find_ultimate_window()
        if hwnd:
            try:
                # Gửi tin nhắn đóng cửa sổ (tương đương Alt+F4)
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                self.flash_status("CLOSED APP", "#ff4444")
                print(f"Closed Ultimate app window: {hwnd}")
            except Exception as e:
                print(f"Error closing app: {e}")
                self.flash_status("CLOSE ERR", "#ff0000")
        else:
            self.flash_status("NO APP", "#ff8800")
            print("Ultimate app window not found for closing")

    def find_ultimate_window(self):
        """Find Ultimate Special Edition window using win32gui"""
        if not HAS_WIN32:
            print("Win32 not available, docking disabled")
            return None
        
        # List of possible window titles to search for
        possible_titles = [
            "Ultimate Special Edition",
            "[Ultimate Special Edition]",
            "Ultimate Special",
            "[Ultimate Special",
        ]
        
        # Try exact match first (fast path)
        for title in possible_titles:
            try:
                hwnd = win32gui.FindWindow(None, title)
                if hwnd and win32gui.IsWindowVisible(hwnd):
                    print(f"Found Ultimate window: {title}")
                    return hwnd
            except:
                continue
        
        # Try partial match search
        def enum_handler(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "Ultimate" in window_text and "Special" in window_text:
                    # Skip our own window
                    if "TX" not in window_text and "Embroider" not in window_text:
                        results.append(hwnd)
        
        results = []
        try:
            win32gui.EnumWindows(enum_handler, results)
            if results:
                return results[0]
        except:
            pass
        
        return None
    
    def update_dock_position(self):
        """Update position to follow target window (called by timer)"""
        if not self.is_docked or not HAS_WIN32:
            return
        
        # Check if we have a valid window handle
        if not self.target_window_hwnd:
            # Try to find the window
            self.dock_search_attempts += 1
            if self.dock_search_attempts % 10 == 0:  # Every ~1 second
                hwnd = self.find_ultimate_window()
                if hwnd:
                    self.target_window_hwnd = hwnd
                    print("Reconnected to Ultimate window")
                    self.dock_search_attempts = 0
            return
        
        try:
            # Check if window still exists and is visible
            if not win32gui.IsWindow(self.target_window_hwnd):
                print("Target window closed")
                self.target_window_hwnd = None
                return
            
            if win32gui.IsIconic(self.target_window_hwnd):
                # Window is minimized, don't update position
                return
            
            if not win32gui.IsWindowVisible(self.target_window_hwnd):
                # Window is hidden
                return
            
            # Get target window position
            rect = win32gui.GetWindowRect(self.target_window_hwnd)
            target_x, target_y, target_x2, target_y2 = rect
            target_width = target_x2 - target_x
            
            # Calculate new position for MiniApp
            # Position at top-right corner with offset
            new_x = target_x2 + self.dock_offset_x
            new_y = target_y + self.dock_offset_y
            
            # Move to new position
            self.move(new_x, new_y)
            
        except Exception as e:
            print(f"Dock position update error: {e}")
            self.target_window_hwnd = None
    
    def on_toggle_dock(self):
        """Toggle docking to Ultimate Special Edition window"""
        if not HAS_WIN32:
            self.flash_status("Thieu win32", "#ff7d86")
            return
        
        self.is_docked = not self.is_docked
        
        if self.is_docked:
            # Enable docking
            hwnd = self.find_ultimate_window()
            if not hwnd:
                self.flash_status("Khong thay Ultimate", "#ff7d86")
                self.is_docked = False
                return
            
            self.target_window_hwnd = hwnd
            self.dock_search_attempts = 0
            
            # Update button appearance (Neon Glow)
            if hasattr(self, 'btn_dock') and self.btn_dock:
                self.btn_dock.setStyleSheet("QPushButton { background: #153126; border: 1px solid #00ff41; border-radius: 4px; color: #0099ff; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
            if hasattr(self, 'btn_dock_title'):
                self.btn_dock_title.setStyleSheet("background: transparent; color: #00f3ff; font-size: 8px; font-weight: bold; border: none; padding: 0;")
            if hasattr(self, 'btn_dock') and self.btn_dock:
                self.btn_dock.setToolTip("Dock to Embroidery Window (ON)")
            
            # Start timer (100ms = 10 updates per second)
            self.dock_timer.start(100)
            
            # Immediately move to docked position
            self.update_dock_position()
            
            self.flash_status("Da bam vi tri", "#58d7a1")
            print("Docking enabled")
        else:
            # Disable docking
            self.dock_timer.stop()
            self.target_window_hwnd = None
            
            # Update button appearance
            if hasattr(self, 'btn_dock') and self.btn_dock:
                self.btn_dock.setStyleSheet("QPushButton { background: #020502; border: 1px solid #00ff41; border-radius: 4px; color: #0099ff; font-size: 12px; font-weight: bold; } QPushButton:hover { background: #002200; }")
            if hasattr(self, 'btn_dock_title'):
                self.btn_dock_title.setStyleSheet("background: transparent; color: #777; font-size: 8px; font-weight: bold; border: none; padding: 0;")
            if hasattr(self, 'btn_dock') and self.btn_dock:
                self.btn_dock.setToolTip("Dock to Embroidery Window (OFF)")
            
            self.flash_status("Da bo bam vi tri", "#b7c2ca")
            print("Docking disabled")
    
    def closeEvent(self, event):
        keyboard.unhook_all()
        self.dock_timer.stop()
        if hasattr(self, 'server_status_timer'):
            self.server_status_timer.stop()
        self.tray_icon.hide()  # Hide tray icon on exit
        event.accept()
        # Forcibly exit the process to terminate all background threads/Flask server/QLocalServer
        os._exit(0)
