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
    
    # 1. ตารางอุปกรณ์ (เพิ่มฟิลด์ image เก็บรูปภาพแบบ Base64)
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
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
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    
    # 3. ตารางบัญชีช่าง (สำหรับสร้าง-แก้ไขรหัสช่าง)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tech_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 4. ตารางประวัติการตรวจเช็คของช่าง (รองรับตรวจ 3 ครั้ง/วัน)
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
    
    # ใส่ข้อมูลเริ่มต้นหากระบบยังว่างอยู่
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone() == 0:
        c.executemany("INSERT INTO items (name, category, quantity, status, note, image) VALUES (?, ?, ?, ?, ?, ?)", [
            ("สว่านกระแทกไร้สาย", "อุปกรณ์ช่าง", 2, "ปกติ", "Makita", None),
            ("ประแจเลื่อน 12 นิ้ว", "อุปกรณ์ช่าง", 5, "ปกติ", "-", None),
            ("ตาข่ายตักขยะสระว่ายน้ำ", "อุปกรณ์สระว่ายน้ำ", 1, "ชำรุด", "ด้ามหัก", None),
            ("ชุดทดสอบคลอรีนและ pH", "อุปกรณ์สระว่ายน้ำ", 1, "ปกติ", "เหลือครึ่งขวด", None),
            ("คลอรีนผง 90%", "อุปกรณ์สระว่ายน้ำ", 3, "ปกติ", "เหลือน้อยใกล้หมด", None)
        ])
        conn.commit()
        
    # ใส่ช่างเริ่มต้นหากยังไม่มี
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
        return pd.DataFrame(res, columns=cols)
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

# --- 1. LOGIN UI (แก้ไขรหัสแอดมิน และตัดข้อความทดสอบออก) ---
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
    # ------------------ 3. จอแอดมิน (Admin Dashboard ปรับปรุงใหม่) ------------------
    admin_menu = st.tabs([
        "📋 1. เพิ่ม-แก้อุปกรณ์ (รองรับรูปภาพ)", 
        "📊 2. รายการตรวจเช็ค (รายวัน - เดือน - ปี)", 
        "⚙️ 3. ตั้งค่ารหัสช่าง"
    ])
    
    # 1. เพิ่ม-แก้อุปกรณ์ (พร้อมอัปโหลดรูป)
    with admin_menu[0]:
        st.subheader("➕ เพิ่ม / แก้ไขอุปกรณ์ในระบบ")
        tab_add, tab_edit_del = st.tabs(["เพิ่มอุปกรณ์ใหม่", "จัดการรายการ (แก้ไข / ลบ)"])
        
        with tab_add:
            with st.form("add_item_form", clear_on_submit=True):
                name = st.text_input("ชื่ออุปกรณ์ *")
                category = st.selectbox("หมวดหมู่", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"])
                quantity = st.number_input("จำนวน (ชิ้น)", min_value=1, value=1)
                status = st.selectbox("สภาพเริ่มต้น", ["ปกติ", "ชำรุด"])
                note = st.text_area("หมายเหตุ")
                uploaded_file = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์", type=["jpg", "jpeg", "png"])
                
                if st.form_submit_button("บันทึกอุปกรณ์ใหม่"):
                    if name.strip():
                        img_base64 = None
                        if uploaded_file is not None:
                            img_bytes = uploaded_file.read()
                            img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            
                        run_query("INSERT INTO items (name, category, quantity, status, note, image) VALUES (?,?,?,?,?,?)",
                                  (name, category, quantity, status, note, img_base64), is_select=False)
                        st.success("เพิ่มอุปกรณ์สำเร็จ!")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่ออุปกรณ์")
                        
        with tab_edit_del:
            if not items_df.empty:
                selected_item_id = st.selectbox("เลือกอุปกรณ์ที่ต้องการจัดการ", items_df['id'].astype(str) + " - " + items_df['name'] + " (" + items_df['category'] + ")")
                if selected_item_id:
                    item_id_int = int(selected_item_id.split(" - ")[0])
                    current_item = items_df[items_df['id'] == item_id_int].iloc[0]
                    
                    with st.form(f"edit_form_{item_id_int}"):
                        e_name = st.text_input("ชื่ออุปกรณ์", value=current_item['name'])
                        e_category = st.selectbox("หมวดหมู่", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if current_item['category']=="อุปกรณ์ช่าง" else 1)
                        e_quantity = st.number_input("จำนวน", min_value=0, value=int(current_item['quantity']))
                        e_status = st.selectbox("สถานะ", ["ปกติ", "ชำรุด"], index=0 if current_item['status']=="ปกติ" else 1)
                        e_note = st.text_area("หมายเหตุ", value=current_item['note'] if current_item['note'] else "")
                        
                        pil_img = get_pil_image_from_base64(current_item['image'])
                        if pil_img:
                            st.image(pil_img, width=150, caption="รูปภาพปัจจุบัน")
                            
                        e_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"file_{item_id_int}")
                        
                        col_e1, col_e2 = st.columns(2)
                        update_btn = col_e1.form_submit_button("บันทึกการแก้ไข", type="primary")
                        delete_btn = col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary")
                        
                        if update_btn:
                            img_base64 = current_item['image']
                            if e_file is not None:
                                img_bytes = e_file.read()
                                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                                
                            run_query("UPDATE items SET name=?, category=?, quantity=?, status=?, note=?, image=? WHERE id=?",
                                      (e_name, e_category, e_quantity, e_status, e_note, img_base64, item_id_int), is_select=False)
                            st.success("อัปเดตข้อมูลสำเร็จ!")
                            st.rerun()
                            
                        if delete_btn:
                            run_query("DELETE FROM items WHERE id=?", (item_id_int,), is_select=False)
                            st.success("ลบอุปกรณ์เรียบร้อยแล้ว!")
                            st.rerun()

    # 2. รายการตรวจเช็ค (รายวัน - เดือน - ปี)
    with admin_menu[1]:
        st.subheader("📊 รายการตรวจเช็คสภาพอุปกรณ์ (รายวัน - เดือน - ปี)")
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
                
            if not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            else:
                st.info("ไม่พบข้อมูลการตรวจเช็คในช่วงเวลาดังกล่าว")
        else:
            st.info("ยังไม่มีประวัติการตรวจเช็คจากช่างในระบบ")

    # 3. ตั้งค่ารหัส tech (ตามข้อ 2)
    with admin_menu[2]:
        st.subheader("⚙️ สร้างและแก้ไขรหัสผ่านช่างทั่วไป")
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("#### ➕ เพิ่มบัญชีช่างใหม่")
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
            st.markdown("#### ✏️ แก้ไข / ลบบัญชีช่าง")
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
                        btn_up_t = col_tu1.form_submit_button("บันทึกการแก้ไข")
                        btn_del_t = col_tu2.form_submit_button("ลบบัญชีนี้")
                        
                        if btn_up_t:
                            run_query("UPDATE tech_users SET username=?, password=? WHERE id=?", (edit_u, edit_p, t_id_int), is_select=False)
                            st.success("อัปเดตบัญชีช่างสำเร็จ!")
                            st.rerun()
                        if btn_del_t:
                            if len(tech_list_df) <= 1:
                                st.error("ต้องเหลือบัญชีช่างไว้อย่างน้อย 1 บัญชี")
                            else:
                                run_query("DELETE FROM tech_users WHERE id=?", (t_id_int,), is_select=False)
                                st.success("ลบบัญชีช่างเรียบร้อยแล้ว!")
                                st.rerun()

elif st.session_state.role == "ช่างทั่วไป":
    # ------------------ 4. จอสำหรับช่าง (Technician UI ปรับปรุงใหม่) ------------------
    st.subheader("📋 หน้าต่างปฏิบัติงานช่างทั่วไป")
    
    tech_category_choice = st.radio("เลือกหมวดหมู่การทำงาน", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
    st.markdown("---")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # หมวดที่ 1: อุปกรณ์ช่าง (ติ๊กชำรุดรายครั้ง สูงสุด 3 ครั้ง/วัน)
    if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
        st.markdown("### 🔧 หมวดอุปกรณ์ช่าง (เช็คความชำรุด)")
        st.write("คำชี้แจง: ทำเครื่องหมายติ๊กเลือกเฉพาะอุปกรณ์ที่ชำรุด (จำกัดตรวจสูงสุด 3 ครั้งต่อวัน)")
        
        today_inspections = run_query("SELECT COUNT(*) as cnt FROM inspections WHERE tech_name = ? AND category = 'อุปกรณ์ช่าง' AND inspection_date LIKE ?", 
                                      (st.session_state.username, f"{today_str}%"))
        check_count = int(today_inspections.iloc[0]['cnt']) if not today_inspections.empty else 0
        
        st.info(f"📌 วันนี้คุณทำการส่งตรวจหมวดอุปกรณ์ช่างไปแล้ว **{check_count}/3 ครั้ง**")
        
        if check_count >= 3:
            st.error("⚠️ คุณได้ทำการตรวจเช็คหมวดอุปกรณ์ช่างครบโควต้า 3 ครั้งสำหรับวันนี้แล้ว")
        else:
            tools_df = items_df[items_df['category'] == 'อุปกรณ์ช่าง']
            if not tools_df.empty:
                with st.form("tech_tools_form"):
                    tool_statuses = {}
                    for _, row in tools_df.iterrows():
                        is_broken_def = True if row['status'] == 'ชำรุด' else False
                        is_broken = st.checkbox(f"รหัส #{row['id']} - **{row['name']}** (คงเหลือ: {row['quantity']})", value=is_broken_def, key=f"t_item_{row['id']}")
                        tool_statuses[row['id']] = "ชำรุด" if is_broken else "ปกติ"
                        
                    if st.form_submit_button(f"ยืนยันส่งผลตรวจ (ครั้งที่ {check_count + 1})"):
                        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for item_id, st_val in tool_statuses.items():
                            run_query("UPDATE items SET status = ? WHERE id = ?", (st_val, item_id), is_select=False)
                            
                        summary_note = f"ตรวจครั้งที่ {check_count+1}: อัปเดตสถานะอุปกรณ์ช่าง"
                        run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details) VALUES (?,?,?,?,?)",
                                  (st.session_state.username, 'อุปกรณ์ช่าง', now_time, check_count+1, summary_note), is_select=False)
                        
                        st.success("บันทึกผลการตรวจสอบอุปกรณ์ช่างเรียบร้อยแล้ว!")
                        st.rerun()
            else:
                st.info("ไม่มีอุปกรณ์ช่างในระบบ")
                
    # หมวดที่ 2: อุปกรณ์สระว่ายน้ำ (ใส่จำนวนคงเหลือ และคลิกดูรูปภาพ)
    else:
        st.markdown("### 🏊 หมวดอุปกรณ์สระว่ายน้ำ (เช็คจำนวน & ดูรูปภาพ)")
        st.write("คลิกที่ชื่อรายการอุปกรณ์เพื่อดูรูปภาพ และปรับปรุงจำนวนคงเหลือ")
        
        pool_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ']
        if not pool_df.empty:
            with st.form("pool_inventory_form"):
                updated_quantities = {}
                
                for _, row in pool_df.iterrows():
                    # ใช้ Expander ให้คลิกดูชื่อและรูปภาพได้สะดวกบนมือถือ
                    with st.expander(f"📦 {row['name']} (คงเหลือปัจจุบัน: {row['quantity']} ชิ้น)"):
                        pil_img = get_pil_image_from_base64(row['image'])
                        if pil_img:
                            st.image(pil_img, width=220, caption=f"รูปภาพ: {row['name']}")
                        else:
                            st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
                            
                    new_qty = st.number_input(f"ระบุจำนวนคงเหลือของ: {row['name']}", min_value=0, value=int(row['quantity']), key=f"pool_q_{row['id']}")
                    updated_quantities[row['id']] = new_qty
                    st.markdown("---")
                    
                if st.form_submit_button("บันทึกจำนวนอุปกรณ์สระว่ายน้ำ"):
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for item_id, q_val in updated_quantities.items():
                        run_query("UPDATE items SET quantity = ? WHERE id = ?", (q_val, item_id), is_select=False)
                        
                    run_query("INSERT INTO inspections (tech_name, category, inspection_date, session_num, details) VALUES (?,?,?,?,?)",
                              (st.session_state.username, 'อุปกรณ์สระว่ายน้ำ', now_time, 1, "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ"), is_select=False)
                              
                    st.success("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ไม่มีอุปกรณ์สระว่ายน้ำในระบบ")
