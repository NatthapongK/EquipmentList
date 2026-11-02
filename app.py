import streamlit as st
import pymongo
import pymongo.operations
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re
import io
import secrets
from PIL import Image, ImageOps
from streamlit_local_storage import LocalStorage

# =====================================================================
#  ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ (ฉบับอัปเดต UI 2026 ทันสมัย)
# =====================================================================

# --- TIMEZONE CONFIG (Thailand UTC+7) ---
TZ_TH = timezone(timedelta(hours=7))

def get_now_th():
    return datetime.now(TZ_TH)

def get_now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return get_now_th().strftime(fmt)

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ", page_icon="🛠️", layout="wide")

ROLE_ADMIN = "ผู้ออกแบบ/ดูแลระบบ"
ROLE_TECH = "ช่างประจำอาคาร"
ROLE_TECH_SP = "ช่างประจำอาคารพิเศษ"
TECH_ROLES = [ROLE_TECH, ROLE_TECH_SP]

# รายการอุปกรณ์เริ่มต้นทั้งหมด
DEFAULT_INITIAL_ITEMS = [
    ("ปลั๊กโรลElecton", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("สว่านแบตMakita", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 2, "ปกติ", "-", None),
    ("บันได3ขั้น", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
    ("เครื่องตรวจเช็กเต้ารับไฟฟ้า", "อุปกรณ์ช่าง", "เครื่องมือช่าง", 1, "ปกติ", "-", None),
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
    ("สายดูดตะกอน สั้น+ยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
]

def build_default_docs():
    return [{
        "id": idx, "name": i[0], "category": i[1], "subcategory": i[2],
        "quantity": i[3], "status": i[4], "alert_zero": 0, "note": i[5], "image": i[6]
    } for idx, i in enumerate(DEFAULT_INITIAL_ITEMS, start=1)]

@st.cache_resource
def init_mongo():
    try:
        uri = st.secrets["mongo"]["uri"]
    except Exception:
        st.error("❌ ไม่พบ st.secrets['mongo']['uri'] กรุณาตั้งค่าใน .streamlit/secrets.toml")
        st.stop()
    client = pymongo.MongoClient(uri, maxPoolSize=20, serverSelectionTimeoutMS=8000)
    database = client["inventory_pro"]

    database.items.create_index("id", unique=True)
    database.transactions.create_index("id")
    database.inspections.create_index("id")
    database.requisition_requests.create_index("id")
    database.tech_users.create_index("username")
    database.settings.create_index("key")
    database.sessions.create_index("token", unique=True)
    database.sessions.create_index("created", expireAfterSeconds=60 * 60 * 24 * 30)

    if database.items.count_documents({}, limit=1) == 0:
        database.items.insert_many(build_default_docs())
        database.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
    database.settings.update_one({"key": "low_stock_threshold"}, {"$setOnInsert": {"value": "1"}}, upsert=True)
    database.settings.update_one({"key": "global_daily_quota"}, {"$setOnInsert": {"value": "3"}}, upsert=True)
    return database

db = init_mongo()

def get_next_sequence(name):
    counter = db.counters.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
    return counter["seq"]

def compress_image_to_base64(uploaded_file, max_size=(800, 800), quality=80):
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img.draft("RGB", (max_size[0] * 2, max_size[1] * 2))
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.BILINEAR)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        uploaded_file.seek(0)
        return base64.b64encode(uploaded_file.read()).decode("utf-8")

def b64_to_bytes(img_base64):
    if not img_base64:
        return None
    try:
        return base64.b64decode(img_base64)
    except Exception:
        return None

@st.cache_resource(ttl=600, show_spinner=False)
def get_image_store():
    store = {}
    for d in db.items.find({"image": {"$nin": [None, ""]}}, {"_id": 0, "id": 1, "image": 1}):
        b = b64_to_bytes(d.get("image"))
        if b:
            store[int(d["id"])] = b
    return store

def get_item_image(item_id):
    return get_image_store().get(int(item_id))

@st.cache_data(ttl=30, show_spinner=False)
def get_items_df():
    df = pd.DataFrame(list(db.items.find({}, {"_id": 0, "image": 0})))
    if not df.empty:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        df['alert_zero'] = pd.to_numeric(df.get('alert_zero', 0), errors='coerce').fillna(0).astype(int)
        df['note'] = df['note'].fillna("") if 'note' in df.columns else ""
    return df

@st.cache_data(ttl=60, show_spinner=False)
def get_tech_users_df():
    return pd.DataFrame(list(db.tech_users.find({}, {"_id": 0})))

@st.cache_data(ttl=30, show_spinner=False)
def get_settings_val(key, default="1"):
    res = db.settings.find_one({"key": key})
    return res["value"] if res else default

def set_settings_val(key, val):
    db.settings.update_one({"key": key}, {"$set": {"value": str(val)}}, upsert=True)
    get_settings_val.clear()

@st.cache_data(ttl=15, show_spinner=False)
def get_active_borrows():
    return list(db.transactions.find({"status": "กำลังยืม"}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_pending_reqs():
    return list(db.requisition_requests.find({"status": "รออนุมัติ"}, {"_id": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_inspection_count(category, today_str):
    return db.inspections.count_documents({"category": category, "inspection_date": {"$regex": f"^{today_str}"}})

@st.cache_data(ttl=30, show_spinner=False)
def get_tx_history(limit=300):
    return list(db.transactions.find({}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1).limit(limit))

@st.cache_data(ttl=600, max_entries=300, show_spinner=False)
def get_tx_image(tx_id):
    d = db.transactions.find_one({"id": tx_id}, {"_id": 0, "borrower_image": 1})
    return b64_to_bytes(d.get("borrower_image")) if d else None

@st.cache_data(ttl=30, show_spinner=False)
def get_inspections_list(limit=1000):
    return list(db.inspections.find({}, {"_id": 0, "photos": 0}).sort("id", -1).limit(limit))

@st.cache_data(ttl=600, max_entries=100, show_spinner=False)
def get_inspection_photos(insp_id):
    doc = db.inspections.find_one({"id": insp_id}, {"_id": 0, "photos": 1})
    raw = doc.get("photos") if doc else None
    if not raw or not str(raw).strip():
        return []
    return [b for b in (b64_to_bytes(p) for p in str(raw).split("|||")) if b]

@st.cache_data(ttl=30, show_spinner=False)
def get_req_history(limit=300):
    return list(db.requisition_requests.find({"status": {"$ne": "รออนุมัติ"}}, {"_id": 0}).sort("id", -1).limit(limit))

@st.cache_data(ttl=30, show_spinner=False)
def get_my_reqs(username):
    return list(db.requisition_requests.find({"tech_name": username}, {"_id": 0}).sort("id", -1).limit(200))

def clear_tx_cache():
    get_active_borrows.clear()
    get_tx_history.clear()

def clear_req_cache():
    get_pending_reqs.clear()
    get_req_history.clear()
    get_my_reqs.clear()

def refresh_items(images=False):
    get_items_df.clear()
    if images:
        get_image_store.clear()

def done(msg, icon="✅"):
    st.session_state["_flash"] = (msg, icon)
    st.rerun()

def close_quick_edit():
    st.session_state.pop("quick_edit_id", None)
    st.session_state.items_tbl_ver = st.session_state.get("items_tbl_ver", 0) + 1

def nz(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)

def parse_tech_txt_content(text_content):
    tech_list = []
    u = None
    p = None
    for line in text_content.splitlines():
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

fragment = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None) or (lambda f: f)

def switch_role(new_role):
    st.session_state.role = new_role
    st.session_state.original_role = ROLE_ADMIN
    tk = st.session_state.get("token")
    if tk:
        db.sessions.update_one({"token": tk}, {"$set": {"role": new_role}})
    st.rerun()

# --- THEME & CSS ---
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
.stDeployButton {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important; visibility: hidden !important; opacity: 0 !important;}

.block-container{padding-top:1.5rem; padding-bottom:3rem; max-width:1200px;}
h2, h3, h4{color:var(--ink); font-weight:600; letter-spacing:0;}

.app-hero{background:#111827; color:#fff; border-radius:14px; padding:1rem 1.25rem; border:1px solid var(--line);
  display:flex; justify-content:space-between; align-items:center; gap:.75rem 1rem; flex-wrap:wrap; margin-bottom:1rem;}
.app-hero .t{font-size:1.3rem; font-weight:700; line-height:1.3; color:#F8FAFC;}
.app-hero .s{font-size:.85rem; color:#94A3B8; margin-top:.15rem;}
.chip{display:inline-block; padding:.2rem .7rem; border-radius:999px; font-size:.8rem; font-weight:600;
  background:var(--teal); color:#fff;}

.kpi-grid{display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; margin-bottom:1rem;}
.kpi{background:var(--card); border:1px solid var(--line); border-left:4px solid var(--c,var(--teal));
  border-radius:10px; padding:.7rem .9rem;}
.kpi .n{font-size:1.7rem; font-weight:700; line-height:1.15; color:#F8FAFC;}
.kpi .l{font-size:.82rem; color:var(--muted);}

section[data-testid="stSidebar"]{background:#111827; border-right:1px solid var(--line);}
.user-card{display:flex; align-items:center; gap:.7rem; padding:.7rem; border:1px solid var(--line);
  border-radius:12px; background:var(--card);}
.avatar{width:2.4rem; height:2.4rem; border-radius:50%; background:var(--teal); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; flex:none;}
.u-name{font-weight:600; line-height:1.2; word-break:break-all; color:#F8FAFC;}
.u-role{font-size:.8rem; color:var(--muted);}

.stTabs [data-baseweb="tab-list"]{gap:.2rem; border-bottom:1px solid var(--line); overflow-x:auto; flex-wrap:nowrap;}
.stTabs [data-baseweb="tab"]{height:auto; padding:.6rem .9rem; font-weight:500; color:var(--muted); white-space:nowrap;}
.stTabs [aria-selected="true"]{color:#38BDF8; font-weight:600;}
.stTabs [data-baseweb="tab-highlight"]{background:#38BDF8; height:3px;}

[data-testid="stExpander"]{border:1px solid var(--line); border-radius:10px; background:var(--card);}
[data-testid="stForm"]{border:1px solid var(--line); border-radius:12px; background:var(--card); padding:1rem;}

[data-testid="stDataFrame"], .stTable {
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow-x: auto !important;
  -webkit-overflow-scrolling: touch;
}

.stApp button{border-radius:8px; font-weight:600;}
.stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--teal); border-color:var(--teal); color:#fff;}
.stApp button[kind="primary"]:hover, .stApp button[data-testid="stBaseButton-primary"]:hover,
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:var(--teal-d); border-color:var(--teal-d);}

.req-banner{display:flex; align-items:center; gap:.9rem; padding:.9rem 1.1rem; margin-bottom:1rem;
  border-radius:12px; border:2px solid var(--warn); background:linear-gradient(90deg,#78350F,#92400E);
  animation:reqpulse 1.8s ease-in-out infinite;}
.req-banner .ic{font-size:1.9rem; line-height:1;}
.req-banner .t{font-size:1.1rem; font-weight:700; color:#FEF3C7;}
.req-banner .s{font-size:.85rem; color:#FDE68A; margin-top:.1rem;}
@keyframes reqpulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.55);} 50%{box-shadow:0 0 0 8px rgba(245,158,11,0);}}
</style>
""", unsafe_allow_html=True)

# --- LOGIN STATE & SESSION RESTORATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.session_state.token = None

if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0

LS_KEY = "inv_token"
local_store = LocalStorage()
try:
    saved_token = local_store.getItem(LS_KEY)
except Exception:
    saved_token = None

if not st.session_state.logged_in:
    cand_token = st.query_params.get("token") or saved_token
    if cand_token:
        sess = db.sessions.find_one({"token": cand_token})
        if sess and sess.get("role") and sess.get("role") not in ["None", "null", ""]:
            db.sessions.update_one({"token": cand_token}, {"$set": {"created": datetime.now(timezone.utc)}})
            st.session_state.logged_in = True
            st.session_state.role = sess["role"]
            st.session_state.username = sess["username"]
            st.session_state.original_role = sess.get("original_role")
            st.session_state.token = sess["token"]
            st.query_params["token"] = sess["token"]
        else:
            st.query_params.clear()
            if saved_token:
                try:
                    local_store.deleteItem(LS_KEY, key="ls_del_token")
                except:
                    pass

_flash = st.session_state.pop("_flash", None)
if _flash:
    st.toast(_flash[0], icon=_flash[1])

if st.session_state.get("token") and saved_token != st.session_state.token:
    try:
        local_store.setItem(LS_KEY, st.session_state.token, key="ls_set_token")
    except:
        pass

# --- SIDEBAR & LOGOUT FIX ---
if st.session_state.role in TECH_ROLES:
    st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)
else:
    st.sidebar.markdown(
        f'<div class="user-card"><div class="avatar">{esc(st.session_state.username[:1].upper() if st.session_state.username else "U")}</div>'
        f'<div><div class="u-name">{esc(st.session_state.username)}</div>'
        f'<div class="u-role">สิทธิ์: {esc(st.session_state.role)}</div></div></div>',
        unsafe_allow_html=True)
    st.sidebar.markdown("")

    with st.sidebar.expander("👤 เมนูบัญชีผู้ใช้ & ออกจากระบบ", expanded=True):
        st.write(f"ผู้ใช้งาน: **{st.session_state.username}**")
        st.write(f"สิทธิ์: **{st.session_state.role}**")

        if st.session_state.original_role == ROLE_ADMIN:
            st.markdown("---")
            if st.session_state.role == ROLE_ADMIN:
                if st.button("🔀 สลับเป็น 'ช่างประจำอาคารพิเศษ'", type="secondary", use_container_width=True):
                    switch_role(ROLE_TECH_SP)
            else:
                if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True):
                    switch_role(ROLE_ADMIN)

        st.markdown("---")
        if st.button("🚪 ออกจากระบบ (Logout)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
            if st.session_state.get("token"):
                db.sessions.delete_one({"token": st.session_state.token})
            try:
                local_store.deleteItem(LS_KEY, key="ls_del_token")
            except:
                pass
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            st.session_state.original_role = None
            st.session_state.token = None
            st.query_params.clear()
            st.rerun()

# --- LOGIN FORM IF NOT LOGGED IN OR ROLE IS NONE ---
if not st.session_state.logged_in or not st.session_state.role or st.session_state.role == "None":
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
        
        tech_df = get_tech_users_df()
        
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
                role_val = ROLE_ADMIN
                user_val = admin_user
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)] if not tech_df.empty else pd.DataFrame()
                if not matched_tech.empty:
                    role_val = ROLE_TECH
                    user_val = username
            
            if role_val:
                orig_role = role_val if role_val == ROLE_ADMIN else None
                token = secrets.token_urlsafe(24)
                db.sessions.insert_one({
                    "token": token, "username": user_val, "role": role_val,
                    "original_role": orig_role, "created": datetime.now(timezone.utc)
                })
                
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                st.session_state.original_role = orig_role
                st.session_state.token = token
                
                st.query_params["token"] = token
                try:
                    local_store.setItem(LS_KEY, token, key="ls_set_token")
                except:
                    pass
                
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# --- HEADER (ถ้า Login ผ่านแล้ว) ---
if st.session_state.role in TECH_ROLES:
    st.markdown(
        f'<div class="app-hero"><div><div class="t">🛠️ ระบบเช็คสถานะอุปกรณ์</div>'
        f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {get_now_str("%d/%m/%Y")}</div></div>'
        f'<span class="chip">{esc(st.session_state.username)} ({esc(st.session_state.role)})</span></div>',
        unsafe_allow_html=True)
else:
    col_h_title, col_h_btn = st.columns([4, 1])
    with col_h_title:
        st.markdown(
            f'<div class="app-hero" style="margin-bottom:0.5rem;"><div><div class="t">🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์</div>'
            f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {get_now_str("%d/%m/%Y")}</div></div>'
            f'<span class="chip">{esc(st.session_state.role)}</span></div>',
            unsafe_allow_html=True)
    with col_h_btn:
        if st.button("🔄 โหลดข้อมูลใหม่", type="secondary", use_container_width=True):
            st.cache_data.clear()
            get_image_store.clear()
            st.rerun()

# --- ALERT SYSTEM & DATA FETCH ---
low_stock_limit = int(get_settings_val('low_stock_threshold', '1'))
items_df = get_items_df()

if not items_df.empty:
    item_name_map = dict(zip(items_df['id'], items_df['name']))
else:
    item_name_map = {}

is_tech_view = st.session_state.role in TECH_ROLES
abn_statuses = ['ชำรุด', 'อุปกรณ์หมด'] if is_tech_view else ['ชำรุด', 'สูญหาย', 'ยืม', 'อุปกรณ์หมด']
abn_label = "ชำรุด / กำลังใช้งาน / หมด" if is_tech_view else "ผิดปกติ / กำลังใช้งาน / หมด / ยืม"
abn_title = "อุปกรณ์ชำรุด/กำลังใช้งาน/หมด" if is_tech_view else "อุปกรณ์ผิดปกติ/กำลังใช้งาน/หมด/ถูกยืม"

if not items_df.empty:
    abnormal_items = items_df[
        items_df['status'].isin(abn_statuses) |
        items_df['status'].str.startswith('กำลังใช้งาน', na=False) |
        items_df['status'].str.contains('กำลังใช้งาน', na=False)
    ]
    thr = pd.Series(low_stock_limit, index=items_df.index).where(items_df['alert_zero'] != 1, 0)
    low_stock_items = items_df[(items_df['subcategory'] != 'เครื่องมือช่าง') & (items_df['quantity'] <= thr)]
else:
    abnormal_items = pd.DataFrame()
    low_stock_items = pd.DataFrame()

active_borrows = get_active_borrows()
borrowed_cnt = len(active_borrows)
abn_cnt, low_cnt = len(abnormal_items), len(low_stock_items)

def _pending_req_banner():
    pending = get_pending_reqs()
    if not pending:
        return
    st.markdown(
        f'<div class="req-banner"><div class="ic">📥</div><div>'
        f'<div class="t">มีคำขอเบิกของรออนุมัติ {len(pending)} รายการ</div>'
        f'<div class="s">ไปที่แท็บ "3. อนุมัติคำขอเพิ่มอุปกรณ์" เพื่อพิจารณาอนุมัติ/ปฏิเสธ</div></div></div>',
        unsafe_allow_html=True)
    with st.expander(f"📥 รายการคำขอเบิกของที่รออนุมัติ ({len(pending)} รายการ)", expanded=True):
        st.dataframe(pd.DataFrame([{
            "รหัสคำขอ": r["id"], "ผู้ขอ": r.get("tech_name"),
            "อุปกรณ์": item_name_map.get(r["item_id"], "Unknown"),
            "จำนวนที่ขอ": r.get("quantity"), "เหตุผล": r.get("note"), "วันที่ขอ": r.get("request_date"),
        } for r in pending]), hide_index=True, use_container_width=True)

if st.session_state.role == ROLE_ADMIN:
    try:
        st.fragment(run_every="30s")(_pending_req_banner)()
    except TypeError:
        _pending_req_banner()

st.markdown(
    f'''<div class="kpi-grid">
      <div class="kpi"><div class="n">{len(items_df)}</div><div class="l">รายการอุปกรณ์ทั้งหมด</div></div>
      <div class="kpi" style="--c:{'var(--bad)' if abn_cnt else 'var(--ok)'}"><div class="n">{abn_cnt}</div><div class="l">{abn_label}</div></div>
      <div class="kpi" style="--c:{'var(--warn)' if