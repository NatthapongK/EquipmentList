import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ Pro", page_icon="🛠️", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("inventory_pro.db")
    c = conn.cursor()
    # 1. ตารางอุปกรณ์
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT
        )
    ''')
    # 2. ตารางยืม-คืน
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            borrower_name TEXT,
            borrow_date TEXT,
            return_date TEXT,
            status TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    
    # ใส่ข้อมูลเริ่มต้นหากระบบยังว่างอยู่
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone() == 0:
        c.executemany("INSERT INTO items (name, category, quantity, status, note) VALUES (?, ?, ?, ?, ?)", [
            ("สว่านกระแทกไร้สาย", "อุปกรณ์ช่าง", 2, "ปกติ", "Makita"),
            ("ประแจเลื่อน 12 นิ้ว", "อุปกรณ์ช่าง", 5, "ปกติ", "-"),
            ("ตาข่ายตักขยะสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", 1, "ชำรุด", "ด้ามหัก"),
            ("ชุดทดสอบคลอรีนและ pH", "อุปกรณ์สระว่ายน้ำ", 1, "ปกติ", "เหลือครึ่งขวด"),
            ("คลอรีนผง 90%", "อุปกรณ์สระว่ายน้ำ", 3, "ปกติ", "เหลือน้อยใกล้หมด")
        ])
        conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def run_query(query, params=(), is_select=True):
    conn = sqlite3.connect("inventory_pro.db")
    c = conn.cursor()
    c.execute(query, params)
    if is_select:
        res = c.fetchall()
        cols = [d[0] for d in c.description]
        conn.close()
        return pd.DataFrame(res, columns=cols)
    conn.commit()
    conn.close()

# --- SESSION STATE FOR LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

# --- LOGIN UI ---
if not st.session_state.logged_in:
    st.title("🔑 เข้าสู่ระบบจัดการอุปกรณ์")
    col_login, _ = st.columns([1, 2])
    with col_login:
        username = st.text_input("ชื่อผู้ใช้งาน (Username)")
        password = st.text_input("รหัสผ่าน (Password)", type="password")
        
        st.info("💡 ทดสอบระบบ:\n- แอดมิน: admin / admin123\n- ช่างทั่วไป: tech / tech123")
        
        if st.button("เข้าสู่ระบบ", type="primary"):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.role = "แอดมิน"
                st.session_state.username = "Administrator"
                st.rerun()
            elif username == "tech" and password == "tech123":
                st.session_state.logged_in = True
                st.session_state.role = "ช่างทั่วไป"
                st.session_state.username = "ช่างประจำโครงการ"
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# --- MAIN APP LOGGED IN ---
# แถบเมนูด้านบน / ปุ่ม Logout
st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.write(f"สิทธิ์การใช้งาน: **{st.session_state.role}**")
if st.sidebar.button("🔒 ออกจากระบบ"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

st.title("🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์")
st.markdown("---")

# --- ALERT SYSTEM (แจ้งเตือนสิทธิ์แอดมิน/ช่างให้เห็นร่วมกัน) ---
st.subheader("🚨 การแจ้งเตือนระบบ")
items_df = run_query("SELECT * FROM items")
broken_items = items_df[items_df['status'] == 'ชำรุด']
low_stock_items = items_df[items_df['quantity'] <= 1]

col_a1, col_a2 = st.columns(2)
with col_a1:
    if not broken_items.empty:
        st.error(f"❌ **มีอุปกรณ์ชำรุด {len(broken_items)} รายการ:** " + ", ".join(broken_items['name'].tolist()))
    else:
        st.success("✅ ไม่มีอุปกรณ์ชำรุดในระบบ")
with col_a2:
    if not low_stock_items.empty:
        st.warning(f"⚠️ **มีอุปกรณ์ใกล้หมด/จำนวนน้อย ({len(low_stock_items)} รายการ):** " + ", ".join(low_stock_items['name'].tolist()))
    else:
        st.success("✅ อุปกรณ์ทุกชิ้นมีจำนวนเพียงพอ")
st.markdown("---")

# --- DIVISION BY ROLE ---
if st.session_state.role == "แอดมิน":
    # ------------------ จอแอดมิน (Admin Dashboard) ------------------
    menu = st.tabs(["📋 ดูข้อมูล & เพิ่มอุปกรณ์", "🔄 ระบบยืม-คืนอุปกรณ์", "📊 ประวัติการยืม"])
    
    with menu[0]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("➕ เพิ่มอุปกรณ์ใหม่")
            with st.form("add_item_form", clear_on_submit=True):
                name = st.text_input("ชื่ออุปกรณ์ *")
                category = st.selectbox("หมวดหมู่", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
                quantity = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1)
                status = st.selectbox("สภาพเริ่มต้น", ["ปกติ", "ชำรุด"])
                note = st.text_area("หมายเหตุ")
                if st.form_submit_button("บันทึก"):
                    if name.strip():
                        run_query("INSERT INTO items (name, category, quantity, status, note) VALUES (?,?,?,?,?)",
                                  (name, category, quantity, status, note), is_select=False)
                        st.success("เพิ่มอุปกรณ์สำเร็จ!")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่อ")
        with c2:
            st.subheader("📦 รายการอุปกรณ์ทั้งหมด")
            st.dataframe(items_df, use_container_width=True, hide_index=True)
            
    with menu[1]:
        st.subheader("🔄 บันทึกการยืมอุปกรณ์")
        available_items = items_df[items_df['status'] == 'ปกติ']
        if not available_items.empty:
            with st.form("borrow_form", clear_on_submit=True):
                item_options = {f"{row['name']} ({row['category']})": row['id'] for _, row in available_items.iterrows()}
                selected_item_name = st.selectbox("เลือกอุปกรณ์ที่ต้องการยืม", list(item_options.keys()))
                borrower = st.text_input("ชื่อผู้ยืมอุปกรณ์ *")
                if st.form_submit_button("ยืนยันการยืม"):
                    if borrower.strip():
                        item_id = item_options[selected_item_name]
                        today = datetime.now().strftime("%Y-%m-%d %H:%M")
                        # บันทึกประวัติยืม
                        run_query("INSERT INTO transactions (item_id, borrower_name, borrow_date, status) VALUES (?,?,?,?)",
                                  (item_id, borrower, today, "กำลังยืม"), is_select=False)
                        st.success(f"บันทึกการยืม '{selected_item_name}' โดยคุณ {borrower} แล้ว")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่อผู้ยืม")
        else:
            st.info("ไม่มีอุปกรณ์สภาพปกติเหลือให้ยืมในขณะนี้")
            
        st.markdown("---")
        st.subheader("🔙 รายการที่กำลังถูกยืม (คลิกเพื่อคืน)")
        borrowed_df = run_query("""
            SELECT t.id as tx_id, i.name, i.category, t.borrower_name, t.borrow_date 
            FROM transactions t JOIN items i ON t.item_id = i.id WHERE t.status = 'กำลังยืม'
        """)
        if not borrowed_df.empty:
            for _, row in borrowed_df.iterrows():
                col_b1, col_b2 = st.columns([3, 1])
                col_b1.write(f"📦 **{row['name']}** ({row['category']}) - ยืมโดย: **{row['borrower_name']}** เมื่อ {row['borrow_date']}")
                if col_b2.button("รับคืนอุปกรณ์", key=f"ret_{row['tx_id']}"):
                    today = datetime.now().strftime("%Y-%m-%d %H:%M")
                    run_query("UPDATE transactions SET return_date = ?, status = 'คืนแล้ว' WHERE id = ?", (today, row['tx_id']), is_select=False)
                    st.success("บันทึกการคืนเรียบร้อย!")
                    st.rerun()
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่ถูกยืมอยู่ในขณะนี้")

    with menu[2]:
        st.subheader("📜 ประวัติการยืม-คืนทั้งหมด")
        history_df = run_query("""
            SELECT i.name as 'ชื่ออุปกรณ์', i.category as 'หมวดหมู่', t.borrower_name as 'ผู้ยืม', 
                   t.borrow_date as 'วันที่ยืม', t.return_date as 'วันที่คืน', t.status as 'สถานะ'
            FROM transactions t JOIN items i ON t.item_id = i.id ORDER BY t.id DESC
        """)
        st.dataframe(history_df, use_container_width=True, hide_index=True)

elif st.session_state.role == "ช่างทั่วไป":
    # ------------------ จอสำหรับช่าง (Technician UI) ------------------
    st.subheader("📋 หน้าต่างเช็คสภาพอุปกรณ์ประจำวันสำหรับช่าง")
    st.write("คำชี้แจง: ให้ทำเครื่องหมายติ๊กเลือก (✅) เฉพาะ **อุปกรณ์ที่ชำรุด** เท่านั้น อันไหนไม่ได้ติ๊กระบบจะถือว่าสภาพ **ปกติ**")
    
    # ดึงรายชื่ออุปกรณ์มาทำ Checklist
    with st.form("tech_checklist"):
        updated_statuses = {}
        
        # แยกหมวดหมู่ให้ช่างดูง่ายสแกนไว
        for cat in ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"]:
            st.markdown(f"### 📍 หมวด{cat}")
            cat_items = items_df[items_df['category'] == cat]
            
            for _, row in cat_items.iterrows():
                # ถ้าสถานะเดิมใน DB ชำรุดอยู่แล้ว ให้ติ๊กค้างไว้เป็น Default
                is_broken_default = True if row['status'] == 'ชำรุด' else False
                
                is_broken = st.checkbox(
                    f"รหัส #{row['id']} - **{row['name']}** (จำนวนคงเหลือ: {row['quantity']} ชิ้น)", 
                    value=is_broken_default,
                    key=f"item_{row['id']}"
                )
                # บันทึกผลลัพธ์จากติ๊ก
                updated_statuses[row['id']] = "ชำรุด" if is_broken else "ปกติ"
        
        st.markdown("---")
