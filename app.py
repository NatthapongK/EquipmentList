import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re
import time
import io
from PIL import Image

# --- TIMEZONE CONFIG (Thailand UTC+7) ---
TZ_TH = timezone(timedelta(hours=7))

def get_now_th():
    return datetime.now(TZ_TH)

def get_now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return get_now_th().strftime(fmt)

# --- CONFIGURATION ---
st.set_page_config(
    page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ",
    page_icon="🛠️",
    layout="wide"
)

# --- PWA & PERSISTENT LOGIN FRONTEND BRIDGE ---
st.markdown("""
<link rel="manifest" href="app/static/manifest.json">
<meta name="theme-color" content="#0E7C86">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="InventoryApp">
<script>
// ตรวจสอบและกู้คืนสถานะการเข้าสู่ระบบจาก LocalStorage ของเครื่องมือถือ/แท็บเล็ต
window.addEventListener('DOMContentLoaded', () => {
    const savedUser = localStorage.getItem('pwa_username');
    const savedRole = localStorage.getItem('pwa_role');
    const currentParams = new URLSearchParams(window.location.search);
    
    if (savedUser && savedRole && !currentParams.has('logged_in')) {
        currentParams.set('logged_in', 'true');
        currentParams.set('username', savedUser);
        currentParams.set('role', savedRole);
        currentParams.set('login_time', Date.now());
        window.location.search = currentParams.toString();
    }
});
</script>
""", unsafe_allow_html=True)

# รายการอุปกรณ์เริ่มต้นทั้งหมด
DEFAULT_INITIAL_ITEMS = [
    # เครื่องมือช่าง
    ("ปลั๊กโรลElecton", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("สว่านแบตMakita", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("บันได3ขั้น", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องตรวจเช็กเต้ารับไฟฟ้า (Socket Tester)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("โบลเวอร์เป่าลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจขันน๊อตใต้อ่างอเนกประสงค์ Cotora", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ปืนทะลวงท่ออัดแรงดัน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("แคมป์มิเตอร์", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ไขควงแฉก", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 4, "ปกติ", "-", None),
    ("ไขควงแบน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("ตลับเมตร", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("ปืนยิงซิลิโคน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ปืนยิงPU", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("แปลงทาสี", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("ค้อน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดประแจก๊อกแก๊กพร้อมลูกบล็อก 10-24", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจชุดเบอร์ 8-24", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมตัด", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมปากแหลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมรวม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("อุปกรณ์เปิดฝาท่อFCO Cotora", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("อุปกรณ์ยกฝาท่อ", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("เกียงโป้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("ตะใบขัดไม้", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("คีมล็อคSOLO", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ถีมล็อคโซ่", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมคอม้าเล็กขนาด30ซม.", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมคอม้าใหญ่ขนาด2นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจเลื่อน 10นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจเลื่อน 12นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดประแจหกเหลี่ยมSolosหุน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดประแจหกเหลี่ยมหัวบอลMasterToolหุน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("พวงประแจหกเหลี่ยมมิลดำ", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("พวงประแจหกเหลี่ยมมิลเงิน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เกจวัดลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เลื่อยตัดเหล็ก (Hacksaw)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("เลื่อยไม้20นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องเป่าลมร้อน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("เครื่องเจียร4นิ้ว(ลูกหมู)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("สว่านกระแทก", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดเครื่องมือช่างพื้นฐาน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องวัดอุณภูมิหม้อแปลง", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ฟิตเทป", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    
    # อุปกรณ์ช่างทั่วไป
    ("กาวร้อน", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("เทปพันสายไฟ", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("เทปพันเกลียว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 6, "ปกติ", "-", None),
    ("เต๋าต่อสายไฟ", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("สเปรย์หล่อลื่นโซแน็กซ์", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("หัวคิว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("สเปรย์Contact Cleaner WD40", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("กระดาษทรายไม้เบอร์5", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
    ("กระดาษทรายไม้เบอร์1", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
    ("แปรงทองเหลือง", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("สเปย์ลู่วิ่งSilicone Oil", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย6x1นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 100, "ปกติ", "-", None),
    ("สกรูปลายสว่านTF", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 100, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย8x1-1/4นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย12x1นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("จารบี", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("หัวสว่านแปรงทองเหลือง", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("ใบตัดเหล็ก", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 7, "ปกติ", "-", None),
    ("ใบเจียรเหล็ก", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
    ("ใบขัดกระดาษทราย", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("ใบตัดอลู", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("ใบตัดปูน", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("ใบเจียรปูน", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    
    # หมวดสระว่ายน้ำ
    ("คลอรีนผง 90%", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("สารส้ม", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 4, "ปกติ", "-", None),
    ("โซดาแอช", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
    ("กรดเกลือผง", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 4, "ปกติ", "-", None),
    ("กรดเกลือน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
    ("เกลือบริสุทธิ์", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 50, "ปกติ", "-", None),
    ("ตาข่ายตักขยะสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("แปรงขัดสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ด้ามจับยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ด้ามจับสั้น", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ชุดทดสอบคลอรีนและ pH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ขวดน้ำยาคลอรีน", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("ขวดน้ำยาpH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None)
]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '-',
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            image TEXT
        )
    ''')
    
    c.execute("PRAGMA table_info(items)")
    item_cols = [col[1] for col in c.fetchall()]
    if 'alert_zero' not in item_cols:
        c.execute("ALTER TABLE items ADD COLUMN alert_zero INTEGER DEFAULT 0")
        conn.commit()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            borrower_name TEXT,
            borrow_date TEXT,
            return_date TEXT,
            status TEXT,
            borrower_image TEXT,
            quantity INTEGER DEFAULT 1,
            giver_name TEXT,
            receiver_name TEXT,
            return_image TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    c.execute("PRAGMA table_info(transactions)")
    tx_cols = [col[1] for col in c.fetchall()]
    if 'giver_name' not in tx_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN giver_name TEXT")
        conn.commit()
    if 'receiver_name' not in tx_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN receiver_name TEXT")
        conn.commit()
    if 'return_image' not in tx_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN return_image TEXT")
        conn.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS requisition_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_name TEXT,
            item_id INTEGER,
            quantity INTEGER,
            note TEXT,
            status TEXT,
            request_date TEXT,
            approval_date TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    c.execute("PRAGMA table_info(requisition_requests)")
    req_cols = [col[1] for col in c.fetchall()]
    if 'approval_date' not in req_cols:
        c.execute("ALTER TABLE requisition_requests ADD COLUMN approval_date TEXT")
        conn.commit()

    c.execute('''
        CREATE TABLE IF NOT EXISTS tech_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_name TEXT,
            category TEXT,
            inspection_date TEXT,
            session_num INTEGER,
            details TEXT,
            photos TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('low_stock_threshold', '1')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('global_daily_quota', '3')")
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sync_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute("INSERT OR IGNORE INTO sync_meta (key, value) VALUES ('last_update', ?)", (str(time.time()),))
    
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      [(i[0], i[1], i[2], i[3], i[4], 0, i[5], i[6]) for i in DEFAULT_INITIAL_ITEMS])
        
    conn.commit()
    conn.close()

init_db()

def get_db_version():
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT value FROM sync_meta WHERE key='last_update'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else "0"

def run_query(query, params=(), is_select=True):
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    
    if not is_select:
        new_timestamp = str(time.time())
        c.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_update', ?)", (new_timestamp,))
        conn.commit()
        st.session_state.local_db_ver = new_timestamp
        
    if is_select:
        res = c.fetchall()
        cols = [d[0] for d in c.description]
        conn.close()
        df = pd.DataFrame(res, columns=cols)
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        if 'alert_zero' in df.columns:
            df['alert_zero'] = pd.to_numeric(df['alert_zero'], errors='coerce').fillna(0).astype(int)
        return df
    
    conn.close()

def trigger_smooth_update(msg=None):
    if msg:
        st.toast(msg, icon="✅")
    try:
        st.rerun(scope="fragment")
    except Exception:
        st.rerun()

@st.fragment(run_every="3s")
def background_sync_watcher():
    latest_ver = get_db_version()
    if "local_db_ver" not in st.session_state:
        st.session_state.local_db_ver = latest_ver
    elif st.session_state.local_db_ver != latest_ver:
        st.session_state.local_db_ver = latest_ver
        st.rerun(scope="app")

def parse_tech_txt_content(text_content):
    tech_list = []
    lines = text_content.splitlines()
    u = None
    p = None
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        if "username" in line_s:
            m = re.search(r'["\']([^"\']+)["\']', line_s)
            if m:
                u = m.group(1)
        elif "password" in line_s:
            m = re.search(r'["\']([^"\']+)["\']', line_s)
            if m:
                p = m.group(1)
        if u and p:
            tech_list.append((u, p))
            u, p = None, None
    return tech_list

def esc(text):
    return _html.escape(str(text))

def keyed_container(key, **kwargs):
    try:
        return st.container(key=key, **kwargs)
    except TypeError:
        return st.container(**kwargs)

@st.cache_data(show_spinner=False, max_entries=256)
def get_pil_image_from_base64(img_base64):
    if not img_base64:
        return None
    try:
        img_bytes = base64.b64decode(img_base64)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None

# --- STYLING ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap');
:root{
  --ink:#F1F5F9; --muted:#94A3B8; --line:#334155; --bg:#0B132B; --card:#1E293B;
  --teal:#0E7C86; --teal-d:#0A5C64; --ok:#22C55E; --warn:#F59E0B; --bad:#EF4444;
}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp input, .stApp textarea, .stApp button, .stApp [data-baseweb="tab"], .stApp [data-baseweb="select"]{
  font-family:'IBM Plex Sans Thai','Noto Sans Thai',system-ui,sans-serif;
}
.stApp{background:var(--bg); color:var(--ink);}
header[data-testid="stHeader"] {display: none !important;}
footer {visibility: hidden !important; display: none !important;}
#MainMenu {visibility: hidden !important; display: none !important;}
.block-container{padding-top:1.5rem; padding-bottom:3rem; max-width:1200px;}
.app-hero{background:#111827; color:#fff; border-radius:14px; padding:1rem 1.25rem; border:1px solid var(--line);
  display:flex; justify-content:space-between; align-items:center; gap:.75rem 1rem; flex-wrap:wrap; margin-bottom:1rem;}
.app-hero .t{font-size:1.3rem; font-weight:700; line-height:1.3; color:#F8FAFC;}
.app-hero .s{font-size:.85rem; color:#94A3B8; margin-top:.15rem;}
.chip{display:inline-block; padding:.2rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600; background:var(--teal); color:#fff;}
.kpi-grid{display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; margin-bottom:1rem;}
.kpi{background:var(--card); border:1px solid var(--line); border-left:4px solid var(--c,var(--teal)); border-radius:10px; padding:.7rem .9rem;}
.kpi .n{font-size:1.7rem; font-weight:700; line-height:1.15; color:#F8FAFC;}
.kpi .l{font-size:.82rem; color:var(--muted);}
section[data-testid="stSidebar"]{background:#111827; border-right:1px solid var(--line);}
.user-card{display:flex; align-items:center; gap:.7rem; padding:.7rem; border:1px solid var(--line); border-radius:12px; background:var(--card);}
.avatar{width:2.4rem; height:2.4rem; border-radius:50%; background:var(--teal); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; flex:none;}
.u-name{font-weight:600; line-height:1.2; word-break:break-all; color:#F8FAFC;}
.u-role{font-size:.8rem; color:var(--muted);}
</style>
""", unsafe_allow_html=True)

# --- PERMANENT LOGIN PERSISTENCE STATE & LOCALSTORAGE SYNC ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None

qp = st.query_params
if not st.session_state.logged_in and "logged_in" in qp and qp["logged_in"] == "true":
    st.session_state.logged_in = True
    st.session_state.role = qp.get("role", "")
    st.session_state.username = qp.get("username", "")
    st.session_state.original_role = qp.get("original_role", None)

if st.session_state.logged_in and "original_role" in qp and qp["original_role"]:
    st.session_state.original_role = qp["original_role"]

# --- LOGIN UI ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 1.6, 1])
    with col_login:
        st.markdown(
            '<div class="app-hero"><div><div class="t">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>'
            '<div class="s">เข้าสู่ระบบครั้งเดียวเพื่อจดจำอุปกรณ์และใช้งานต่อเนื่อง</div></div></div>',
            unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ (จดจำอุปกรณ์นี้)", type="primary", use_container_width=True)
        
        tech_df = run_query("SELECT * FROM tech_users")
        
        if submitted:
            role_val = ""
            user_val = ""
            
            try:
                admin_user = st.secrets["admin"]["username"]
                admin_pass = st.secrets["admin"]["password"]
            except Exception:
                admin_user = "admin"
                admin_pass = "admin"
            
            if username == admin_user and password == admin_pass:
                role_val = "ผู้ออกแบบ/ดูแลระบบ"
                user_val = admin_user
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)]
                if not matched_tech.empty:
                    role_val = "ช่างประจำอาคาร"
                    user_val = username
            
            if role_val:
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                orig_role = role_val if role_val == "ผู้ออกแบบ/ดูแลระบบ" else ""
                st.session_state.original_role = orig_role if orig_role else None
                
                # ฝัง Script บันทึกค่าลงใน LocalStorage ของมือถือเพื่อให้ Login ถาวร
                st.markdown(f"""
                <script>
                localStorage.setItem('pwa_username', '{user_val}');
                localStorage.setItem('pwa_role', '{role_val}');
                window.location.href = window.location.pathname + '?logged_in=true&username={user_val}&role={role_val}';
                </script>
                """, unsafe_allow_html=True)
                st.success("เข้าสู่ระบบสำเร็จ! กำลังเข้าสู่หน้าหลัก...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

background_sync_watcher()

# --- MAIN APP LOGGED IN (Sidebar with user profile & logout) ---
st.sidebar.markdown(
    f'<div class="user-card"><div class="avatar">{esc(st.session_state.username[:1].upper())}</div>'
    f'<div><div class="u-name">{esc(st.session_state.username)}</div>'
    f'<div class="u-role">สิทธิ์: {esc(st.session_state.role)}</div></div></div>',
    unsafe_allow_html=True)
st.sidebar.markdown("")

with st.sidebar.expander("👤 เมนูบัญชีผู้ใช้ & ออกจากระบบ", expanded=True):
    st.write(f"ผู้ใช้งาน: **{st.session_state.username}**")
    st.write(f"สิทธิ์: **{st.session_state.role}**")
    
    is_admin_origin = (
        (st.session_state.get("original_role") == "ผู้ออกแบบ/ดูแลระบบ")
        or (st.query_params.get("original_role") == "ผู้ออกแบบ/ดูแลระบบ")
        or (st.session_state.role == "ผู้ออกแบบ/ดูแลระบบ")
    )
    
    if is_admin_origin:
        st.markdown("---")
        if st.session_state.role == "ผู้ออกแบบ/ดูแลระบบ":
            if st.button("🔀 สลับเป็น 'ช่างประจำอาคารพิเศษ'", type="secondary", use_container_width=True):
                st.session_state.role = "ช่างประจำอาคารพิเศษ"
                st.session_state.original_role = "ผู้ออกแบบ/ดูแลระบบ"
                st.rerun()
        else:
            if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True):
                st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                st.session_state.original_role = "ผู้ออกแบบ/ดูแลระบบ"
                st.rerun()
    
    st.markdown("---")
    if st.button("🚪 ออกจากระบบ (ล้างความจำเครื่อง)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
        # สคริปต์ล้างข้อมูลจำในเครื่องมือถือ
        st.markdown("""
        <script>
        localStorage.removeItem('pwa_username');
        localStorage.removeItem('pwa_role');
        window.location.href = window.location.pathname;
        </script>
        """, unsafe_allow_html=True)
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = ""
        st.session_state.original_role = None
        st.query_params.clear()
        st.rerun()

st.markdown(
    f'<div class="app-hero"><div><div class="t">🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์</div>'
    f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {get_now_str("%d/%m/%Y")}</div></div>'
    f'<span class="chip">{esc(st.session_state.role)}</span></div>',
    unsafe_allow_html=True)

# --- (ฟังก์ชันการทำงานหลักและ UI หน้าอื่นๆ คงเดิมตามสถาปัตยกรรม Fragment ป้องกันการรีเฟรช) ---
