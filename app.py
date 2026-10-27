import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
import html as _html

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ", page_icon="🛠️", layout="wide")

# รายการอุปกรณ์เริ่มต้นทั้งหมด
DEFAULT_INITIAL_ITEMS = [
    # เครื่องมือช่าง
    ("ปลั๊กโรลElecton", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("แปลงทาสี", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("ค้อน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เลื่อยตัดเหล็ก (Hacksaw)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("ประแจชุดเบอร์ 8-24", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจขันน๊อตใต้อ่างอเนกประสงค์ Cotora", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ตะใบขัดเหล็ก", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("คีมตัด", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมปากแหลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมรวม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("อุปกรณ์เปิดฝาท่อFCO Cotora", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("อุปกรณ์ยกฝาท่อ", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("ชุดประแจก๊อกแก๊กพร้อมลูกบล็อก 10-24", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เกียงโป้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("คีมล็อคSOLO", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ถีมล็อคโซ่", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมคอม้าเล็กขนาด30ซม.", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("คีมคอม้าใหญ่ขนาด2นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจเลื่อน 10นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ประแจเลื่อน 12นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("แคมป์มิเตอร์", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดประแจหกเหลี่ยมSoloนิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดประแจหกเหลี่ยมหัวบอลMasterToolมิล", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("พวงประแจหกเหลี่ยมนิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("พวงประแจหกเหลี่ยมมิล", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ตลับเมตร", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("เกจวัดลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เลื่อยไม้20นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ปืนยิงซิลิโคน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ปืนยิงPU", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("สว่านแบตMakita", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("โบลเวอร์เป่าลม", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องเป่าลมร้อน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("เครื่องเจียร4นิ้ว(ลูกหมู)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("สว่านกระแทก", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ชุดเครื่องมือช่างพื้นฐาน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("บันได3ขั้น", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องตรวจเช็กเต้ารับไฟฟ้า (Socket Tester)", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("ไขควงแฉก", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 4, "ปกติ", "-", None),
    ("ไขควงแบน", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 3, "ปกติ", "-", None),
    ("ฟิตเทป", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องวัดอุณภูมิหม้อแปลง", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    
    # อุปกรณ์ช่างทั่วไป
    ("สเปรย์หล่อลื่นโซแน็กซ์", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("สเปรย์หล่อลื่นWD40", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("สเปย์ลู่วิ่งSilicone Oil", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("กาวร้อน", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("หัวคิว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 2, "ปกติ", "-", None),
    ("กระดาษทรายไม้เบอร์5", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
    ("กระดาษทรายไม้เบอร์1", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
    ("จารบี", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
    ("เทปพันเกลียว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 6, "ปกติ", "-", None),
    ("เต๋าต่อสายไฟ", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย6x1นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 100, "ปกติ", "-", None),
    ("สกรูปลายสว่านTF", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 100, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย8x1-1/4นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("สกรูเกลียวปล่อย12x1นิ้ว", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 20, "ปกติ", "-", None),
    ("แปรงทองเหลือง", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 1, "ปกติ", "-", None),
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
    ("โซดาแอช", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("กรดเกลือน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("เกลือบริสุทธิ์", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 50, "ปกติ", "-", None),
    ("ตาข่ายตักขยะสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("แปรงขัดสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ด้ามจับยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ด้ามจับสั้น", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ชุดทดสอบคลอรีนและ pH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ขวดน้ำยาคลอรีน", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 5, "ปกติ", "-", None),
    ("ขวดน้ำยาpH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 5, "ปกติ", "-", None)
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
    
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      [(i[0], i[1], i[2], i[3], i[4], 0, i[5], i[6]) for i in DEFAULT_INITIAL_ITEMS])
        
    c.execute("SELECT COUNT(*) FROM tech_users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO tech_users (username, password) VALUES (?, ?)", ("tech", "tech123"))
        
    conn.commit()
    conn.close()

init_db()

# --- THEME / UI HELPERS (Light Theme + Hide All Streamlit Badges & Status Widgets) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap');
:root{
  --ink:#14232B; --muted:#5B6B73; --line:#DCE4E7; --bg:#F8FAFB; --card:#FFFFFF;
  --teal:#0E7C86; --teal-d:#0A5C64; --ok:#2E7D5B; --warn:#B7791F; --bad:#B93A32;
}
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp input, .stApp textarea, .stApp button, .stApp [data-baseweb="tab"], .stApp [data-baseweb="select"]{
  font-family:'IBM Plex Sans Thai','Noto Sans Thai',system-ui,sans-serif;
}
.stApp{background:var(--bg); color:var(--ink);}

header[data-testid="stHeader"] {display: none !important;}
footer {visibility: hidden !important; display: none !important;}
#MainMenu {visibility: hidden !important; display: none !important;}
.stDeployButton {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important; visibility: hidden !important; opacity: 0 !important;}
div[class*="viewerBadge"] {display: none !important; visibility: hidden !important; opacity: 0 !important;}
a[href*="streamlit.io"] {display: none !important; visibility: hidden !important; opacity: 0 !important;}
.styles_viewerBadge__1yG5_ {display: none !important;}

.block-container{padding-top:1.5rem; padding-bottom:3rem; max-width:1200px;}
h2, h3, h4{color:var(--ink); font-weight:600; letter-spacing:0;}

.app-hero{background:var(--ink); color:#fff; border-radius:14px; padding:1rem 1.25rem;
  display:flex; justify-content:space-between; align-items:center; gap:.75rem 1rem; flex-wrap:wrap; margin-bottom:1rem;}
.app-hero .t{font-size:1.3rem; font-weight:700; line-height:1.3;}
.app-hero .s{font-size:.85rem; color:#A9BCC4; margin-top:.15rem;}
.chip{display:inline-block; padding:.2rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600;
  background:rgba(14,124,134,.9); color:#fff;}

.kpi-grid{display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; margin-bottom:1rem;}
.kpi{background:var(--card); border:1px solid var(--line); border-left:4px solid var(--c,var(--teal));
  border-radius:10px; padding:.7rem .9rem;}
.kpi .n{font-size:1.7rem; font-weight:700; line-height:1.15; color:var(--ink);}
.kpi .l{font-size:.82rem; color:var(--muted);}

section[data-testid="stSidebar"]{background:#fff; border-right:1px solid var(--line);}
.user-card{display:flex; align-items:center; gap:.7rem; padding:.7rem; border:1px solid var(--line);
  border-radius:12px; background:var(--bg);}
.avatar{width:2.4rem; height:2.4rem; border-radius:50%; background:var(--teal); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; flex:none;}
.u-name{font-weight:600; line-height:1.2; word-break:break-all;}
.u-role{font-size:.8rem; color:var(--muted);}

.stTabs [data-baseweb="tab-list"]{gap:.2rem; border-bottom:1px solid var(--line); overflow-x:auto;}
.stTabs [data-baseweb="tab"]{height:auto; padding:.6rem .9rem; font-weight:500; color:var(--muted); white-space:nowrap;}
.stTabs [aria-selected="true"]{color:var(--teal-d); font-weight:600;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--teal); height:3px;}

[data-testid="stExpander"]{border:1px solid var(--line); border-radius:10px; background:var(--card);}
[data-testid="stForm"]{border:1px solid var(--line); border-radius:12px; background:var(--card); padding:1rem;}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:10px; overflow:hidden;}
[data-testid="stAlert"]{border-radius:10px;}

.stApp button{border-radius:8px; font-weight:600;}
.stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--teal); border-color:var(--teal); color:#fff;}
.stApp button[kind="primary"]:hover, .stApp button[data-testid="stBaseButton-primary"]:hover,
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:var(--teal-d); border-color:var(--teal-d);}

.st-key-tech_check_list div[data-testid="stHorizontalBlock"]{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  gap: 0.5rem !important;
}
.st-key-tech_check_list div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
.st-key-tech_check_list div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
.st-key-tech_check_list div[data-testid="stHorizontalBlock"] > div:last-child {
  flex: 0 0 110px !important;
}
.st-key-tech_check_list div[data-testid="stCheckbox"] {
  margin-top: 0 !important;
  white-space: nowrap !important;
}

@media (max-width:640px){
  .block-container{padding-left:.8rem; padding-right:.8rem;}
  .kpi-grid{grid-template-columns:repeat(2,1fr);}
  .app-hero .t{font-size:1.1rem;}
  .stApp .stButton > button, .stApp [data-testid="stFormSubmitButton"] > button{width:100%;}
}
</style>
""", unsafe_allow_html=True)

def esc(text):
    return _html.escape(str(text))

def keyed_container(key, **kwargs):
    try:
        return st.container(key=key, **kwargs)
    except TypeError:
        return st.container(**kwargs)

# --- HELPER FUNCTIONS ---
def run_query(query, params=(), is_select=True):
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
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
    conn.commit()
    conn.close()

def get_pil_image_from_base64(img_base64):
    if not img_base64:
        return None
    try:
        import io
        from PIL import Image
        img_bytes = base64.b64decode(img_base64)
        return Image.open(io.BytesIO(img_bytes))
    except:
        return None

# --- SESSION STATE & LOGIN PERSISTENCE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

qp = st.query_params
if not st.session_state.logged_in and "logged_in" in qp and qp["logged_in"] == "true":
    try:
        login_time = float(qp.get("login_time", 0))
        if datetime.now().timestamp() - login_time < 24 * 3600:
            st.session_state.logged_in = True
            st.session_state.role = qp.get("role", "")
            st.session_state.username = qp.get("username", "")
        else:
            st.query_params.clear()
    except:
        st.query_params.clear()

# --- LOGIN UI ---
if not st.session_state.logged_in:
    _, col_login, _ = st.columns([1, 1.6, 1])
    with col_login:
        st.markdown(
            '<div class="app-hero"><div><div class="t">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>'
            '<div class="s">เข้าสู่ระบบเพื่อตรวจเช็ค ยืม-คืน และจัดการคลังอุปกรณ์</div></div></div>',
            unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
        
        tech_df = run_query("SELECT * FROM tech_users")
        
        if submitted:
            role_val = ""
            user_val = ""
            if username == "Natthapongk" and password == "0891148075":
                role_val = "แอดมิน"
                user_val = "Natthapongk"
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)]
                if not matched_tech.empty:
                    role_val = "ช่างทั่วไป"
                    user_val = username
            
            if role_val:
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                st.query_params["logged_in"] = "true"
                st.query_params["role"] = role_val
                st.query_params["username"] = user_val
                st.query_params["login_time"] = str(datetime.now().timestamp())
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# --- MAIN APP LOGGED IN (Sidebar with expandable user profile & logout) ---
st.sidebar.markdown(
    f'<div class="user-card"><div class="avatar">{esc(st.session_state.username[:1].upper())}</div>'
    f'<div><div class="u-name">{esc(st.session_state.username)}</div>'
    f'<div class="u-role">สิทธิ์: {esc(st.session_state.role)}</div></div></div>',
    unsafe_allow_html=True)
st.sidebar.markdown("")

with st.sidebar.expander("👤 เมนูบัญชีผู้ใช้ & ออกจากระบบ", expanded=True):
    st.write(f"ผู้ใช้งาน: **{st.session_state.username}**")
    st.write(f"สิทธิ์: **{st.session_state.role}**")
    if st.button("🚪 ออกจากระบบ (Logout)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = ""
        st.query_params.clear()
        st.rerun()

st.markdown(
    f'<div class="app-hero"><div><div class="t">🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์</div>'
    f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {datetime.now().strftime("%d/%m/%Y")}</div></div>'
    f'<span class="chip">{esc(st.session_state.role)}</span></div>',
    unsafe_allow_html=True)

# --- QUICK ACCOUNT & LOGOUT EXPANDER ON MAIN PAGE (Ensure user never loses access if sidebar is closed) ---
with st.expander(f"👤 ข้อมูลผู้ใช้งานปัจจุบัน: {st.session_state.username} (สิทธิ์: {st.session_state.role}) — คลิกเพื่อจัดการบัญชี / ออกจากระบบ"):
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        st.write(f"กำลังใช้งานในชื่อ: **{st.session_state.username}** | สิทธิ์ระบบ: **{st.session_state.role}**")
    with col_u2:
        if st.button("🚪 ออกจากระบบ", type="primary", use_container_width=True, key="main_page_logout_btn"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            st.query_params.clear()
            st.rerun()

# --- ALERT SYSTEM ---
setting_df = run_query("SELECT value FROM settings WHERE key='low_stock_threshold'")
low_stock_limit = int(setting_df.iloc[0]['value']) if not setting_df.empty else 1

items_df = run_query("SELECT * FROM items")

abnormal_items = items_df[items_df['status'].isin(['ชำรุด', 'สูญหาย', 'ยืม', 'อุปกรณ์หมด'])]

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
      <div class="kpi" style="--c:{'var(--bad)' if abn_cnt else 'var(--ok)'}"><div class="n">{abn_cnt}</div><div class="l">ผิดปกติ / หมด / ถูกยืม</div></div>
      <div class="kpi" style="--c:{'var(--warn)' if low_cnt else 'var(--ok)'}"><div class="n">{low_cnt}</div><div class="l">เหลือน้อยกว่าเกณฑ์</div></div>
      <div class="kpi" style="--c:var(--teal)"><div class="n">{borrowed_cnt}</div><div class="l">กำลังถูกยืมอยู่</div></div>
    </div>''', unsafe_allow_html=True)

col_a1, col_a2 = st.columns(2)
with col_a1:
    if abn_cnt:
        with st.expander(f"❌ อุปกรณ์ผิดปกติ/หมด/ถูกยืม ({abn_cnt} รายการ)"):
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

# --- SHARED BORROW / RETURN COMPONENT ---
def render_borrow_return_system():
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
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        run_query("INSERT INTO transactions (item_id, borrower_name, borrow_date, status, borrower_image, quantity, giver_name) VALUES (?,?,?,?,?,?,?)",
                                  (selected_id, borrower_name, now_time, "กำลังยืม", b_img_b64, borrow_qty, st.session_state.username), is_select=False)
                        
                        new_qty = max_q - borrow_qty
                        new_status = 'ยืม' if new_qty == 0 else item_info['status']
                        
                        run_query("UPDATE items SET quantity = ?, status = ? WHERE id = ?", (new_qty, new_status, selected_id), is_select=False)
                        
                        st.success(f"บันทึกการยืม {item_info['name']} จำนวน {borrow_qty} ชิ้น เรียบร้อยแล้ว")
                        st.rerun()
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
                            
                            if st.form_submit_button(f"✅ รับคืนอุปกรณ์รายการนี้"):
                                now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                                r_img_b64 = None
                                if ret_img_file is not None:
                                    r_img_bytes = ret_img_file.read()
                                    r_img_b64 = base64.b64encode(r_img_bytes).decode("utf-8")
                                    
                                run_query("UPDATE transactions SET return_date = ?, status = 'คืนแล้ว', receiver_name = ?, return_image = ? WHERE id = ?", 
                                          (now_time, st.session_state.username, r_img_b64, row['tx_id']), is_select=False)
                                
                                tx_qty = int(row['quantity']) if pd.notnull(row['quantity']) else 1
                                new_q = int(row['current_q']) + tx_qty
                                run_query("UPDATE items SET quantity = ?, status = 'ปกติ' WHERE id = ?", (new_q, row['item_id']), is_select=False)
                                
                                st.success(f"รับคืน {row['item_name']} จำนวน {tx_qty} ชิ้น เรียบร้อยแล้ว")
                                st.rerun()
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

# --- DIVISION BY ROLE ---
if st.session_state.role == "แอดมิน":
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
                
            st.caption(f"แสดงรายการอุปกรณ์ทั้งหมด {len(filtered_df)} จาก {len(items_df)} รายการ")
            
            # ใช้ selectbox เลือกรายการเพื่อแก้ไขอย่างเสถียร 100% ทุกเวอร์ชัน Streamlit ไม่เกิด Error
            if not filtered_df.empty:
                item_options = {f"#{row['id']} - {row['name']} (หมวด: {row['category']} | คงเหลือ: {row['quantity']})": int(row['id']) for _, row in filtered_df.iterrows()}
                selected_item_label = st.selectbox("📌 เลือกรายการอุปกรณ์ที่ต้องการแก้ไขด่วน", ["-- กรุณาเลือกรายการอุปกรณ์เพื่อแก้ไข --"] + list(item_options.keys()))
                if selected_item_label != "-- กรุณาเลือกรายการอุปกรณ์เพื่อแก้ไข --":
                    st.session_state.quick_edit_id = item_options[selected_item_label]
            
            show_df = filtered_df[['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note']].copy()
            show_df['alert_zero'] = show_df['alert_zero'].astype(bool)
            
            st.dataframe(
                show_df, use_container_width=True, hide_index=True, height=300,
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
            
            if "quick_edit_id" in st.session_state and st.session_state.quick_edit_id:
                qe_id = st.session_state.quick_edit_id
                qe_item_check = items_df[items_df['id'] == qe_id]
                if not qe_item_check.empty:
                    qe_row = qe_item_check.iloc[0]
                    st.markdown("---")
                    st.markdown(f"### ✏️ แก้ไขข้อมูลอุปกรณ์: #{qe_row['id']} - {qe_row['name']}")
                    
                    with st.form(f"quick_edit_form_{qe_id}"):
                        qe_name = st.text_input("ชื่ออุปกรณ์", value=qe_row['name'])
                        qe_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if qe_row['category']=="อุปกรณ์ช่าง" else 1)
                        
                        if qe_category == "อุปกรณ์ช่าง":
                            sub_idx = 0 if qe_row['subcategory'] == "เครื่องมือช่าง" else 1
                            qe_subcat = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"], index=sub_idx)
                        else:
                            qe_subcat = "เคมีภัณฑ์"
                            st.info("📌 หมวดหมู่ย่อยถูกกำหนดเป็น: **เคมีภัณฑ์** โดยอัตโนมัติ")
                            
                        qe_quantity = st.number_input("จำนวน", min_value=0, value=int(qe_row['quantity']))
                        status_list = ["ปกติ", "ชำรุด", "สูญหาย", "ยืม", "อุปกรณ์หมด"]
                        qe_status = st.selectbox("สถานะ", status_list, index=status_list.index(qe_row['status']) if qe_row['status'] in status_list else 0)
                        
                        qe_alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0", value=bool(qe_row.get('alert_zero', 0)))
                        qe_note = st.text_area("หมายเหตุ", value=qe_row['note'] if qe_row['note'] else "")
                        
                        pil_img = get_pil_image_from_base64(qe_row['image'])
                        if pil_img:
                            st.image(pil_img, width=150, caption="รูปภาพปัจจุบัน")
                        qe_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"qe_file_{qe_id}")
                        
                        col_qe1, col_qe2, col_qe3 = st.columns([1, 1, 2])
                        if col_qe1.form_submit_button("💾 บันทึกการแก้ไข", type="primary"):
                            img_base64 = qe_row['image']
                            if qe_file is not None:
                                img_bytes = qe_file.read()
                                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            az_val = 1 if qe_alert_zero else 0
                            run_query("UPDATE items SET name=?, category=?, subcategory=?, quantity=?, status=?, alert_zero=?, note=?, image=? WHERE id=?",
                                      (qe_name, qe_category, qe_subcat, qe_quantity, qe_status, az_val, qe_note, img_base64, qe_id), is_select=False)
                            st.success("อัปเดตข้อมูลสำเร็จ!")
                            del st.session_state.quick_edit_id
                            st.rerun()
                        if col_qe2.form_submit_button("🗑️ ลบอุปกรณ์นี้", type="secondary"):
                            run_query("DELETE FROM items WHERE id=?", (qe_id,), is_select=False)
                            st.success("ลบเรียบร้อยแล้ว!")
                            del st.session_state.quick_edit_id
                            st.rerun()
                        if col_qe3.form_submit_button("❌ ปิดหน้าต่างแก้ไข"):
                            del st.session_state.quick_edit_id
                            st.rerun()

        with tab_add_edit:
            sub_a, sub_e = st.tabs(["➕ เพิ่มอุปกรณ์ใหม่", "✏️ แก้ไข/ลบ รายการ"])
            with sub_a:
                with st.form("add_item_form_new", clear_on_submit=True):
                    name = st.text_input("ชื่ออุปกรณ์ *")
                    category = st.selectbox("หมวดหมู่หลัก *", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
                    if category == "อุปกรณ์ช่าง":
                        subcategory = st.selectbox("หมวดหมู่ย่อย *", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"])
                    else:
                        subcategory = "เคมีภัณฑ์"
                        st.info("📌 หมวดหมู่ย่อยถูกกำหนดเป็น: **เคมีภัณฑ์** โดยอัตโนมัติ")
                        
                    quantity = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1)
                    status = st.selectbox("สภาพเริ่มต้น", ["ปกติ", "ชำรุด", "สูญหาย", "อุปกรณ์หมด"])
                    
                    alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0 (ค่าเริ่มต้นเตือนที่ 1)")
                    
                    note = st.text_area("หมายเหตุ")
                    uploaded_file = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์", type=["jpg", "jpeg", "png"])
                    
                    if st.form_submit_button("บันทึกอุปกรณ์ใหม่"):
                        if name.strip():
                            img_base64 = None
                            if uploaded_file is not None:
                                img_bytes = uploaded_file.read()
                                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            az_val = 1 if alert_zero else 0
                            run_query("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?,?,?,?,?,?,?,?)",
                                      (name, category, subcategory, quantity, status, az_val, note, img_base64), is_select=False)
                            st.success("เพิ่มอุปกรณ์สำเร็จ!")
                            st.rerun()
                        else:
                            st.error("กรุณากรอกชื่ออุปกรณ์")
                            
            with sub_e:
                if not items_df.empty:
                    selected_item_id = st.selectbox("เลือกอุปกรณ์ที่ต้องการแก้ไข", items_df['id'].astype(str) + " - " + items_df['name'])
                    if selected_item_id:
                        item_id_int = int(selected_item_id.split(" - ")[0])
                        current_item = items_df[items_df['id'] == item_id_int].iloc[0]
                        
                        with st.form(f"edit_form_{item_id_int}"):
                            e_name = st.text_input("ชื่ออุปกรณ์", value=current_item['name'])
                            e_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if current_item['category']=="อุปกรณ์ช่าง" else 1)
                            
                            if e_category == "อุปกรณ์ช่าง":
                                sub_idx = 0 if current_item['subcategory'] == "เครื่องมือช่าง" else 1
                                e_subcat = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"], index=sub_idx)
                            else:
                                e_subcat = "เคมีภัณฑ์"
                                st.info("📌 หมวดหมู่ย่อยถูกกำหนดเป็น: **เคมีภัณฑ์** โดยอัตโนมัติ")
                                
                            e_quantity = st.number_input("จำนวน", min_value=0, value=int(current_item['quantity']))
                            status_list = ["ปกติ", "ชำรุด", "สูญหาย", "ยืม", "อุปกรณ์หมด"]
                            e_status = st.selectbox("สถานะ", status_list, index=status_list.index(current_item['status']) if current_item['status'] in status_list else 0)
                            
                            e_alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0", value=bool(current_item.get('alert_zero', 0)))
                            
                            e_note = st.text_area("หมายเหตุ", value=current_item['note'] if current_item['note'] else "")
                            
                            pil_img = get_pil_image_from_base64(current_item['image'])
                            if pil_img:
                                st.image(pil_img, width=150, caption="รูปภาพปัจจุบัน")
                            e_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"file_{item_id_int}")
                            
                            col_e1, col_e2 = st.columns(2)
                            if col_e1.form_submit_button("บันทึกการแก้ไข", type="primary"):
                                img_base64 = current_item['image']
                                if e_file is not None:
                                    img_bytes = e_file.read()
                                    img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                                az_val = 1 if e_alert_zero else 0
                                run_query("UPDATE items SET name=?, category=?, subcategory=?, quantity=?, status=?, alert_zero=?, note=?, image=? WHERE id=?",
                                          (e_name, e_category, e_subcat, e_quantity, e_status, az_val, e_note, img_base64, item_id_int), is_select=False)
                                st.success("อัปเดตข้อมูลสำเร็จ!")
                                st.rerun()
                            if col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary"):
                                run_query("DELETE FROM items WHERE id=?", (item_id_int,), is_select=False)
                                st.success("ลบเรียบร้อยแล้ว!")
                                st.rerun()

        with tab_excel_import:
            st.markdown("### ⚡ โหลดชุดข้อมูลตั้งต้นทั้งหมด")
            if st.button("🚀 รีเซ็ตและโหลดอุปกรณ์ทั้งหมด 54 รายการ", type="primary"):
                run_query("DELETE FROM items", is_select=False)
                run_query("DELETE FROM sqlite_sequence WHERE name='items'", is_select=False)
                conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
                c = conn.cursor()
                c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                              [(i[0], i[1], i[2], i[3], i[4], 0, i[5], i[6]) for i in DEFAULT_INITIAL_ITEMS])
                conn.commit()
                conn.close()
                st.success("นำเข้าอุปกรณ์ทั้งหมดสำเร็จ!")
                st.rerun()

    with admin_menu[1]:
        st.subheader("📊 รายการตรวจเช็คสภาพอุปกรณ์")
        report_type = st.radio("เลือกมุมมองรายงาน", ["รายวัน (Daily)", "รายเดือน (Monthly)", "รายปี (Yearly)", "ประวัติทั้งหมด"], horizontal=True)
        inspections_df = run_query("SELECT * FROM inspections ORDER BY id DESC")
        
        if not inspections_df.empty:
            inspections_df['inspection_date'] = pd.to_datetime(inspections_df['inspection_date'])
            now_dt = datetime.now()
            if report_type == "รายวัน (Daily)":
                target_date = st.date_input("เลือกวันที่", value=now_dt.date())
                filtered_df = inspections_df[inspections_df['inspection_date'].dt.date == target_date]
            elif report_type == "รายเดือน (Monthly)":
                col_m1, col_m2 = st.columns(2)
                selected_month = col_m1.selectbox("เดือน", list(range(1, 13)), index=now_dt.month-1)
                selected_year = col_m2.number_input("ปี (ค.ศ.)", value=now_dt.year)
                filtered_df = inspections_df[(inspections_df['inspection_date'].dt.month == selected_month) & (inspections_df['inspection_date'].dt.year == selected_year)]
            elif report_type == "รายปี (Yearly)":
                selected_year = st.number_input("ปี ค.ศ.", value=now_dt.year)
                filtered_df = inspections_df[inspections_df['inspection_date'].dt.year == selected_year]
            else:
                filtered_df = inspections_df
            
            st.dataframe(
                filtered_df[['id', 'tech_name', 'category', 'inspection_date', 'session_num', 'details']],
                use_container_width=True, hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("รหัส", width="small"),
                    "tech_name": "ผู้ตรวจ", "category": "หมวดหมู่",
                    "inspection_date": st.column_config.DatetimeColumn("วันที่ตรวจ", format="DD/MM/YYYY HH:mm"),
                    "session_num": st.column_config.NumberColumn("รอบ", width="small"),
                    "details": st.column_config.TextColumn("รายละเอียด", width="large"),
                })
            
            st.markdown("---")
            st.markdown("#### 📸 ดูรายละเอียดและรูปถ่ายหน้างานของการตรวจเช็ค")
            for _, row in filtered_df.iterrows():
                date_str_show = row['inspection_date'].strftime("%Y-%m-%d %H:%M:%S")
                with st.expander(f"📌 {date_str_show} | ผู้ตรวจ: {row['tech_name']} | หมวด: {row['category']} (รอบที่ {row['session_num']})"):
                    st.write(f"📝 **รายละเอียดการตรวจ:** {row['details']}")
                    photos_raw = row['photos']
                    if pd.notnull(photos_raw) and str(photos_raw).strip():
                        photo_list = str(photos_raw).split("|||")
                        st.write(f"จำนวนรูปถ่ายทั้งหมด: **{len(photo_list)} รูป**")
                        cols_p = st.columns(min(len(photo_list), 4))
                        for idx, p_b64 in enumerate(photo_list):
                            col_idx = idx % 4
                            p_img = get_pil_image_from_base64(p_b64)
                            if p_img:
                                cols_p[col_idx].image(p_img, caption=f"รูปที่ {idx+1}", use_container_width=True)
                    else:
                        st.info("*(การตรวจเช็ครอบนี้ไม่ได้อัปโหลดรูปถ่ายรวม)*")
        else:
            st.info("ยังไม่มีประวัติการตรวจเช็คจากช่างในระบบ")

    # --- เมนูแอดมิน: อนุมัติคำขอเพิ่มอุปกรณ์ & ประวัติการอนุมัติ (แยกจากระบบยืม-คืน) ---
    with admin_menu[2]:
        st.subheader("📥 จัดการคำขอเพิ่มอุปกรณ์เข้าคลัง")
        sub_req_pending, sub_req_history = st.tabs(["📥 คำขอที่รออนุมัติ", "📜 ประวัติการอนุมัติคำขอ"])
        
        with sub_req_pending:
            pending_requests = run_query("""
                SELECT r.id, r.tech_name, i.name as item_name, r.quantity, r.note, r.request_date, r.item_id, i.quantity as current_stock
                FROM requisition_requests r JOIN items i ON r.item_id = i.id
                WHERE r.status = 'รออนุมัติ' ORDER BY r.id DESC
            """)
            
            if not pending_requests.empty:
                for _, req in pending_requests.iterrows():
                    with st.container():
                        st.write(f"🆔 **รหัสคำขอ:** #{req['id']} | 👤 **ผู้ขอเพิ่ม:** {req['tech_name']} | 📅 **วันที่ขอ:** {req['request_date']}")
                        st.write(f"📦 **อุปกรณ์:** {req['item_name']} | **จำนวนที่ขอเพิ่ม:** +{req['quantity']} ชิ้น (คงเหลือในคลังปัจจุบัน: {req['current_stock']})")
                        st.write(f"📝 **หมายเหตุ/เหตุผล:** {req['note']}")
                        
                        col_app1, col_app2 = st.columns(2)
                        if col_app1.button(f"✅ อนุมัติ (เพิ่มจำนวนเข้าคลัง)", key=f"approve_{req['id']}"):
                            new_stock = int(req['current_stock']) + int(req['quantity'])
                            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            run_query("UPDATE items SET quantity = ?, status = 'ปกติ' WHERE id = ?", (new_stock, req['item_id']), is_select=False)
                            run_query("UPDATE requisition_requests SET status = 'อนุมัติ', approval_date = ? WHERE id = ?", (now_time, req['id']), is_select=False)
                            st.success(f"อนุมัติคำขอ #{req['id']} เรียบร้อยแล้ว (เพิ่มจำนวนในคลังเป็น {new_stock} ชิ้น)")
                            st.rerun()
                            
                        if col_app2.button(f"❌ ไม่อนุมัติ", key=f"reject_{req['id']}"):
                            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            run_query("UPDATE requisition_requests SET status = 'ไม่อนุมัติ', approval_date = ? WHERE id = ?", (now_time, req['id']), is_select=False)
                            st.warning(f"ปฏิเสธคำขอ #{req['id']} เรียบร้อยแล้ว")
                            st.rerun()
                        st.markdown("---")
            else:
                st.info("ไม่มีคำขอเพิ่มอุปกรณ์ที่รอการอนุมัติในขณะนี้")
                
        with sub_req_history:
            st.markdown("#### 📜 ประวัติการอนุมัติคำขอเพิ่มอุปกรณ์")
            req_history = run_query("""
                SELECT r.id as 'รหัส', r.tech_name as 'ผู้ขอ', i.name as 'ชื่ออุปกรณ์', r.quantity as 'จำนวนที่ขอ', 
                       r.note as 'หมายเหตุ', r.request_date as 'วันที่ขอ', r.approval_date as 'วันที่อนุมัติ', r.status as 'สถานะ'
                FROM requisition_requests r JOIN items i ON r.item_id = i.id
                WHERE r.status != 'รออนุมัติ' ORDER BY r.id DESC
            """)
            if not req_history.empty:
                st.dataframe(req_history, use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีประวัติการอนุมัติคำขอ")

    with admin_menu[3]:
        render_borrow_return_system()

    with admin_menu[4]:
        st.subheader("⚙️ ตั้งค่าระบบและบัญชีช่าง")
        
        st.markdown("#### ⚠️ ตั้งค่าเกณฑ์แจ้งเตือนอุปกรณ์ทั่วไปใกล้หมด")
        with st.form("low_stock_setting_form"):
            new_threshold = st.number_input("แจ้งเตือนเมื่อจำนวนน้อยกว่าหรือเท่ากับ (ชิ้น)", min_value=0, value=low_stock_limit)
            if st.form_submit_button("บันทึกค่าเกณฑ์การแจ้งเตือน"):
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('low_stock_threshold', ?)", (str(new_threshold),), is_select=False)
                st.success("บันทึกค่าการแจ้งเตือนสำเร็จ!")
                st.rerun()
                
        st.markdown("---")
        
        st.markdown("#### 🔄 ตั้งค่าและเพิ่มโควต้าการตรวจเช็คประจำวัน (นับรวมทุกคน)")
        q_setting = run_query("SELECT value FROM settings WHERE key='global_daily_quota'")
        current_base_quota = int(q_setting.iloc[0]['value']) if not q_setting.empty else 3
        
        with st.form("global_quota_form"):
            new_base_quota = st.number_input("กำหนดโควต้ารอบตรวจมาตรฐานต่อวัน (รอบ)", min_value=1, value=current_base_quota)
            reset_date = st.date_input("เลือกวันที่ต้องการเพิ่มรอบตรวจพิเศษ", value=datetime.now().date())
            date_str = reset_date.strftime("%Y-%m-%d")
            
            extra_df = run_query("SELECT value FROM settings WHERE key=?", (f"extra_quota_{date_str}",))
            current_extra = int(extra_df.iloc[0]['value']) if not extra_df.empty else 0
            
            add_more_quota = st.number_input("ระบุจำนวนรอบที่ต้องการเพิ่มให้ตรวจอีกสำหรับวันนี้ (รอบพิเศษ)", min_value=0, value=current_extra)
            
            if st.form_submit_button("บันทึกการตั้งค่าโควต้า"):
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('global_daily_quota', ?)", (str(new_base_quota),), is_select=False)
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"extra_quota_{date_str}", str(add_more_quota)), is_select=False)
                st.success("บันทึกการตั้งค่าโควต้าเรียบร้อยแล้ว!")
                st.rerun()
                
        st.markdown("---")
        
        st.markdown("#### 🛠️ จัดการบัญชีช่าง (สร้าง / แก้ไข / ลบ)")
        
        st.markdown("**📋 รายชื่อบัญชีช่างทั้งหมดในระบบ**")
        all_techs_df = run_query("SELECT id as 'รหัส', username as 'ชื่อผู้ใช้งาน (Username)' FROM tech_users")
        st.dataframe(all_techs_df, use_container_width=True, hide_index=True)
        st.markdown("---")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**➕ เพิ่มบัญชีช่างใหม่**")
            with st.form("add_tech_form", clear_on_submit=True):
                new_t_user = st.text_input("Username ช่าง")
                new_t_pass = st.text_input("Password ช่าง", type="password")
                if st.form_submit_button("สร้างบัญชีช่าง"):
                    if new_t_user.strip() and new_t_pass.strip():
                        try:
                            run_query("INSERT INTO tech_users (username, password) VALUES (?, ?)", (new_t_user, new_t_pass), is_select=False)
                            st.success(f"สร้างบัญชีช่าง '{new_t_user}' สำเร็จ!")
                            st.rerun()
                        except:
                            st.error("Username นี้มีอยู่ในระบบแล้ว")
                    else:
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                        
        with col_t2:
            st.markdown("**✏️ แก้ไข / ลบบัญชีช่าง**")
            tech_list_df = run_query("SELECT * FROM tech_users")
            if not tech_list_df.empty:
                selected_tech_id = st.selectbox("เลือกบัญชีช่าง", tech_list_df['id'].astype(str) + " - " + tech_list_df['username'])
                if selected_tech_id:
                    t_id_int = int(selected_tech_id.split(" - ")[0])
                    t_row = tech_list_df[tech_list_df['id'] == t_id_int].iloc[0]
                    with st.form(f"edit_tech_{t_id_int}"):
                        edit_u = st.text_input("Username", value=t_row['username'])
                        edit_p = st.text_input("Password ใหม่", value=t_row['password'])
                        col_tu1, col_tu2 = st.columns(2)
                        if col_tu1.form_submit_button("บันทึกการแก้ไข"):
                            run_query("UPDATE tech_users SET username=?, password=? WHERE id=?", (edit_u, edit_p, t_id_int), is_select=False)
                            st.success("อัปเดตบัญชีช่างสำเร็จ!")
                            st.rerun()
                        if col_tu2.form_submit_button("ลบบัญชีนี้"):
                            if len(tech_list_df) <= 1:
                                st.error("ต้องเหลือบัญชีช่างไว้อย่างน้อย 1 บัญชี")
                            else:
                                run_query("DELETE FROM tech_users WHERE id=?", (t_id_int,), is_select=False)
                                st.success("ลบบัญชีช่างเรียบร้อยแล้ว!")
                                st.rerun()

elif st.session_state.role in ["ช่างทั่วไป", "ช่างประจำอาคาร"]:
    # ------------------ จอสำหรับช่าง (Technician UI) ------------------
    st.subheader("📋 หน้าต่างปฏิบัติงานช่างทั่วไป")
    
    tech_main_tab = st.tabs(["📋 ตรวจสอบสภาพอุปกรณ์", "📦 ส่งคำขอเพิ่มอุปกรณ์เข้าคลัง", "🔄 ระบบยืม-คืน อุปกรณ์"])
    
    with tech_main_tab[2]:
        render_borrow_return_system()
        
    # --- ช่าง: ส่งคำขอเพิ่มอุปกรณ์เข้าคลัง (แสดงทั้ง 'อุปกรณ์ช่างทั่วไป' และ 'อุปกรณ์สระว่ายน้ำ') ---
    with tech_main_tab[1]:
        st.markdown("### 📦 ส่งคำขอเพิ่มอุปกรณ์เข้าคลัง (อุปกรณ์ช่างทั่วไป & อุปกรณ์สระว่ายน้ำ)")
        st.write("ค้นหาและเลือกอุปกรณ์ช่างทั่วไป หรืออุปกรณ์สระว่ายน้ำที่ต้องการเพิ่มจำนวนเข้าคลัง ระบบจะส่งคำขอไปยังแอดมินเพื่อรออนุมัติบวกสต็อก")
        
        tools_requisition_df = items_df[
            ((items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['subcategory'] == 'อุปกรณ์ช่างทั่วไป')) | 
            (items_df['category'] == 'อุปกรณ์สระว่ายน้ำ')
        ]
        
        req_search_keyword = st.text_input("🔍 ค้นหาชื่ออุปกรณ์...", placeholder="พิมพ์ชื่ออุปกรณ์เพื่อค้นหา", key="req_general_search")
        if req_search_keyword.strip():
            tools_requisition_df = tools_requisition_df[tools_requisition_df['name'].str.contains(req_search_keyword.strip(), case=False, na=False)]
        
        if not tools_requisition_df.empty:
            with st.form("requisition_request_form", clear_on_submit=True):
                req_item_dict = {f"#{row['id']} {row['name']} [{row['category']}] (คงเหลือในคลัง: {row['quantity']} ชิ้น)": row['id'] for _, row in tools_requisition_df.iterrows()}
                sel_req_label = st.selectbox("เลือกอุปกรณ์ที่ต้องการเพิ่มจำนวน *", list(req_item_dict.keys()))
                
                req_selected_id = req_item_dict[sel_req_label]
                req_item_info = items_df[items_df['id'] == req_selected_id].iloc[0]
                
                req_qty = st.number_input("จำนวนที่ต้องการเพิ่มเข้าคลัง *", min_value=1, value=1)
                req_note = st.text_area("หมายเหตุ / เหตุผลที่ขอเพิ่ม *")
                
                if st.form_submit_button("📤 ส่งคำขอเพิ่มอุปกรณ์ (รอแอดมินอนุมัติ)"):
                    if req_note.strip():
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        run_query("INSERT INTO requisition_requests (tech_name, item_id, quantity, note, status, request_date) VALUES (?,?,?,?,?,?)",
                                  (st.session_state.username, req_selected_id, req_qty, req_note, 'รออนุมัติ', now_time), is_select=False)
                        st.success(f"ส่งคำขอเพิ่ม '{req_item_info['name']}' จำนวน +{req_qty} ชิ้น ไปยังแอดมินเรียบร้อยแล้ว!")
                        st.rerun()
                    else:
                        st.error("กรุณาระบุหมายเหตุหรือเหตุผลที่ขอเพิ่มอุปกรณ์")
        else:
            st.info("ไม่พบรายการอุปกรณ์ตามคำค้นหา")
            
        st.markdown("---")
        st.markdown("#### 📜 ประวัติคำขอเพิ่มอุปกรณ์ของคุณ")
        my_requests = run_query("""
            SELECT r.id as 'รหัส', i.name as 'ชื่ออุปกรณ์', r.quantity as 'จำนวนที่ขอ', r.note as 'หมายเหตุ', r.request_date as 'วันที่ขอ', r.approval_date as 'วันที่อนุมัติ', r.status as 'สถานะ'
            FROM requisition_requests r JOIN items i ON r.item_id = i.id
            WHERE r.tech_name = ? ORDER BY r.id DESC
        """, (st.session_state.username,))
        if not my_requests.empty:
            st.dataframe(my_requests, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการส่งคำขอเพิ่มอุปกรณ์")
        
    with tech_main_tab[0]:
        tech_category_choice = st.radio("เลือกหมวดหมู่การทำงาน", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
        st.markdown("---")
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
            st.markdown("### 🔧 หมวดอุปกรณ์ช่าง (คลิกชื่อเพื่อดูรูปภาพ & เช็คสถานะ)")
            
            global_inspections = run_query("SELECT COUNT(*) as cnt FROM inspections WHERE category = 'อุปกรณ์ช่าง' AND inspection_date LIKE ?", 
                                          (f"{today_str}%",))
            global_count = int(global_inspections.iloc[0]['cnt']) if not global_inspections.empty else 0
            
            q_setting = run_query("SELECT value FROM settings WHERE key='global_daily_quota'")
            base_quota = int(q_setting.iloc[0]['value']) if not q_setting.empty else 3
            
            extra_df = run_query("SELECT value FROM settings WHERE key=?", (f"extra_quota_{today_str}",))
            extra_quota = int(extra_df.iloc[0]['value']) if not extra_df.empty else 0
            
            total_allowed = base_quota + extra_quota
            
            if global_count >= total_allowed:
                st.error("⚠️ ครบโควตารอบการตรวจสำหรับวันนี้แล้ว (กรุณาติดต่อแอดมินเพื่อเพิ่มรอบตรวจพิเศษ)")
            else:
                tools_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['quantity'] > 0)]
                
                if not tools_df.empty:
                    tech_search = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
                    if tech_search.strip():
                        tools_df = tools_df[tools_df['name'].str.contains(tech_search.strip(), case=False, na=False)]
                    
                    with keyed_container("tech_check_list", height=500):
                        item_reports = {}
                        for _, row in tools_df.iterrows():
                            col_item, col_flag = st.columns([5, 1.4])
                            
                            with col_item:
                                with st.expander(f"🛠️ {row['name']} (คงเหลือ: {row['quantity']})"):
                                    pil_img = get_pil_image_from_base64(row['image'])
                                    if pil_img:
                                        st.image(pil_img, width=220, caption=f"รูปภาพ: {row['name']}")
                                    else:
                                        st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
                            
                            with col_flag:
                                is_flagged = st.checkbox("แจ้งปัญหา", key=f"flag_{row['id']}")
                            
                            issue_type = "ปกติ"
                            issue_detail = ""
                            if is_flagged:
                                issue_type = st.selectbox(
                                    "ประเภทปัญหา *", 
                                    ["-- เลือกประเภท --", "กำลังใช้งาน", "อุปกรณ์หมด", "ชำรุด", "สูญหาย"], 
                                    key=f"issue_type_{row['id']}"
                                )
                                if issue_type == "กำลังใช้งาน":
                                    issue_detail = st.text_input("ระบุรายละเอียดการใช้งาน *", key=f"issue_detail_{row['id']}")
                                    
                            item_reports[row['id']] = {"flagged": is_flagged, "status": issue_type, "detail": issue_detail}
                            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                            
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 📸 รูปถ่ายรวมหน้างาน / ภาพประกอบการตรวจเช็ค (บังคับครบทั้ง 4 รูป)")
                    if "tech_photo_count" not in st.session_state:
                        st.session_state.tech_photo_count = 4
                        
                    uploaded_photos_b64 = []
                    for i in range(4):
                        up_file = st.file_uploader(f"รูปถ่ายรวมที่ {i+1} *", type=["jpg", "jpeg", "png"], key=f"tech_p_{i}")
                        if up_file is not None:
                            b64_str = base64.b64encode(up_file.read()).decode("utf-8")
                            uploaded_photos_b64.append(b64_str)
                            
                    st.progress(len(uploaded_photos_b64) / 4, text=f"📸 แนบรูปแล้ว {len(uploaded_photos_b64)}/4 รูป")
                    if st.button(f"💾 ยืนยันส่งผลตรวจ (รอบที่ {global_count + 1})", type="primary", use_container_width=True):
                        has_error = False
                        error_msg = ""
                        
                        for item_id, data in item_reports.items():
                            if data["flagged"]:
                                if data["status"] == "-- เลือกประเภท --":
                                    has_error = True
                                    error_msg = "❌ กรุณาเลือกประเภทปัญหาให้ครบถ้วนสำหรับรายการที่ติ๊ก"
                                    break
                                if data["status"] == "กำลังใช้งาน" and not data["detail"].strip():
                                    has_error = True
                                    error_msg = "❌ กรุณากรอกรายละเอียดการใช้งานสำหรับรายการที่เลือก 'กำลังใช้งาน'"
                                    break
                        
                        if not has_error and len(uploaded_photos_b64) < 4:
                            has_error = True
                            error_msg = "❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานให้ครบทั้ง 4 รูป จึงจะสามารถยืนยันผลตรวจได้"
                            
                        if has_error:
                            st.error(error_msg)
                        else:
                            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            flagged_summaries = []
                            
                            for item_id, data in item_reports.items():
                                item_row = items_df[items_df['id'] == item_id].iloc[0]
                                curr_q = int(item_row['quantity'])
                                item_name = item_row['name']
                                
                                if data["flagged"]:
                                    final_st = data["status"]
                                    if data["status"] == "กำลังใช้งาน" and data["detail"].strip():
                                        final_st = f"กำลังใช้งาน ({data['detail']})"
                                    
                                    if data["status"] in ["อุปกรณ์หมด", "สูญหาย"]:
                                        new_q = max(0, curr_q - 1)
                                        run_query("UPDATE items SET status = ?, quantity = ? WHERE id = ?", (final_st, new_q, item_id), is_select=False)
                                    elif data["status"] == "ชำรุด":
                                        run_query("UPDATE items SET status = ? WHERE id = ?", (final_st, item_id), is_select=False)
                                    else:
                                        run_query("UPDATE items SET status = ? WHERE id = ?", (final_st, item_id), is_select=False)
                                        
                                    detail_txt = f"{item_name}: {data['status']}" + (f" ({data['detail']})" if data['detail'] else "")
                                    flagged_summaries.append(detail_txt)
                                else:
                                    run_query("UPDATE items SET status = ? WHERE id = ?", ("ปกติ", item_id), is_select=False)
                                    
                            photos_str = "|||".join(uploaded_photos_b64)
                            summary_details = ", ".join(flagged_summaries) if flagged_summaries else "ปกติทุกรายการ"
                            summary_note = f"รอบที่ {global_count+1} | รายการผิดปกติ: {summary_details}"
                            
                            run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details, photos) VALUES (?,?,?,?,?,?)",
                                      (st.session_state.username, 'อุปกรณ์ช่าง', now_time, global_count+1, summary_note, photos_str), is_select=False)
                            
                            st.success("บันทึกผลการตรวจสอบเรียบร้อยแล้ว!")
                            st.rerun()
                else:
                    st.info("ไม่มีอุปกรณ์ช่างให้ตรวจสอบในขณะนี้")
                    
        else:
            st.markdown("### 🏊 หมวดอุปกรณ์สระว่ายน้ำ (เช็คจำนวน & ดูรูปภาพ)")
            st.write("คลิกที่ชื่อรายการอุปกรณ์เพื่อดูรูปภาพ และปรับปรุงจำนวนคงเหลือ")
            
            pool_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ']
            if not pool_df.empty:
                tech_pool_search = st.text_input("🔍 ค้นหาอุปกรณ์สระว่ายน้ำ...", key="tech_pool_search_box")
                if tech_pool_search.strip():
                    pool_df = pool_df[pool_df['name'].str.contains(tech_pool_search.strip(), case=False, na=False)]
                    
                with st.container(height=500):
                    updated_quantities = {}
                    for _, row in pool_df.iterrows():
                        with st.expander(f"📦 {row['name']} (คงเหลือปัจจุบัน: {row['quantity']} ชิ้น)"):
                            pil_img = get_pil_image_from_base64(row['image'])
                            if pil_img:
                                st.image(pil_img, width=220, caption=f"รูปภาพ: {row['name']}")
                            else:
                                st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
                                
                        new_qty = st.number_input(f"จำนวนคงเหลือ: {row['name']}", min_value=0, value=int(row['quantity']), key=f"pool_q_{row['id']}")
                        updated_quantities[row['id']] = new_qty
                        st.markdown("---")
                        
                st.markdown("### 📸 รูปถ่ายรวมหน้างานสระว่ายน้ำ (บังคับครบทั้ง 4 รูป)")
                uploaded_pool_photos_b64 = []
                for i in range(4):
                    up_file = st.file_uploader(f"รูปถ่ายรวมสระที่ {i+1} *", type=["jpg", "jpeg", "png"], key=f"tech_pool_p_{i}")
                    if up_file is not None:
                        b64_str = base64.b64encode(up_file.read()).decode("utf-8")
                        uploaded_pool_photos_b64.append(b64_str)
                        
                st.progress(len(uploaded_pool_photos_b64) / 4, text=f"📸 แนบรูปแล้ว {len(uploaded_pool_photos_b64)}/4 รูป")
                if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                    if len(uploaded_pool_photos_b64) < 4:
                        st.error("❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานสระว่ายน้ำให้ครบทั้ง 4 รูป")
                    else:
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        pool_summaries = []
                        for item_id, q_val in updated_quantities.items():
                            old_row = items_df[items_df['id'] == item_id].iloc[0]
                            run_query("UPDATE items SET quantity = ? WHERE id = ?", (q_val, item_id), is_select=False)
                            if q_val != int(old_row['quantity']):
                                pool_summaries.append(f"{old_row['name']}: ปรับจาก {old_row['quantity']} เหลือ {q_val}")
                                
                        photos_str = "|||".join(uploaded_pool_photos_b64)
                        summary_note = "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ" + (f" | การเปลี่ยนแปลง: {', '.join(pool_summaries)}" if pool_summaries else "")
                        run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details, photos) VALUES (?,?,?,?,?,?)",
                                  (st.session_state.username, 'อุปกรณ์สระว่ายน้ำ', now_time, 1, summary_note, photos_str), is_select=False)
                                  
                        st.success("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")
                        st.rerun()
            else:
                st.info("ไม่มีอุปกรณ์สระว่ายน้ำในระบบ")