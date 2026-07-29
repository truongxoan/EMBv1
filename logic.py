import os
import webbrowser
import platform
import subprocess
from datetime import datetime
import pyautogui
import pyperclip
from bs4 import BeautifulSoup
import re
import json
import csv

# Cache for dimensions DB
_DIMENSIONS_DB = None


def parse_details(data):
    """
    MASTER PARSER V3: Specific HTML Structure Targeting.
    """
    parsed = {}
    if not isinstance(data, dict):
        data = {}
    parsed['image_url'] = data.get('image_url', '') if isinstance(data, dict) else ''
    
    # 1. Flatten Data to find HTML chunks
    all_values = []
    def extract_strings(obj):
        if isinstance(obj, dict):
            for v in obj.values(): extract_strings(v)
        elif isinstance(obj, list):
            for i in obj: extract_strings(i)
        elif isinstance(obj, str):
            all_values.append(obj)
        elif isinstance(obj, (int, float)):
            all_values.append(str(obj))
            
    extract_strings(data)
    combined_text = " ".join(all_values)
    
    # Extract [SYSTEM] THREAD_COLOR and [SYSTEM] CHOOSE_BACKGROUND_COLOR
    thread_color = "-"
    bg_color = "-"
    
    color_patterns = [
        r'\[SYSTEM\]\s*THREAD_COLOR:\s*([^\n\r<|]+)',
        r'THREAD_COLOR:\s*([^\n\r<|]+)'
    ]
    bg_patterns = [
        r'\[SYSTEM\]\s*CHOOSE_BACKGROUND_COLOR:\s*([^\n\r<|]+)',
        r'CHOOSE_BACKGROUND_COLOR:\s*([^\n\r<|]+)'
    ]
    
    # Try using BeautifulSoup for clean extraction from HTML structure
    try:
        soup_color = BeautifulSoup(combined_text, 'html.parser')
        
        # 1. Thread Color
        span_thread = soup_color.find(lambda tag: tag.name == 'span' and 'THREAD_COLOR' in tag.text)
        if span_thread:
            sibling = span_thread.find_next()
            if sibling:
                txt = ''.join([t for t in sibling.contents if isinstance(t, str)]).strip()
                if txt:
                    thread_color = txt
                    
        # 2. Background Color
        span_bg = soup_color.find(lambda tag: tag.name == 'span' and 'CHOOSE_BACKGROUND_COLOR' in tag.text)
        if span_bg:
            sibling = span_bg.find_next()
            if sibling:
                txt = ''.join([t for t in sibling.contents if isinstance(t, str)]).strip()
                if txt:
                    bg_color = txt
    except Exception as esoup:
        print(f"[PARSER] Soup color parsing exception: {esoup}")

    # Fallback to Regex if still default
    if thread_color == "-":
        for pattern in color_patterns:
            m = re.search(pattern, combined_text, re.IGNORECASE)
            if m:
                thread_color = re.sub(r'<[^>]*>', '', m.group(1)).strip()
                thread_color = " ".join(thread_color.split())
                break
                
    if bg_color == "-":
        for pattern in bg_patterns:
            m = re.search(pattern, combined_text, re.IGNORECASE)
            if m:
                bg_color = re.sub(r'<[^>]*>', '', m.group(1)).strip()
                bg_color = " ".join(bg_color.split())
                break
                
    parsed['thread_color'] = thread_color
    parsed['bg_color'] = bg_color
    
    # 2. Aggressive HTML Parsing
    # We reconstruct a soup from all potential HTML-like strings found
    html_fragments = [v for v in all_values if "<div" in v or "<span" in v or "<td" in v]
    full_html = " ".join(html_fragments)
    
    soup = BeautifulSoup(full_html, 'html.parser')
    
    # A. Product Name & Variant
    # Target: <div class="... text-cyan" ...>Product</div>
    # Variant: Sibling <div ...>Variant</div>
    cyan_divs = soup.find_all('div', class_=lambda x: x and 'text-cyan' in x)
    
    for div in cyan_divs:
        txt = div.get_text(strip=True)
        # Filter out small UI labels if any match text-cyan (e.g. "Copy"?)
        if len(txt) > 3: 
            parsed['product_name'] = txt
            
            # Variant is the next div sibling
            sibling = div.find_next_sibling('div')
            if sibling:
                parsed['variant_info'] = sibling.get_text(strip=True)
            break # Found the most likely product header

    # B. Order ID & File Type
    # Target: <span class="truncate">ID</span> and <span class="truncate">DST/TBF</span>
    spans = soup.find_all('span', class_='truncate')
    
    possible_types = []
    
    for s in spans:
        txt = s.get_text(strip=True)
        
        # Check for ID - must start with a digit (not "WO" or other text prefix)
        # Accept IDs like "111-XXX", "112-...", "3abc-123" but reject "WO-123"
        if '-' in txt and len(txt) > 3 and txt not in ['DST', 'TBF', 'PDF', 'PNG', 'EST']:
            # Must start with a digit
            if txt[0].isdigit():
                parsed['order_id'] = txt
        # Check for Type
        elif txt in ['DST', 'TBF', 'PDF', 'PNG', 'EST']:
            possible_types.append(txt)
            
    if possible_types:
        parsed['file_type'] = possible_types[0]

    # 3. Fallbacks (Regex) if HTML failed
    if 'order_id' not in parsed:
        # Look for IDs starting with digit followed by hyphen (more permissive but must start with number)
        oid_match = re.search(r'\d[\w\d]*-[\w\d-]+', combined_text)
        if oid_match: parsed['order_id'] = oid_match.group(0)
        else: parsed['order_id'] = 'Unknown'

    if 'file_type' not in parsed:
        if "DST" in combined_text: parsed['file_type'] = "DST"
        elif "TBF" in combined_text: parsed['file_type'] = "TBF"
        else: parsed['file_type'] = "UNK"

    if 'product_name' not in parsed:
         # Fallback regex or key
         if isinstance(data, dict):
             parsed['product_name'] = data.get('product_name', '-')
             
    if 'variant_info' not in parsed:
         # Fallback regex for "A / B / C" or "Color / Size"
         # Must avoid matching file paths like "images/designs/..."
         var_match = re.search(r'[\w\s]+\s?/\s?[\w\s]+\s?/\s?[\w\s]+', combined_text)
         
         if var_match:
             candidate = var_match.group(0)
             # Filter out paths/URLs
             is_bad = any(x in candidate.lower() for x in ['http', 'www', '.com', '.net', 'images/', 'content/', '.jpg', '.png', '_'])
             
             if not is_bad and len(candidate) < 50:
                 parsed['variant_info'] = candidate
             else:
                 parsed['variant_info'] = "-"
         else:
             parsed['variant_info'] = "-"

    # 4. Refined Extraction for "Size" and "Mode"
    # User wants: 1. Size, 2. DST/TBF, 3. Product ID, 4. Mode
    
    # Defaults
    parsed['size'] = "-"
    parsed['mode'] = parsed.get('product_name', '-') # Default Mode to Product Name
    
    variant_txt = parsed.get('variant_info', '')
    if variant_txt and variant_txt != "-":
        # Expecting format like: "Cream / L / Sweatshirt" or "Color / Size / Style"
        # Split by slash
        parts = [p.strip() for p in variant_txt.split('/')]
        
        # Heuristic to find SIZE (S, M, L, XL, 2XL, numbers)
        size_regex = r'^(XS|S|M|L|XL|2XL|3XL|4XL|5XL|\d+([.]\d+)?(inch|cm|mm)?)$'
        
        found_size = False
        found_mode = False
        
        for p in parts:
            # Check for Size
            if re.match(size_regex, p, re.IGNORECASE):
                parsed['size'] = p
                found_size = True
                continue
                
            # Check for Mode/Style (Not color, not size)
            # Assuming Mode is the remaining part that isn't a color? 
            # Or just take the last part if it's 3 parts.
            if len(parts) >= 3 and p == parts[-1]:
                 parsed['mode'] = p
                 found_mode = True
        
        # If regex failed but we have 3 parts: Color / Size / Mode
        if not found_size and len(parts) >= 2:
            # Guess middle is size?
            parsed['size'] = parts[1]
            if len(parts) > 2:
                parsed['mode'] = parts[2]
                
    # 5. Position Mapping
    # User Rules: 
    # Middle -> 4
    # Arm -> 5, 6
    # Black -> B
    # Front -> F
    # Chest -> 3
    # Neck -> 1
    # Cuf -> 8
    # Sleeve -> V, T
    
    # 5. Position Mapping (Comprehensive)
    # Based on User Image & Text
    pos_map = {
        'chest': ['3'],
        'neck': ['1'],
        'middle': ['4'],
        'arm': ['5', '6'],
        'cuff': ['8', '9'],
        'sleeve': ['5', '6'],  # Updated: Sleeve = 5 and 6
        'pocket': ['I', 'O', 'P'],
        'back': ['B'],
        'black': ['B'], # User specific request
        'leg': ['G'],
        'thigh': ['H'],
        'slit': ['S', 'E'],
        'side': ['S', 'E'],
        'collar': ['C'],
        'shoulder': ['D'],
        'front': ['F'],
        'left': ['L'],
        'right': ['R']
    }
    
    detected_pos = set()
    scan_text = (parsed.get('product_name', '') + " " + parsed.get('variant_info', '')).lower()
    
    for key, codes in pos_map.items():
        if key in scan_text:
            for c in codes: detected_pos.add(c)
            
    # Sort: Numbers first (as strings), then Letters
    parsed['positions'] = sorted(list(detected_pos), key=lambda x: (not x.isdigit(), x))
    
    # Special Rule: Products with "Patches" always show checkbox "4" (Middle)
    product_name = parsed.get('product_name', '').lower()
    mode = parsed.get('mode', '').lower()
    combined_product_text = f"{product_name} {mode}"
    
    if 'patches' in combined_product_text or 'patch' in combined_product_text:
        if '4' not in parsed['positions']:
            parsed['positions'].insert(0, '4')  # Add to front
            print("Special Rule: 'Patches' detected - Added position '4'")
            
    # Bỏ chức năng chọn nhiều dữ liệu: chỉ giữ lại 1 vị trí đầu tiên
    if len(parsed['positions']) > 1:
        parsed['positions'] = [parsed['positions'][0]]
    elif not parsed['positions']:
        parsed['positions'] = ['4']
            
    # 6. Look up Dimensions
    parsed['dims'] = get_product_dimensions(
        parsed.get('product_name', ''),
        parsed.get('size', '-'),
        parsed.get('positions', [])
    )
    
    # Debug log for dimension lookup
    if parsed['dims']:
        print(f"✓ Dimensions found: {parsed['dims']} for {parsed.get('product_name', 'N/A')} / {parsed.get('size', 'N/A')}")
    else:
        print(f"⚠ No dimensions found for: {parsed.get('product_name', 'N/A')} / {parsed.get('size', 'N/A')}")
    
    return parsed

def open_folder(path):
    if not path or not os.path.exists(path):
        print(f"Path not found: {path}")
        return False
    if platform.system() == "Windows":
        os.startfile(path)
    return True

def open_image_url(url):
    if url:
        webbrowser.open(url)
        return True
    return False

def take_screenshot(save_path_prefix="Tx_Shot", folder_path=None):
    try:
        filename = f"{save_path_prefix}_{datetime.now().strftime('%H%M%S')}.png"
        
        if folder_path and os.path.exists(folder_path):
            target_dir = folder_path
        else:
            target_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            
        filepath = os.path.join(target_dir, filename)
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return filepath
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

def create_order_folder(base_path, order_id):
    """
    Create folder structure: base_path/yyyy-MM-dd/order_id
    Returns: (folder_path, was_created)
    """
    try:
        # Get current date for folder name
        date_folder = datetime.now().strftime("%Y-%m-%d")
        
        # Clean order_id for folder name (remove invalid chars)
        clean_id = order_id.replace('/', '-').replace('\\', '-').replace(':', '-')
        
        # Build path: Desktop/2026-01-25/113-XXX
        date_path = os.path.join(base_path, date_folder)
        full_path = os.path.join(date_path, clean_id)
        
        # Check if already exists
        existed = os.path.exists(full_path)
        
        # Create if needed
        if not existed:
            os.makedirs(full_path, exist_ok=True)
            print(f"Created folder: {full_path}")
            return (full_path, True)
        else:
            print(f"Folder already exists: {full_path}")
            return (full_path, False)
            
    except Exception as e:
        print(f"Folder creation error: {e}")
        return (None, False)

def copy_to_clipboard(text):
    try:
        pyperclip.copy(text)
        return True
    except:
        return False

def load_dimensions_db():
    global _DIMENSIONS_DB
    if _DIMENSIONS_DB is not None:
        return _DIMENSIONS_DB
        
    db = {}
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kichthuoc.csv")
    
    if not os.path.exists(csv_path):
        print("[Dimensions] kichthuoc.csv not found next to logic.py - dimensions lookup disabled.")
        _DIMENSIONS_DB = {}
        return db

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        current_products = []
        i = 0
        while i < len(rows):
            row = rows[i]
            clean_row = [c.strip() for c in row if c.strip()]
            
            if not clean_row:
                i += 1
                continue

            # Skip comment rows
            first_cell = (row[0] if row else "").strip()
            if first_cell.startswith("#"):
                i += 1
                continue
                
            if "Vị trí" in row or "Cost" in row:
                # Header row
                last_pos = ""
                i += 1
                while i < len(rows):
                    data_row = rows[i]
                    # Check break conditions
                    if not any(c.strip() for c in data_row):
                        i += 1
                        continue
                    if "Vị trí" in data_row and not (len(data_row)>4 and data_row[4].isdigit()):
                         break # New header
                         
                    # Check if data row
                    is_data = False
                    if len(data_row) > 5 and (str(data_row[4]).strip().isdigit() or str(data_row[5]).strip().isdigit()):
                        is_data = True
                    if len(data_row) > 3 and str(data_row[3]).strip() == "All":
                        is_data = True
                    
                    if not is_data:
                         # Possible new product name?
                         if len("".join(data_row)) > 10: break
                    
                    # Parse safely (defensive against short / comment rows)
                    # Index expectation: 1=Pos, 3=Size, 4=H, 5=W, 6=Unit
                    pos = data_row[1].strip() if len(data_row) > 1 else ""
                    if pos:
                        last_pos = pos
                    else:
                        pos = last_pos
                    
                    size = data_row[3].strip() if len(data_row) > 3 else ""
                    h = data_row[4].strip() if len(data_row) > 4 else ""
                    w = data_row[5].strip() if len(data_row) > 5 else ""
                    unit = data_row[6].strip() if len(data_row) > 6 else "mm"
                    
                    dims = f"{h}x{w}{unit}"
                    
                    for p_name in current_products:
                        p_key = p_name.lower().strip()
                        if p_key not in db: db[p_key] = []
                        db[p_key].append({'size': size, 'pos': pos, 'dims': dims})
                    
                    i += 1
                continue
            
            # Extract product names
            text = " ".join(row).strip()
            if len(text) > 5 and not any(k in text.lower() for k in ['vị trí', 'cost', 'size', 'unit']):
                # Find the column with text
                p_str = ""
                for col in row:
                    if len(col) > 5: 
                        p_str = col; break
                
                if p_str and not p_str.strip().startswith('#'):
                    parts = p_str.split('+')
                    current_products = [p.strip().replace('\n', ' ') for p in parts if p.strip()]
                    # product group set

            
            i += 1
            
        _DIMENSIONS_DB = db
        try:
            print(f"[Dimensions] Loaded dimensions for {len(db)} products")
        except Exception:
            pass

        # Ensure some common entries for Cap (the CSV block sometimes gets skipped by the brittle parser)
        if 'cap' not in db and 'hat' not in db:
            cap_entries = [
                {'size': 'All', 'pos': '1', 'dims': '60x55mm'},
                {'size': 'All', 'pos': '4', 'dims': '45x40mm'},
            ]
            db['cap'] = cap_entries
            db['hat'] = cap_entries
            _DIMENSIONS_DB = db
            print('[Dimensions] Added fallback cap/hat entries')

        return db
    except Exception as e:
        try:
            print(f"[Dimensions] Error loading CSV: {e}")
        except Exception:
            pass
        _DIMENSIONS_DB = {}
        return {}

def reload_dimensions_db():
    """
    Force reload of the dimensions database.
    Returns the number of products loaded.
    """
    global _DIMENSIONS_DB
    _DIMENSIONS_DB = None
    print("Reloading dimensions DB...")
    db = load_dimensions_db()
    return len(db)

def get_product_dimensions(product_name, size, positions_codes=None):
    """
    Look up dimensions in the CSV DB.
    positions_codes: list of codes like ['4', 'B'] mapped from logic.pos_map
    """
    db = load_dimensions_db()
    if not db or not product_name or not size: return ""
    
    p_key = product_name.lower().strip()
    
    # 1. Find Product Key
    entries = db.get(p_key)
    if not entries:
        # Try substring match
        for k in db.keys():
            if k in p_key or p_key in k:
                entries = db[k]
                break
    
    if not entries: return ""
    
    # 2. Filter by Size
    size_matches = []
    target_size = size.lower()
    
    for e in entries:
        csv_size = e['size'].lower()
        if csv_size == "all":
            size_matches.append(e)
        elif target_size == csv_size:
             size_matches.append(e)
        elif target_size in csv_size: # Handle "XS - S" ranges
             size_matches.append(e)
             
    if not size_matches: return ""
    
    # 3. Filter by Position
    code_to_content = {
        '4': ['middle'],
        '3': ['chest'],
        '1': ['neck'],
        '5': ['arm', 'sleeve'],
        '6': ['arm', 'sleeve'],
        'B': ['back', 'black'],
        'F': ['front'],
    }
    
    priority_pos = []
    if positions_codes:
        for code in positions_codes:
            if code in code_to_content:
                priority_pos.extend(code_to_content[code])
    
    if not priority_pos: priority_pos = ['middle']
    
    for pos_kw in priority_pos:
        for e in size_matches:
            epos = e.get('pos', '').lower()
            if pos_kw in epos or epos in pos_kw or epos == pos_kw:
                return e['dims']
    
    # fallback to first size match
    if size_matches:
        return size_matches[0]['dims']
    return ""

