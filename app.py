import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ Pro", page_icon="🛠️", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("inventory_pro.db", check_same_thread=False)
    c = conn.cursor()
    
    # 1. ตารางอุปกรณ์
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
    
    # 2. ตารางยืม-คืน
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            borrower_name TEXT,
            borrow_date TEXT,
            return_date TEXT,
            status TEXT,
            borrower_image TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    
    # ตรวจสอบและเพิ่ม column borrower_image หากยังไม่มีในฐานข้อมูลเดิม
    c.execute("PRAGMA table_info(transactions)")
    tx_cols = [col[1] for col in c.fetchall()]
    if 'borrower_image' not in tx_cols:
        c.execute("ALTER TABLE transactions ADD COLUMN borrower_image TEXT")
        conn.commit()

    # 3. ตารางบัญชีช่าง
    c.execute('''
        CREATE TABLE IF NOT EXISTS tech_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 4. ตารางประวัติการตรวจเช็คของช่าง
    c.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tech_name TEXT,
            category TEXT,
            inspection_date TEXT,
            session_num INTEGER,
            details TEXT
        )
    ''')

    # 5. ตารางตั้งค่าระบบ
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('low_stock_threshold', '1')")
    conn.commit()
    
    # ใส่ข้อมูลเริ่มต้นหากระบบยังว่างอยู่
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone() == 0:
        c.executemany("INSERT INTO items (name, category, subcategory, quantity, status, note, image) VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("สว่านกระแทกไร้สาย", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "Makita", None),
            ("ประแจเลื่อน 12 นิ้ว", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 5, "ปกติ", "-", None),
            ("ตู้เชื่อมไฟฟ้า portable", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
            ("บันไดอลูมิเนียม 8 ฟุต", "อุปกรณ์ช่าง", "อุปกรณ์ช่างทั่วไป", 3, "ปกติ", "-", None),
            ("ตาข่ายตักขยะสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", "-", 1, "ชำรุด", "ด้ามหัก", None),
            ("ชุดทดสอบคลอรีนและ pH", "อุปกรณ์สระว่ายน้ำ", "-", 1, "ปกติ", "เหลือครึ่งขวด", None),
            ("คลอรีนผง 90%", "อุปกรณ์สระว่ายน้ำ", "-", 3, "ปกติ", "เหลือน้อยใกล้หมด", None)
        ])
        conn.commit()
        
    c.execute("SELECT COUNT(*) FROM tech_users")
    if c.fetchone() == 0:
        c.execute("INSERT INTO tech_users (username, password) VALUES (?, ?)", ("tech", "tech123"))
        conn.commit()
        
    conn.close()

init_db()

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
        # ป้องกัน Type Error ของ quantity
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
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
        
        tech_df = run_query("SELECT * FROM tech_users")
        
        if st.button("เข้าสู่ระบบ", type="primary"):
            if username == "Natthapongk" and password == "0891148075":
                st.session_state.logged_in = True
                st.session_state.role = "แอดมิน"
                st.session_state.username = "Natthapongk"
                st.rerun()
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)]
                if not matched_tech.empty:
                    st.session_state.logged_in = True
                    st.session_state.role = "ช่างทั่วไป"
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# --- MAIN APP LOGGED IN ---
st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.write(f"สิทธิ์การใช้งาน: **{st.session_state.role}**")
if st.sidebar.button("🔒 ออกจากระบบ"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

st.title("🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์")
st.markdown("---")

# --- ALERT SYSTEM ---
setting_df = run_query("SELECT value FROM settings WHERE key='low_stock_threshold'")
low_stock_limit = int(setting_df.iloc[0]['value']) if not setting_df.empty else 1

st.subheader("🚨 การแจ้งเตือนระบบ")
items_df = run_query("SELECT * FROM items")

abnormal_items = items_df[items_df['status'].isin(['ชำรุด', 'สูญหาย', 'ยืม'])]
non_tools_df = items_df[items_df['subcategory'] != 'เครื่องมือช่าง']
low_stock_items = non_tools_df[non_tools_df['quantity'] <= low_stock_limit]

col_a1, col_a2 = st.columns(2)
with col_a1:
    if not abnormal_items.empty:
        alert_text = [f"{row['name']} ({row['status']})" for _, row in abnormal_items.iterrows()]
        st.error(f"❌ **มีอุปกรณ์ผิดปกติ/ถูกยืม ({len(abnormal_items)} รายการ):** " + ", ".join(alert_text))
    else:
        st.success("✅ อุปกรณ์ทุกชิ้นอยู่ในสภาพปกติ")
with col_a2:
    if not low_stock_items.empty:
        st.warning(f"⚠️ **มีอุปกรณ์ทั่วไปเหลือน้อยกว่า/เท่ากับ {low_stock_limit} ชิ้น ({len(low_stock_items)} รายการ):** " + ", ".join(low_stock_items['name'].tolist()))
    else:
        st.success(f"✅ อุปกรณ์ทั่วไปทุกชิ้นมีจำนวนเพียงพอ")
st.markdown("---")

# --- DIVISION BY ROLE ---
if st.session_state.role == "แอดมิน":
    admin_menu = st.tabs([
        "🔄 1. ยืม-คืน เครื่องมือ-อุปกรณ์", 
        "📋 2. จัดการอุปกรณ์ทั้งหมด", 
        "📊 3. รายงานการตรวจเช็ค", 
        "⚙️ 4. ตั้งค่าระบบ & รหัสช่าง"
    ])
    
    with admin_menu[0]:
        st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
        sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])
        
        with sub_borrow:
            available_items = items_df[items_df['quantity'] > 0]
            if not available_items.empty:
                with st.form("admin_borrow_form", clear_on_submit=True):
                    item_dict = {f"#{row['id']} {row['name']} (คงเหลือ: {row['quantity']} ชิ้น) [{row['category']}]": row['id'] for _, row in available_items.iterrows()}
                    sel_item_label = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(item_dict.keys()))
                    borrower_name = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                    borrow_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายผู้ยืมหรือหลักฐานการยืม *", type=["jpg", "jpeg", "png"])
                    
                    if st.form_submit_button("ยืนยันการยืมอุปกรณ์"):
                        if borrower_name.strip() and borrow_img_file is not None:
                            selected_id = item_dict[sel_item_label]
                            item_info = items_df[items_df['id'] == selected_id].iloc[0]
                            
                            b_img_bytes = borrow_img_file.read()
                            b_img_b64 = base64.b64encode(b_img_bytes).decode("utf-8")
                            now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                            
                            run_query("INSERT INTO transactions (item_id, borrower_name, borrow_date, status, borrower_image) VALUES (?,?,?,?,?)",
                                      (selected_id, borrower_name, now_time, "กำลังยืม", b_img_b64), is_select=False)
                            
                            new_qty = int(item_info['quantity']) - 1
                            new_status = 'ยืม' if new_qty == 0 else item_info['status']
                            
                            run_query("UPDATE items SET quantity = ?, status = ? WHERE id = ?", (new_qty, new_status, selected_id), is_select=False)
                            
                            st.success(f"บันทึกการยืม {item_info['name']} เรียบร้อยแล้ว")
                            st.rerun()
                        else:
                            st.error("กรุณากรอกชื่อผู้ยืมและอัปโหลดรูปถ่ายผู้ยืม/หลักฐานการยืมให้ครบถ้วน")
            else:
                st.info("ไม่มีอุปกรณ์ที่มีจำนวนคงเหลือให้ยืมในขณะนี้")
                
        with sub_return:
            st.markdown("#### รายการที่กำลังถูกยืมอยู่")
            active_tx = run_query("""
                SELECT t.id as tx_id, t.item_id, i.name as item_name, t.borrower_name, t.borrow_date, t.borrower_image, i.quantity
                FROM transactions t JOIN items i ON t.item_id = i.id 
                WHERE t.status = 'กำลังยืม' ORDER BY t.id DESC
            """)
            
            if not active_tx.empty:
                for _, row in active_tx.iterrows():
                    with st.expander(f"📦 อุปกรณ์: {row['item_name']} | ผู้ยืม: {row['borrower_name']} (ยืมเมื่อ: {row['borrow_date']})"):
                        col_r1, col_r2 = st.columns([1, 2])
                        with col_r1:
                            p_img = get_pil_image_from_base64(row['borrower_image'])
                            if p_img:
                                st.image(p_img, caption=f"รูปถ่ายผู้ยืม: {row['borrower_name']}", width=200)
                            else:
                                st.write("*(ไม่มีรูปถ่าย)*")
                        with col_r2:
                            st.write(f"**ชื่ออุปกรณ์:** {row['item_name']}")
                            st.write(f"**ผู้ยืม:** {row['borrower_name']}")
                            st.write(f"**วันที่ยืม:** {row['borrow_date']}")
                            if st.button(f"✅ รับคืนอุปกรณ์รายการนี้", key=f"ret_btn_{row['tx_id']}"):
                                now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                                run_query("UPDATE transactions SET return_date = ?, status = 'คืนแล้ว' WHERE id = ?", (now_time, row['tx_id']), is_select=False)
                                
                                current_item = items_df[items_df['id'] == row['item_id']].iloc[0]
                                new_q = int(current_item['quantity']) + 1
                                run_query("UPDATE items SET quantity = ?, status = 'ปกติ' WHERE id = ?", (new_q, row['item_id']), is_select=False)
                                
                                st.success(f"รับคืน {row['item_name']} เรียบร้อยแล้ว")
                                st.rerun()
            else:
                st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืมในขณะนี้")
                
        with sub_history:
            st.markdown("#### ประวัติการยืม-คืนทั้งหมด")
            tx_history = run_query("""
                SELECT t.id as 'รหัส', i.name as 'ชื่ออุปกรณ์', t.borrower_name as 'ผู้ยืม', 
                       t.borrow_date as 'วันที่ยืม', t.return_date as 'วันที่คืน', t.status as 'สถานะ'
                FROM transactions t JOIN items i ON t.item_id = i.id ORDER BY t.id DESC
            """)
            st.dataframe(tx_history, use_container_width=True, hide_index=True)

    with admin_menu[1]:
        st.subheader("📋 จัดการอุปกรณ์ทั้งหมดในระบบ")
        tab_list, tab_add_edit = st.tabs(["🔍 ดูรายการทั้งหมด", "➕ เพิ่ม/แก้ไขอุปกรณ์"])
        
        with tab_list:
            c_f1, c_f2, c_f3 = st.columns([2, 1, 1])
            search_kw = c_f1.text_input("🔍 ค้นหาชื่ออุปกรณ์...", placeholder="พิมพ์ชื่ออุปกรณ์เพื่อค้นหา")
            cat_filter = c_f2.selectbox("กรองตามหมวดหลัก", ["ทั้งหมด", "อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
            status_filter = c_f3.selectbox("กรองตามสถานะ", ["ทั้งหมด", "ปกติ", "ชำรุด", "สูญหาย", "ยืม"])
            
            filtered_df = items_df.copy()
            if search_kw.strip():
                filtered_df = filtered_df[filtered_df['name'].str.contains(search_kw.strip(), case=False, na=False)]
            if cat_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['category'] == cat_filter]
            if status_filter != "ทั้งหมด":
                filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
            st.caption(f"แสดงรายการอุปกรณ์ทั้งหมด {len(filtered_df)} จาก {len(items_df)} รายการ")
            st.dataframe(
                filtered_df[['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'note']], 
                use_container_width=True, 
                hide_index=True,
                height=400
            )

        with tab_add_edit:
            sub_a, sub_e = st.tabs(["➕ เพิ่มอุปกรณ์ใหม่", "✏️ แก้ไข/ลบ รายการ"])
            with sub_a:
                with st.form("add_item_form_new", clear_on_submit=True):
                    name = st.text_input("ชื่ออุปกรณ์ *")
                    category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
                    subcategory = "-"
                    if category == "อุปกรณ์ช่าง":
                        subcategory = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"])
                    quantity = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1)
                    status = st.selectbox("สภาพเริ่มต้น", ["ปกติ", "ชำรุด", "สูญหาย"])
                    note = st.text_area("หมายเหตุ")
                    uploaded_file = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์", type=["jpg", "jpeg", "png"])
                    
                    if st.form_submit_button("บันทึกอุปกรณ์ใหม่"):
                        if name.strip():
                            img_base64 = None
                            if uploaded_file is not None:
                                img_bytes = uploaded_file.read()
                                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            run_query("INSERT INTO items (name, category, subcategory, quantity, status, note, image) VALUES (?,?,?,?,?,?,?)",
                                      (name, category, subcategory, quantity, status, note, img_base64), is_select=False)
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
                            e_subcat = "-"
                            if e_category == "อุปกรณ์ช่าง":
                                sub_idx = 0 if current_item['subcategory'] == "เครื่องมือช่าง" else 1
                                e_subcat = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"], index=sub_idx)
                            e_quantity = st.number_input("จำนวน", min_value=0, value=int(current_item['quantity']))
                            status_list = ["ปกติ", "ชำรุด", "สูญหาย", "ยืม"]
                            e_status = st.selectbox("สถานะ", status_list, index=status_list.index(current_item['status']) if current_item['status'] in status_list else 0)
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
                                run_query("UPDATE items SET name=?, category=?, subcategory=?, quantity=?, status=?, note=?, image=? WHERE id=?",
                                          (e_name, e_category, e_subcat, e_quantity, e_status, e_note, img_base64, item_id_int), is_select=False)
                                st.success("อัปเดตข้อมูลสำเร็จ!")
                                st.rerun()
                            if col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary"):
                                run_query("DELETE FROM items WHERE id=?", (item_id_int,), is_select=False)
                                st.success("ลบเรียบร้อยแล้ว!")
                                st.rerun()

    with admin_menu[2]:
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
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการตรวจเช็คจากช่างในระบบ")

    with admin_menu[3]:
        st.subheader("⚙️ ตั้งค่าระบบและบัญชีช่าง")
        st.markdown("#### ⚠️ ตั้งค่าเกณฑ์แจ้งเตือนอุปกรณ์ทั่วไปใกล้หมด")
        with st.form("low_stock_setting_form"):
            new_threshold = st.number_input("แจ้งเตือนเมื่อจำนวนน้อยกว่าหรือเท่ากับ (ชิ้น)", min_value=0, value=low_stock_limit)
            if st.form_submit_button("บันทึกค่าเกณฑ์การแจ้งเตือน"):
                run_query("INSERT OR REPLACE INTO settings (key, value) VALUES ('low_stock_threshold', ?)", (str(new_threshold),), is_select=False)
                st.success("บันทึกค่าการแจ้งเตือนสำเร็จ!")
                st.rerun()
                
        st.markdown("---")
        st.markdown("#### 🔄 รีเซ็ตโควต้าการตรวจเช็คประจำวันของช่าง")
        tech_list_df = run_query("SELECT * FROM tech_users")
        if not tech_list_df.empty:
            with st.form("reset_quota_form"):
                reset_tech_user = st.selectbox("เลือกช่างที่ต้องการรีเซ็ตโควต้า", tech_list_df['username'].tolist())
                reset_date = st.date_input("เลือกวันที่ต้องการรีเซ็ตโควต้า", value=datetime.now().date())
                if st.form_submit_button("รีเซ็ตโควต้าการตรวจวันนี้"):
                    date_str = reset_date.strftime("%Y-%m-%d")
                    run_query("DELETE FROM inspections WHERE tech_name = ? AND inspection_date LIKE ?", (reset_tech_user, f"{date_str}%"), is_select=False)
                    st.success(f"รีเซ็ตโควต้าการตรวจของช่าง '{reset_tech_user}' สำหรับวันที่ {date_str} เรียบร้อยแล้ว")
                    st.rerun()
                    
        st.markdown("---")
        st.markdown("#### 🛠️ จัดการบัญชีช่าง (สร้าง / แก้ไข / ลบ)")
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

elif st.session_state.role == "ช่างทั่วไป":
    # ------------------ จอสำหรับช่าง (Technician UI) ------------------
    st.subheader("📋 หน้าต่างปฏิบัติงานช่างทั่วไป")
    tech_category_choice = st.radio("เลือกหมวดหมู่การทำงาน", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
    st.markdown("---")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
        st.markdown("### 🔧 หมวดอุปกรณ์ช่าง (คลิกชื่อเพื่อดูรูปภาพ & เช็คสถานะ)")
        st.write("คำชี้แจง: คลิกที่ชื่ออุปกรณ์เพื่อดูรูปภาพ และทำเครื่องหมายแจ้งปัญหา (ชำรุด หรือ สูญหาย)")
        
        today_inspections = run_query("SELECT COUNT(*) as cnt FROM inspections WHERE tech_name = ? AND category = 'อุปกรณ์ช่าง' AND inspection_date LIKE ?", 
                                      (st.session_state.username, f"{today_str}%"))
        check_count = int(today_inspections.iloc[0]['cnt']) if not today_inspections.empty else 0
        
        st.info(f"📌 วันนี้ส่งตรวจหมวดอุปกรณ์ช่างไปแล้ว **{check_count}/3 ครั้ง**")
        
        if check_count >= 3:
            st.error("⚠️ ครบโควต้า 3 ครั้งสำหรับวันนี้แล้ว (หากต้องการตรวจเพิ่ม ให้ติดต่อแอดมินเพื่อรีเซ็ต)")
        else:
            tools_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['quantity'] > 0)]
            
            if not tools_df.empty:
                tech_search = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
                if tech_search.strip():
                    tools_df = tools_df[tools_df['name'].str.contains(tech_search.strip(), case=False, na=False)]
                
                with st.container(height=500):
                    item_reports = {}
                    for _, row in tools_df.iterrows():
                        # ใช้ Expander ให้ช่างคลิกดูชื่อ/รูปภาพได้ และแสดงตัวเลือกในตัว
                        with st.expander(f"🛠️ {row['name']} (คงเหลือ: {row['quantity']})"):
                            pil_img = get_pil_image_from_base64(row['image'])
                            if pil_img:
                                st.image(pil_img, width=220, caption=f"รูปภาพ: {row['name']}")
                            else:
                                st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
                        
                        col_c1, col_c2 = st.columns([1, 2])
                        with col_c1:
                            is_flagged = st.checkbox("แจ้งปัญหา", key=f"flag_{row['id']}")
                        with col_c2:
                            issue_type = "ปกติ"
                            if is_flagged:
                                issue_type = st.selectbox(
                                    "ประเภทปัญหา *", 
                                    ["-- เลือกประเภท --", "ชำรุด", "สูญหาย"], 
                                    key=f"issue_type_{row['id']}"
                                )
                        item_reports[row['id']] = {"flagged": is_flagged, "status": issue_type}
                        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                        
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"💾 ยืนยันส่งผลตรวจ (ครั้งที่ {check_count + 1})", type="primary", use_container_width=True):
                    has_error = False
                    for item_id, data in item_reports.items():
                        if data["flagged"] and data["status"] == "-- เลือกประเภท --":
                            has_error = True
                            break
                            
                    if has_error:
                        st.error("❌ กรุณาเลือกประเภทปัญหา (ชำรุด หรือ สูญหาย) ให้ครบสำหรับรายการที่ติ๊กแจ้งปัญหา")
                    else:
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for item_id, data in item_reports.items():
                            final_st = data["status"] if data["flagged"] else "ปกติ"
                            run_query("UPDATE items SET status = ? WHERE id = ?", (final_st, item_id), is_select=False)
                            
                        summary_note = f"ตรวจครั้งที่ {check_count+1}: อัปเดตสถานะอุปกรณ์ช่าง"
                        run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details) VALUES (?,?,?,?,?)",
                                  (st.session_state.username, 'อุปกรณ์ช่าง', now_time, check_count+1, summary_note), is_select=False)
                        
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
                    
            if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item_id, q_val in updated_quantities.items():
                    run_query("UPDATE items SET quantity = ? WHERE id = ?", (q_val, item_id), is_select=False)
                    
                run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details) VALUES (?,?,?,?,?)",
                          (st.session_state.username, 'อุปกรณ์สระว่ายน้ำ', now_time, 1, "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ"), is_select=False)
                          
                st.success("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")
                st.rerun()
        else:
            st.info("ไม่มีอุปกรณ์สระว่ายน้ำในระบบ")
