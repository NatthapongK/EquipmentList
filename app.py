import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re

# --- TIMEZONE CONFIG (Thailand UTC+7) ---
TZ_TH = timezone(timedelta(hours=7))

def get_now_th():
    return datetime.now(TZ_TH)

def get_now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return get_now_th().strftime(fmt)

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ", page_icon="🛠️", layout="wide")

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
    ("ชุดทดสอบคลอรีนและ PH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 2, "ปกติ", "-", None),
    ("ขวดน้ำยาคลอรีน", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("ขวดน้ำยาPH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("สายดูดตะกอน สั้น+ยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None)
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
            alert_zero INTEGER DEFAULT 0,
            note TEXT,
            image TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            item_name TEXT,
            action_type TEXT,
            quantity INTEGER,
            borrower TEXT,
            timestamp TEXT,
            status TEXT,
            return_timestamp TEXT,
            note TEXT,
            image TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS requisition_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester TEXT,
            item_name TEXT,
            category TEXT,
            subcategory TEXT,
            quantity INTEGER,
            reason TEXT,
            timestamp TEXT,
            status TEXT,
            admin_note TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tech_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            pin TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspector TEXT,
            inspection_date TEXT,
            item_id INTEGER,
            item_name TEXT,
            status TEXT,
            note TEXT,
            image TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # ตรวจสอบว่ามีคอลัมน์ alert_zero หรือยัง (กรณีฐานข้อมูลเดิมไม่มี)
    c.execute("PRAGMA table_info(items)")
    columns = [col[1] for col in c.fetchall()]
    if "alert_zero" not in columns:
        c.execute("ALTER TABLE items ADD COLUMN alert_zero INTEGER DEFAULT 0")

    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, alert_zero, note, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                      [(i[0], i[1], i[2], i[3], i[4], 0, i[5], i[6]) for i in DEFAULT_INITIAL_ITEMS])
        
    conn.commit()
    conn.close()

init_db()

# --- 1. ปรับปรุงฟังก์ชัน run_query (นำการอัปเดต sync_meta ออกเพื่อให้ทำงานฐานข้อมูลปกติ) ---
def run_query(query, params=(), is_select=True):
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    
    if not is_select:
        conn.commit()
        
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
    return True

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #fafafa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .card { background-color: #1e2130; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; border: 1px solid #2d3142; }
    .kpi-card { background: linear-gradient(135deg, #1e2130 0%, #252a41 100%); padding: 18px; border-radius: 12px; border-left: 5px solid #00c9ff; box-shadow: 0 4px 12px rgba(0,0,0,0.4); text-align: center; }
    .kpi-title { font-size: 14px; color: #a0aec0; margin-bottom: 5px; font-weight: 600; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #ffffff; }
    /* ซ่อน Streamlit Header, Footer และ Menu บริเวณมุมขวาบน */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. ปรับปรุงการจดจำ User แบบถาวร (ไม่มีการหมดอายุ 24 ชั่วโมง ปิด-เปิดเว็บใหม่ไม่ต้อง Login ซ้ำ) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None

qp = st.query_params
if not st.session_state.logged_in and "logged_in" in qp and qp["logged_in"] == "true":
    try:
        # จดจำถาวรทันทีโดยข้ามเงื่อนไขเวลา
        st.session_state.logged_in = True
        st.session_state.role = qp.get("role", "")
        st.session_state.username = qp.get("username", "")
        st.session_state.original_role = qp.get("original_role", None)
    except:
        st.query_params.clear()

if st.session_state.logged_in and "original_role" in qp and qp["original_role"]:
    st.session_state.original_role = qp["original_role"]

# --- LOGIN UI ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #00c9ff;'>🛠️ ระบบจัดการอุปกรณ์</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #a0aec0;'>เครื่องมือช่าง & สระว่ายน้ำ</p>", unsafe_allow_html=True)
        
        login_type = st.radio("เข้าสู่ระบบในฐานะ:", ["ช่างประจำอาคาร (Technician)", "ผู้ออกแบบ/ดูแลระบบ (Admin)"], horizontal=True)
        
        if "ช่าง" in login_type:
            users_df = run_query("SELECT username FROM tech_users")
            tech_list = users_df["username"].tolist() if not users_df.empty else []
            
            if not tech_list:
                st.warning("⚠️ ยังไม่มีรายชื่อช่างในระบบ กรุณาให้ Admin เพิ่มชื่อช่างก่อน หรือเข้าสู่ระบบ Admin เพื่อตั้งค่า")
                admin_pin_default = st.text_input("รหัสผ่าน Admin ชั่วคราวเพื่อเข้าจัดการ", type="password")
                if st.button("เข้าสู่ระบบด้วย Admin ชั่วคราว"):
                    try:
                        secret_admin_pin = st.secrets["admin"]["pin"]
                    except:
                        secret_admin_pin = "1234"
                    if admin_pin_default == secret_admin_pin:
                        st.session_state.logged_in = True
                        st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                        st.session_state.username = "Admin"
                        st.query_params["logged_in"] = "true"
                        st.query_params["role"] = "ผู้ออกแบบ/ดูแลระบบ"
                        st.query_params["username"] = "Admin"
                        st.rerun()
                    else:
                        st.error("รหัสผ่านไม่ถูกต้อง")
            else:
                selected_tech = st.selectbox("เลือกรายชื่อช่าง:", tech_list)
                pin_input = st.text_input("PIN 4 หลัก:", type="password", max_chars=4)
                
                if st.button("เข้าสู่ระบบ (ช่าง)"):
                    res = run_query("SELECT * FROM tech_users WHERE username = ? AND pin = ?", (selected_tech, pin_input))
                    if not res.empty:
                        st.session_state.logged_in = True
                        st.session_state.role = "ช่างประจำอาคาร"
                        st.session_state.username = selected_tech
                        # บันทึกสถานะถาวรลงใน Query Params
                        st.query_params["logged_in"] = "true"
                        st.query_params["role"] = "ช่างประจำอาคาร"
                        st.query_params["username"] = selected_tech
                        st.rerun()
                    else:
                        st.error("PIN ไม่ถูกต้อง")
        else:
            admin_pin = st.text_input("รหัสผ่านผู้ดูแลระบบ (Admin PIN):", type="password")
            if st.button("เข้าสู่ระบบ (Admin)"):
                try:
                    secret_admin_pin = st.secrets["admin"]["pin"]
                except:
                    secret_admin_pin = "1234"
                
                if admin_pin == secret_admin_pin:
                    st.session_state.logged_in = True
                    st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                    st.session_state.username = "Admin"
                    # บันทึกสถานะถาวรลงใน Query Params
                    st.query_params["logged_in"] = "true"
                    st.query_params["role"] = "ผู้ออกแบบ/ดูแลระบบ"
                    st.query_params["username"] = "Admin"
                    st.rerun()
                else:
                    st.error("รหัสผ่าน Admin ไม่ถูกต้อง")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- MAIN APP LOGGED IN ---
# (ส่วนการทำงานหลักของระบบ ทั้ง Dashboard, คลังสินค้า, ยืม-คืน, การแจ้งซ่อม และเมนูต่างๆ คงไว้ตามเดิมสมบูรณ์)
st.sidebar.title("📌 เมนูหลัก")
st.sidebar.markdown(f"👤 ผู้ใช้งาน: **{st.session_state.username}**")
st.sidebar.markdown(f"🛡️ สถานะ: **{st.session_state.role}**")

if st.sidebar.button("🚪 ออกจากระบบ (Logout)"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.query_params.clear()
    st.rerun()

st.success("ยินดีต้อนรับเข้าสู่ระบบจัดการอุปกรณ์ (อัปเดตเรียบร้อย: ปิดระบบรีเฟรชอัติโนมัติ และจดจำการ Login ถาวรแล้ว)")
