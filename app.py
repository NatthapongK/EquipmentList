import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re
import time
import io
import secrets
import streamlit.components.v1 as components
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

# --- PWA META ---
st.markdown("""
<link rel="manifest" href="app/static/manifest.json">
<meta name="theme-color" content="#0E7C86">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="InventoryApp">
""", unsafe_allow_html=True)

# รายการอุปกรณ์เริ่มต้นทั้งหมด
DEFAULT_INITIAL_ITEMS = [
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
    
    # ตาราง Token สำหรับจดจำการล็อกอินถาวร (เก็บฝั่งเซิร์ฟเวอร์ + Cookie ฝั่งเบราว์เซอร์)
    c.execute('''
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT,
            expires_at REAL NOT NULL
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

# --- PERSISTENT LOGIN (Cookie + Server-side Token) ---
COOKIE_NAME = "inv_auth_token"
REMEMBER_DAYS = 365  # จำการล็อกอินไว้ 1 ปี (จนกว่าจะกดออกจากระบบ)
ROLE_ADMIN = "ผู้ออกแบบ/ดูแลระบบ"
ROLE_TECH = "ช่างประจำอาคาร"

def get_admin_credentials():
    try:
        return st.secrets["admin"]["username"], st.secrets["admin"]["password"]
    except Exception:
        return "admin", "admin"

def create_auth_token(username, role):
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM auth_tokens WHERE expires_at < ?", (time.time(),))  # ล้าง token หมดอายุ
    c.execute("INSERT INTO auth_tokens (token, username, role, created_at, expires_at) VALUES (?,?,?,?,?)",
              (token, username, role, get_now_str(), time.time() + REMEMBER_DAYS * 86400))
    conn.commit()
    conn.close()
    return token

def validate_auth_token(token):
    """คืนค่า (username, role) ถ้า token ถูกต้องและยังไม่หมดอายุ ไม่งั้นคืน None"""
    if not token:
        return None
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT username, role, expires_at FROM auth_tokens WHERE token = ?", (token,))
    row = c.fetchone()
    result = None
    if row and row[2] > time.time():
        username, role = row[0], row[1]
        if role == ROLE_ADMIN:
            if username == get_admin_credentials()[0]:
                result = (username, role)
        else:
            # ตรวจว่าบัญชีช่างยังมีอยู่ (ถ้าแอดมินลบบัญชีแล้ว จะเข้าอัตโนมัติไม่ได้)
            c.execute("SELECT 1 FROM tech_users WHERE username = ?", (username,))
            if c.fetchone():
                result = (username, role)
    conn.close()
    return result

def delete_auth_token(token):
    if not token:
        return
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def get_cookie_token():
    # อ่าน Cookie จาก request header ฝั่งเซิร์ฟเวอร์ (ต้องใช้ Streamlit >= 1.37)
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None

def set_browser_cookie(token, days=REMEMBER_DAYS):
    # iframe ของ components.html เป็น same-origin จึงเขียน cookie ของหน้าหลักได้
    components.html(f"""
    <script>
    try {{
        const secure = window.parent.location.protocol === 'https:' ? '; Secure' : '';
        window.parent.document.cookie = "{COOKIE_NAME}={token}; max-age={int(days) * 86400}; path=/; SameSite=Lax" + secure;
    }} catch (e) {{ console.error(e); }}
    </script>
    """, height=0)

def clear_browser_cookie():
    set_browser_cookie("", days=0)

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

# --- SESSION & LOGIN STATE MANAGEMENT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.session_state.auth_token = None

# กู้คืนการล็อกอินอัตโนมัติจาก Cookie (เปิดเว็บใหม่/รีเฟรช/ปิดแล้วเปิดใหม่ ไม่ต้องล็อกอินซ้ำ)
if not st.session_state.logged_in:
    _cookie_token = get_cookie_token()
    _saved = validate_auth_token(_cookie_token)
    if _saved:
        st.session_state.logged_in = True
        st.session_state.username, st.session_state.role = _saved
        st.session_state.original_role = ROLE_ADMIN if _saved[1] == ROLE_ADMIN else None
        st.session_state.auth_token = _cookie_token

# --- LOGIN UI ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 1.6, 1])
    with col_login:
        st.markdown(
            '<div class="app-hero"><div><div class="t">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>'
            '<div class="s">เข้าสู่ระบบครั้งเดียวเพื่อจดจำการใช้งานบนอุปกรณ์นี้</div></div></div>',
            unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ (จดจำอุปกรณ์)", type="primary", use_container_width=True)
        
        tech_df = run_query("SELECT * FROM tech_users")
        
        # ล้าง Cookie เก่าหลังกดออกจากระบบ
        if st.session_state.pop("clear_cookie", False):
            clear_browser_cookie()

        if submitted:
            role_val = ""
            user_val = ""
            admin_user, admin_pass = get_admin_credentials()

            if username == admin_user and password == admin_pass:
                role_val = ROLE_ADMIN
                user_val = admin_user
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)]
                if not matched_tech.empty:
                    role_val = ROLE_TECH
                    user_val = username

            if role_val:
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                st.session_state.original_role = ROLE_ADMIN if role_val == ROLE_ADMIN else None

                # สร้าง Token เก็บในฐานข้อมูล แล้วส่งให้เบราว์เซอร์เก็บเป็น Cookie ในรอบถัดไป
                token = create_auth_token(user_val, role_val)
                st.session_state.auth_token = token
                st.session_state.pending_cookie_token = token
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

background_sync_watcher()

# เขียน Cookie ลงเบราว์เซอร์ (ทำครั้งเดียวหลังล็อกอินสำเร็จ)
if st.session_state.get("pending_cookie_token"):
    set_browser_cookie(st.session_state.pop("pending_cookie_token"))

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
    if st.button("🚪 ออกจากระบบ (ล้างค่าอุปกรณ์)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
        # ลบ Token ออกจากฐานข้อมูล (Cookie เก่าจะใช้ไม่ได้อีก) และสั่งล้าง Cookie ในหน้า Login
        delete_auth_token(st.session_state.get("auth_token") or get_cookie_token())
        st.session_state.clear_cookie = True
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = ""
        st.session_state.original_role = None
        st.session_state.auth_token = None
        st.rerun()

st.markdown(
    f'<div class="app-hero"><div><div class="t">🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์</div>'
    f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {get_now_str("%d/%m/%Y")}</div></div>'
    f'<span class="chip">{esc(st.session_state.role)}</span></div>',
    unsafe_allow_html=True)

# --- LIVE KPI & ALERT SYSTEM ---
@st.fragment(run_every="3s")
def render_kpi_and_alerts():
    setting_df = run_query("SELECT value FROM settings WHERE key='low_stock_threshold'")
    low_stock_limit = int(setting_df.iloc[0]['value']) if not setting_df.empty else 1

    items_df = run_query("SELECT * FROM items")

    abnormal_items = items_df[
        items_df['status'].isin(['ชำรุด', 'สูญหาย', 'ยืม', 'อุปกรณ์หมด']) | 
        items_df['status'].str.startswith('กำลังใช้งาน', na=False)
    ]

    low_stock_list = []
    for _, row in items_df.iterrows():
        if row['subcategory'] == 'เครื่องมือช่าง':
            continue
        threshold = 0 if row.get('alert_zero', 0) == 1 else low_stock_limit
        if row['quantity'] <= threshold:
            low_stock_list.append(row)
    low_stock_items = pd.DataFrame(low_stock_list)

    borrowed_cnt = int(run_query("SELECT COUNT(*) AS c FROM transactions WHERE status = 'กำลังยืม'").iloc[0]['c'])
    abn_cnt, low_cnt = len(abnormal_items), len(low_stock_items)

    st.markdown(
        f'''<div class="kpi-grid">
          <div class="kpi"><div class="n">{len(items_df)}</div><div class="l">รายการอุปกรณ์ทั้งหมด</div></div>
          <div class="kpi" style="--c:{'var(--bad)' if abn_cnt else 'var(--ok)'}"><div class="n">{abn_cnt}</div><div class="l">ผิดปกติ / กำลังใช้งาน / หมด / ยืม</div></div>
          <div class="kpi" style="--c:{'var(--warn)' if low_cnt else 'var(--ok)'}"><div class="n">{low_cnt}</div><div class="l">เหลือน้อยกว่าเกณฑ์</div></div>
          <div class="kpi" style="--c:var(--teal)"><div class="n">{borrowed_cnt}</div><div class="l">กำลังถูกยืมอยู่</div></div>
        </div>''', unsafe_allow_html=True)

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        if abn_cnt:
            with st.expander(f"❌ อุปกรณ์ผิดปกติ/กำลังใช้งาน/หมด/ถูกยืม ({abn_cnt} รายการ)"):
                st.dataframe(abnormal_items[['name', 'category', 'status', 'quantity']], hide_index=True, use_container_width=True,
                             column_config={"name": "ชื่ออุปกรณ์", "category": "หมวดหมู่", "status": "สถานะ",
                                            "quantity": st.column_config.NumberColumn("คงเหลือ", format="%d")})
        else:
            st.success("✅ อุปกรณ์ทุกชิ้นอยู่ในสภาพปกติ")
    with col_a2:
        if low_cnt:
            with st.expander(f"⚠️ อุปกรณ์ทั่วไปเหลือน้อย ({low_cnt} รายการ)"):
                st.dataframe(low_stock_items[['name', 'category', 'quantity']], hide_index=True, use_container_width=True,
                             column_config={"name": "ชื่ออุปกรณ์", "category": "หมวดหมู่",
                                            "quantity": st.column_config.NumberColumn("คงเหลือ", format="%d")})
        else:
            st.success("✅ อุปกรณ์ทั่วไปทุกชิ้นมีจำนวนเพียงพอ")
    st.markdown("")

render_kpi_and_alerts()

# --- SHARED BORROW / RETURN COMPONENT ---
@st.fragment
def render_borrow_return_system():
    items_df = run_query("SELECT * FROM items")
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])
    
    with sub_borrow:
        available_items = items_df[items_df['quantity'] > 0]
        if not available_items.empty:
            with st.form("borrow_form_shared", clear_on_submit=True):
                item_dict = {f"#{row['id']} {row['name']} (คงเหลือ: {row['quantity']} ชิ้น) [{row['category']}]": row['id'] for _, row in available_items.iterrows()}
                sel_item_label = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(item_dict.keys()))
                
                selected_id = item_dict[sel_item_label]
                item_info = items_df[items_df['id'] == selected_id].iloc[0]
                max_q = int(item_info['quantity'])
                
                borrow_qty = st.number_input("จำนวนที่ต้องการยืม *", min_value=1, max_value=max_q, value=1)
                borrower_name = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                borrow_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายผู้ยืมหรือหลักฐานการยืม (ถ้ามี)", type=["jpg", "jpeg", "png"])
                
                st.info(f"📌 ผู้ทำรายการ/ผู้ให้ยืม: **{st.session_state.username}** (บันทึกอัตโนมัติ)")
                
                if st.form_submit_button("ยืนยันการยืมอุปกรณ์"):
                    if borrower_name.strip():
                        b_img_b64 = None
                        if borrow_img_file is not None:
                            b_img_bytes = borrow_img_file.read()
                            b_img_b64 = base64.b64encode(b_img_bytes).decode("utf-8")
                        now_time = get_now_str("%Y-%m-%d %H:%M")
                        
                        run_query("INSERT INTO transactions (item_id, borrower_name, borrow_date, status, borrower_image, quantity, giver_name) VALUES (?,?,?,?,?,?,?)",
                                  (selected_id, borrower_name, now_time, "กำลังยืม", b_img_b64, borrow_qty, st.session_state.username), is_select=False)
                        
                        new_qty = max_q - borrow_qty
                        new_status = 'ยืม' if new_qty == 0 else item_info['status']
                        
                        run_query("UPDATE items SET quantity = ?, status = ? WHERE id = ?", (new_qty, new_status, selected_id), is_select=False)
                        
                        trigger_smooth_update(f"บันทึกการยืม {item_info['name']} สำเร็จ")
                    else:
                        st.error("❌ กรุณากรอกชื่อผู้ยืมให้เรียบร้อย")
        else:
            st.info("ไม่มีอุปกรณ์ที่มีจำนวนคงเหลือให้ยืมในขณะนี้")
            
    with sub_return:
        st.markdown("#### รายการที่กำลังถูกยืมอยู่")
        active_tx = run_query("""
            SELECT t.id as tx_id, t.item_id, i.name as item_name, t.borrower_name, t.borrow_date, t.borrower_image, t.quantity, i.quantity as current_q, t.giver_name
            FROM transactions t JOIN items i ON t.item_id = i.id 
            WHERE t.status = 'กำลังยืม' ORDER BY t.id DESC
        """)
        
        if not active_tx.empty:
            for _, row in active_tx.iterrows():
                giver_str = f" | ผู้ให้ยืม: {row['giver_name']}" if pd.notnull(row['giver_name']) and row['giver_name'] else ""
                with st.expander(f"📦 อุปกรณ์: {row['item_name']} (จำนวนยืม: {row['quantity']} ชิ้น) | ผู้ยืม: {row['borrower_name']}{giver_str}"):
                    col_r1, col_r2 = st.columns([1, 2])
                    with col_r1:
                        p_img = get_pil_image_from_base64(row['borrower_image'])
                        if p_img:
                            st.image(p_img, caption=f"ผู้ยืม: {row['borrower_name']}", width=200)
                        else:
                            st.write("*(ไม่มีรูปถ่าย)*")
                    with col_r2:
                        st.write(f"**ชื่ออุปกรณ์:** {row['item_name']}")
                        st.write(f"**จำนวนที่ยืม:** {row['quantity']} ชิ้น")
                        st.write(f"**ผู้ยืม:** {row['borrower_name']}")
                        if row.get('giver_name'):
                            st.write(f"**ผู้ให้ยืม/บันทึก:** {row['giver_name']}")
                        st.write(f"**วันที่ยืม:** {row['borrow_date']}")
                        
                        with st.form(key=f"return_form_{row['tx_id']}"):
                            st.info(f"📌 ผู้รับคืน: **{st.session_state.username}** (บันทึกอัตโนมัติ)")
                            ret_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายตอนคืนอุปกรณ์ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"ret_img_{row['tx_id']}")
                            
                            if st.form_submit_button("✅ รับคืนอุปกรณ์รายการนี้"):
                                now_time = get_now_str("%Y-%m-%d %H:%M")
                                r_img_b64 = None
                                if ret_img_file is not None:
                                    r_img_bytes = ret_img_file.read()
                                    r_img_b64 = base64.b64encode(r_img_bytes).decode("utf-8")
                                    
                                run_query("UPDATE transactions SET return_date = ?, status = 'คืนแล้ว', receiver_name = ?, return_image = ? WHERE id = ?", 
                                          (now_time, st.session_state.username, r_img_b64, row['tx_id']), is_select=False)
                                
                                tx_qty = int(row['quantity']) if pd.notnull(row['quantity']) else 1
                                new_q = int(row['current_q']) + tx_qty
                                run_query("UPDATE items SET quantity = ?, status = 'ปกติ' WHERE id = ?", (new_q, row['item_id']), is_select=False)
                                
                                trigger_smooth_update(f"รับคืน {row['item_name']} เรียบร้อยแล้ว")
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืมในขณะนี้")
            
    with sub_history:
        st.markdown("#### ประวัติการยืม-คืนทั้งหมด")
        tx_history = run_query("""
            SELECT t.id as 'รหัส', i.name as 'ชื่ออุปกรณ์', t.quantity as 'จำนวน', t.borrower_name as 'ผู้ยืม', 
                   t.giver_name as 'ผู้ให้ยืม', t.receiver_name as 'ผู้รับคืน', t.borrow_date as 'วันที่ยืม', t.return_date as 'วันที่คืน', t.status as 'สถานะ'
            FROM transactions t JOIN items i ON t.item_id = i.id ORDER BY t.id DESC
        """)
        st.dataframe(tx_history, use_container_width=True, hide_index=True)

# --- ROLE-BASED INTERFACE ROUTING ---
items_df = run_query("SELECT * FROM items")

if st.session_state.role == "ผู้ออกแบบ/ดูแลระบบ":
    admin_menu = st.tabs([
        "📋 1. จัดการอุปกรณ์ทั้งหมด", 
        "📊 2. รายงานการตรวจเช็ค", 
        "📥 3. อนุมัติคำขอเพิ่มอุปกรณ์", 
        "🔄 4. ยืม-คืน เครื่องมือ-อุปกรณ์", 
        "⚙️ 5. ตั้งค่าระบบ & รหัสช่าง"
    ])
    
    with admin_menu[0]:
        st.subheader("📋 จัดการอุปกรณ์ทั้งหมดในระบบ")
        tab_list, tab_add_edit, tab_excel_import = st.tabs(["🔍 ดูรายการทั้งหมด", "➕ เพิ่ม/แก้ไขอุปกรณ์", "📥 นำเข้า/รีเซ็ตข้อมูล"])
        with tab_list:
            c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
            search_kw = c_f1.text_input("🔍 ค้นหาชื่ออุปกรณ์...", placeholder="พิมพ์ชื่ออุปกรณ์เพื่อค้นหา")
            cat_filter = c_f2.selectbox("กรองตามหมวดหลัก", ["ทั้งหมด", "อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
            status_filter = c_f3.selectbox("กรองตามสถานะ", ["ทั้งหมด", "ปกติ", "ชำรุด", "สูญหาย", "ยืม", "อุปกรณ์หมด"])
            
            filtered_df = items_df.copy()
            if search_kw.strip():
                filtered_df = filtered_df[filtered_df['name'].str.contains(search_kw.strip(), case=False, na=False)]
            if cat_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['category'] == cat_filter]
            if status_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
            show_df = filtered_df[['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note']].copy()
            show_df['alert_zero'] = show_df['alert_zero'].astype(bool)
            
            table_event = st.dataframe(
                show_df, use_container_width=True, hide_index=True, height=350,
                on_select="rerun", selection_mode="single-row",
                column_config={
                    "id": st.column_config.NumberColumn("รหัส", width="small"),
                    "name": st.column_config.TextColumn("ชื่ออุปกรณ์", width="large"),
                    "category": "หมวดหมู่หลัก", "subcategory": "หมวดย่อย",
                    "quantity": st.column_config.NumberColumn("จำนวน", format="%d", width="small"),
                    "status": "สถานะ",
                    "alert_zero": st.column_config.CheckboxColumn("เตือนที่ 0", width="small"),
                    "note": "หมายเหตุ",
                }
            )
            
            selected_rows = table_event.get("selection", {}).get("rows", [])
            if selected_rows:
                st.session_state.quick_edit_id = int(filtered_df.iloc[selected_rows[0]]['id'])

            if "quick_edit_id" in st.session_state and st.session_state.quick_edit_id:
                qe_id = st.session_state.quick_edit_id
                qe_item_check = items_df[items_df['id'] == qe_id]
                if not qe_item_check.empty:
                    qe_row = qe_item_check.iloc[0]
                    st.markdown("---")
                    with st.expander(f"📌 หน้าต่างป๊อปอัพแก้ไขข้อมูล: #{qe_row['id']} - {qe_row['name']}", expanded=True):
                        with st.form(f"quick_edit_form_{qe_id}"):
                            qe_name = st.text_input("ชื่ออุปกรณ์", value=qe_row['name'])
                            qe_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if qe_row['category']=="อุปกรณ์ช่าง" else 1)
                            qe_subcat = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"], index=0 if qe_row['subcategory']=="เครื่องมือช่าง" else 1) if qe_category=="อุปกรณ์ช่าง" else "เคมีภัณฑ์"
                            qe_quantity = st.number_input("จำนวน", min_value=0, value=int(qe_row['quantity']))
                            status_list = ["ปกติ", "ชำรุด", "สูญหาย", "ยืม", "อุปกรณ์หมด"]
                            qe_status = st.selectbox("สถานะ", status_list, index=status_list.index(qe_row['status']) if qe_row['status'] in status_list else 0)
                            qe_alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0", value=bool(qe_row.get('alert_zero', 0)))
                            qe_note = st.text_area("หมายเหตุ", value=qe_row['note'] if qe_row['note'] else "")
                            
                            qe_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"qe_file_{qe_id}")
                            
                            col_qe1, col_qe2, col_qe3 = st.columns([1, 1, 2])
                            if col_qe1.form_submit_button("💾 บันทึก", type="primary"):
                                img_base64 = qe_row['image']
                                if qe_file is not None:
                                    img_base64 = base64.b64encode(qe_file.read()).decode("utf-8")
                                run_query("UPDATE items SET name=?, category=?, subcategory=?, quantity=?, status=?, alert_zero=?, note=?, image=? WHERE id=?",
                                          (qe_name, qe_category, qe_subcat, qe_quantity, qe_status, (1 if qe_alert_zero else 0), qe_note, img_base64, qe_id), is_select=False)
                                del st.session_state.quick_edit_id
                                trigger_smooth_update("อัปเดตข้อมูลสำเร็จ!")
                            if col_qe2.form_submit_button("🗑️ ลบอุปกรณ์", type="secondary"):
                                run_query("DELETE FROM items WHERE id=?", (qe_id,), is_select=False)
                                del st.session_state.quick_edit_id
                                trigger_smooth_update("ลบอุปกรณ์เรียบร้อยแล้ว!")
                            if col_qe3.form_submit_button("❌ ปิด"):
                                del st.session_state.quick_edit_id
                                trigger_smooth_update()

        with tab_add_edit:
            with st.form("add_item_form_new", clear_on_submit=True):
                name = st.text_input("ชื่ออุปกรณ์ *")
                category = st.selectbox("หมวดหมู่หลัก *", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
                subcategory = st.selectbox("หมวดหมู่ย่อย *", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"]) if category=="อุปกรณ์ช่าง" else "เคมีภัณฑ์"
                quantity = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1)
                status = st.selectbox("สภาพเริ่มต้น", ["ปกติ", "ชำรุด", "สูญหาย", "อุปกรณ์หมด"])
                alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0")
                note = st.text_area("หมายเหตุ")
                uploaded_file = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์", type=["jpg", "jpeg", "png"])
                
                if st.form_submit_button("บันทึกอุปกรณ์ใหม่"):
                    if name.strip():
                        img_base64 = base64.b64encode(uploaded_file.read()).decode("utf-8") if uploaded_file else None
                        run_query("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?,?,?,?,?,?,?,?)",
                                  (name, category, subcategory, quantity, status, (1 if alert_zero else 0), note, img_base64), is_select=False)
                        trigger_smooth_update(f"เพิ่มอุปกรณ์ '{name}' สำเร็จ!")
                    else:
                        st.error("กรุณากรอกชื่ออุปกรณ์")

        with tab_excel_import:
            st.markdown("### ⚡ โหลดชุดข้อมูลตั้งต้นทั้งหมด")
            if st.button("🚀 รีเซ็ตและโหลดอุปกรณ์ทั้งหมดตามรายการใหม่", type="primary"):
                run_query("DELETE FROM items", is_select=False)
                run_query("DELETE FROM sqlite_sequence WHERE name='items'", is_select=False)
                conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
                c = conn.cursor()
                c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                              [(i[0], i[1], i[2], i[3], i[4], 0, i[5], i[6]) for i in DEFAULT_INITIAL_ITEMS])
                conn.commit()
                conn.close()
                trigger_smooth_update("รีเซ็ตและโหลดอุปกรณ์ใหม่สำเร็จ!")

    with admin_menu[1]:
        st.subheader("📊 รายการตรวจเช็คสภาพอุปกรณ์")
        inspections_df = run_query("SELECT * FROM inspections ORDER BY id DESC")
        if not inspections_df.empty:
            st.dataframe(inspections_df[['id', 'tech_name', 'category', 'inspection_date', 'session_num', 'details']], use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการตรวจเช็ค")

    with admin_menu[2]:
        st.subheader("📥 จัดการคำขอเพิ่มอุปกรณ์เข้าคลัง")
        pending_requests = run_query("""
            SELECT r.id, r.tech_name, i.name as item_name, r.quantity, r.note, r.request_date, r.item_id, i.quantity as current_stock
            FROM requisition_requests r JOIN items i ON r.item_id = i.id WHERE r.status = 'รออนุมัติ' ORDER BY r.id DESC
        """)
        if not pending_requests.empty:
            for _, req in pending_requests.iterrows():
                st.write(f"🆔 **คำขอ #{req['id']}** | ผู้ขอ: {req['tech_name']} | อุปกรณ์: {req['item_name']} (+{req['quantity']})")
                col_app1, col_app2 = st.columns(2)
                if col_app1.button(f"✅ อนุมัติ #{req['id']}", key=f"approve_{req['id']}"):
                    run_query("UPDATE items SET quantity = quantity + ?, status = 'ปกติ' WHERE id = ?", (req['quantity'], req['item_id']), is_select=False)
                    run_query("UPDATE requisition_requests SET status = 'อนุมัติ', approval_date = ? WHERE id = ?", (get_now_str(), req['id']), is_select=False)
                    trigger_smooth_update(f"อนุมัติคำขอ #{req['id']} สำเร็จ")
                if col_app2.button(f"❌ ปฏิเสธ #{req['id']}", key=f"reject_{req['id']}"):
                    run_query("UPDATE requisition_requests SET status = 'ไม่อนุมัติ', approval_date = ? WHERE id = ?", (get_now_str(), req['id']), is_select=False)
                    trigger_smooth_update(f"ปฏิเสธคำขอ #{req['id']}")
                st.markdown("---")
        else:
            st.info("ไม่มีคำขอที่รออนุมัติ")

    with admin_menu[3]:
        render_borrow_return_system()

    with admin_menu[4]:
        st.subheader("⚙️ ตั้งค่าระบบและบัญชีช่าง")
        with st.form("low_stock_setting_form"):
            new_threshold = st.number_input("เกณฑ์แจ้งเตือนอุปกรณ์เหลือน้อย (ชิ้น)", min_value=0, value=1)
            if st.form_submit_button("บันทึกค่าเกณฑ์"):
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('low_stock_threshold', ?)", (str(new_threshold),), is_select=False)
                trigger_smooth_update("บันทึกเกณฑ์สำเร็จ")

elif st.session_state.role in ["ช่างประจำอาคาร", "ช่างประจำอาคารพิเศษ"]:
    if st.session_state.role == "ช่างประจำอาคารพิเศษ":
        col_banner, col_btn_back = st.columns([3, 1])
        with col_banner:
            st.info("⭐ คุณเข้าใช้งานในสถานะ **ช่างประจำอาคารพิเศษ**")
        with col_btn_back:
            if st.button("🔙 สลับกลับเป็นแอดมิน", type="primary", use_container_width=True):
                st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                st.rerun()
    
    st.subheader("📋 หน้าต่างปฏิบัติงานช่างประจำอาคาร")
    tech_main_tab = st.tabs(["📋 ตรวจสอบอุปกรณ์", "📦 เบิกของ", "🔄 ยืม-คืน อุปกรณ์"])
    
    with tech_main_tab[0]:
        tech_category_choice = st.radio("เลือกหมวดหมู่", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
        if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
            tools_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['quantity'] > 0)]
            with keyed_container("tech_check_list", height=400):
                item_reports = {}
                for _, row in tools_df.iterrows():
                    col_i, col_f = st.columns([4, 1])
                    col_i.write(f"🛠️ {row['name']} (เหลือ: {row['quantity']})")
                    is_flag = col_f.checkbox("แจ้งปัญหา", key=f"flag_{row['id']}")
                    item_reports[row['id']] = {"flagged": is_flag, "status": "ชำรุด" if is_flag else "ปกติ"}
            
            uploaded_photos = [base64.b64encode(f.read()).decode("utf-8") for i in range(4) if (f := st.file_uploader(f"รูปถ่ายหน้างานที่ {i+1} *", type=["jpg", "png"], key=f"p_{i}"))]
            if st.button("💾 ส่งผลตรวจเช็ค", type="primary"):
                if len(uploaded_photos) < 4:
                    st.error("❌ กรุณาแนบรูปถ่ายให้ครบทั้ง 4 รูป")
                else:
                    run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details, photos) VALUES (?,?,?,?,?,?)",
                              (st.session_state.username, 'อุปกรณ์ช่าง', get_now_str(), 1, "ตรวจเช็คประจำวัน", "|||".join(uploaded_photos)), is_select=False)
                    trigger_smooth_update("บันทึกผลการตรวจสำเร็จ!")
        else:
            pool_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ']
            updated_q = {row['id']: st.number_input(row['name'], min_value=0, value=int(row['quantity']), key=f"pool_{row['id']}") for _, row in pool_df.iterrows()}
            uploaded_pool = [base64.b64encode(f.read()).decode("utf-8") for i in range(4) if (f := st.file_uploader(f"รูปถ่ายสระที่ {i+1} *", type=["jpg", "png"], key=f"sp_{i}"))]
            if st.button("💾 บันทึกสระว่ายน้ำ", type="primary"):
                if len(uploaded_pool) < 4:
                    st.error("❌ กรุณาแนบรูปถ่ายสระให้ครบ 4 รูป")
                else:
                    for i_id, q in updated_q.items():
                        run_query("UPDATE items SET quantity = ? WHERE id = ?", (q, i_id), is_select=False)
                    run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details, photos) VALUES (?,?,?,?,?,?)",
                              (st.session_state.username, 'อุปกรณ์สระว่ายน้ำ', get_now_str(), 1, "อัปเดตสระ", "|||".join(uploaded_pool)), is_select=False)
                    trigger_smooth_update("บันทึกสระว่ายน้ำสำเร็จ!")

    with tech_main_tab[1]:
        st.markdown("### 📦 ส่งคำขอเบิกของ")
        req_df = items_df[(items_df['category'] == 'อุปกรณ์สระว่ายน้ำ') | (items_df['subcategory'] == 'อุปกรณ์ช่างทั่วไป')]
        with st.form("req_form", clear_on_submit=True):
            item_map = {f"{r['name']} ({r['category']})": r['id'] for _, r in req_df.iterrows()}
            sel_item = st.selectbox("เลือกอุปกรณ์", list(item_map.keys()))
            q_val = st.number_input("จำนวนที่ขอ", min_value=1, value=1)
            note_val = st.text_area("เหตุผลการขอเบิก *")
            if st.form_submit_button("ส่งคำขอ"):
                if note_val.strip():
                    run_query("INSERT INTO requisition_requests (tech_name, item_id, quantity, note, status, request_date) VALUES (?,?,?,?,?,?)",
                              (st.session_state.username, item_map[sel_item], q_val, note_val, 'รออนุมัติ', get_now_str()), is_select=False)
                    trigger_smooth_update("ส่งคำขอเบิกสำเร็จ!")
                else:
                    st.error("กรุณากรอกเหตุผล")

    with tech_main_tab[2]:
        render_borrow_return_system()
