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

# =====================================================================
#  ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ  (เวอร์ชันปรับความเร็ว)
#  ต้องใช้ Streamlit >= 1.37 (รองรับ st.fragment)
#  ต้องตั้งค่า .streamlit/secrets.toml:
#     [mongo]
#     uri = "mongodb+srv://..."
#     [admin]
#     username = "..."
#     password = "..."
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
    ("สายดูดตะกอน สั้น+ยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
]

def build_default_docs():
    """สร้างเอกสารอุปกรณ์เริ่มต้นพร้อม id ลำดับ 1..N (ใช้ insert_many ครั้งเดียว)"""
    return [{
        "id": idx, "name": i[0], "category": i[1], "subcategory": i[2],
        "quantity": i[3], "status": i[4], "alert_zero": 0, "note": i[5], "image": i[6]
    } for idx, i in enumerate(DEFAULT_INITIAL_ITEMS, start=1)]

# --- MONGODB CONNECTION (รันครั้งเดียวต่อ process: สร้าง index + seed ข้อมูล) ---
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
    database.transactions.create_index([("status", 1), ("id", -1)])
    database.inspections.create_index("id")
    database.inspections.create_index([("category", 1), ("inspection_date", 1)])
    database.requisition_requests.create_index("id")
    database.requisition_requests.create_index([("status", 1), ("id", -1)])
    database.requisition_requests.create_index("tech_name")
    database.tech_users.create_index("username")
    database.settings.create_index("key")
    database.sessions.create_index("token", unique=True)
    database.sessions.create_index("created", expireAfterSeconds=60 * 60 * 24 * 30)  # session หมดอายุ 30 วัน

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

# --- IMAGE HELPERS ---
def compress_image_to_base64(uploaded_file, max_size=(800, 800), quality=80):
    """บีบอัดรูป -> base64 (เรียกเฉพาะตอนกดบันทึกเท่านั้น ห้ามเรียกทุก rerun)"""
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

# --- CACHED DATA FUNCTIONS ---
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

# [NEW] แคชข้อมูลที่เคย query ใหม่ทุก rerun (ทุกแท็บถูกรันพร้อมกันเสมอ)
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

# [NEW] แจ้งผลสำเร็จแบบ toast ที่ยังแสดงหลัง rerun
def done(msg, icon="✅"):
    st.session_state["_flash"] = (msg, icon)
    st.rerun()

# [NEW] ปิดหน้าต่างแก้ไขด่วน + รีเซ็ตการเลือกแถว (กันหน้าต่างเด้งกลับมา)
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

# --- SESSION TOKEN ---
def create_session(username, role, original_role):
    token = secrets.token_urlsafe(24)
    db.sessions.insert_one({
        "token": token, "username": username, "role": role,
        "original_role": original_role, "created": datetime.now(timezone.utc)
    })
    return token

def switch_role(new_role):
    st.session_state.role = new_role
    st.session_state.original_role = ROLE_ADMIN
    tk = st.session_state.get("token")
    if tk:
        db.sessions.update_one({"token": tk}, {"$set": {"role": new_role}})
    st.rerun()

# --- THEME & RESPONSIVE MOBILE CSS ---
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

.st-key-tech_check_list [data-testid="stHorizontalBlock"],
.st-key-pool_check_list [data-testid="stHorizontalBlock"]{
  flex-direction:row !important; flex-wrap:nowrap !important; align-items:flex-start !important; gap:.4rem !important;
}
.st-key-tech_check_list [data-testid="stColumn"],
.st-key-pool_check_list [data-testid="stColumn"]{min-width:0 !important;}
.st-key-tech_check_list [data-testid="stColumn"]:first-child,
.st-key-pool_check_list [data-testid="stColumn"]:first-child{flex:1 1 0 !important; width:auto !important;}
.st-key-tech_check_list [data-testid="stColumn"]:last-child{flex:0 0 auto !important; width:auto !important; min-width:6.5rem !important;}
.st-key-pool_check_list [data-testid="stColumn"]:last-child{flex:0 0 8rem !important; width:8rem !important;}
.st-key-tech_check_list [data-testid="stCheckbox"]{padding-top:.55rem;}

@media (max-width:768px){
  .block-container{padding-left:.6rem; padding-right:.6rem;}
  .kpi-grid{grid-template-columns:repeat(2,1fr);}
  .app-hero .t{font-size:1.1rem;}
  .stApp .stButton > button, .stApp [data-testid="stFormSubmitButton"] > button{width:100%;}
  .stTabs [data-baseweb="tab"]{padding:.5rem .6rem; font-size:0.85rem;}
}
</style>
""", unsafe_allow_html=True)

# --- LOGIN STATE MANAGEMENT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.session_state.token = None

if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0

if not st.session_state.logged_in and "token" in st.query_params:
    sess = db.sessions.find_one({"token": st.query_params["token"]})
    if sess:
        st.session_state.logged_in = True
        st.session_state.role = sess["role"]
        st.session_state.username = sess["username"]
        st.session_state.original_role = sess.get("original_role")
        st.session_state.token = sess["token"]
    else:
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

        if submitted:
            role_val, user_val = "", ""
            try:
                admin_user = st.secrets["admin"]["username"]
                admin_pass = st.secrets["admin"]["password"]
            except Exception:
                admin_user, admin_pass = "admin", "admin"

            if username == admin_user and password == admin_pass:
                role_val, user_val = ROLE_ADMIN, admin_user
            elif db.tech_users.find_one({"username": username, "password": password}, {"_id": 1}):
                role_val, user_val = ROLE_TECH, username

            if role_val:
                orig_role = ROLE_ADMIN if role_val == ROLE_ADMIN else None
                token = create_session(user_val, role_val, orig_role)
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                st.session_state.original_role = orig_role
                st.session_state.token = token
                st.query_params["token"] = token
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# [NEW] แสดง toast ที่ค้างไว้จากการบันทึกครั้งก่อน
_flash = st.session_state.pop("_flash", None)
if _flash:
    st.toast(_flash[0], icon=_flash[1])

# --- SIDEBAR ---
if st.session_state.role in TECH_ROLES:
    st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)
else:
    st.sidebar.markdown(
        f'<div class="user-card"><div class="avatar">{esc(st.session_state.username[:1].upper())}</div>'
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
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            st.session_state.original_role = None
            st.session_state.token = None
            st.query_params.clear()
            st.rerun()

# --- HEADER ---
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
        items_df['status'].str.startswith('กำลังใช้งาน', na=False)
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
      <div class="kpi" style="--c:{'var(--warn)' if low_cnt else 'var(--ok)'}"><div class="n">{low_cnt}</div><div class="l">เหลือน้อยกว่าเกณฑ์</div></div>
      <div class="kpi" style="--c:var(--teal)"><div class="n">{borrowed_cnt}</div><div class="l">กำลังถูกยืมอยู่</div></div>
    </div>''', unsafe_allow_html=True)

col_a1, col_a2 = st.columns(2)
with col_a1:
    if abn_cnt:
        with st.expander(f"❌ {abn_title} ({abn_cnt} รายการ)"):
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

if borrowed_cnt:
    with st.expander(f"📤 อุปกรณ์ที่กำลังถูกยืม ({borrowed_cnt} รายการ)"):
        st.dataframe(pd.DataFrame([{
            "อุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
            "จำนวนที่ยืม": t.get("quantity", 1),
            "ผู้ยืม": t.get("borrower_name"),
            "ผู้ให้ยืม": t.get("giver_name"),
            "วันที่ยืม": t.get("borrow_date"),
        } for t in active_borrows]), hide_index=True, use_container_width=True)
else:
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
st.markdown("")

# --- SHARED BORROW / RETURN COMPONENT ---
def render_borrow_return_system():
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])

    with sub_borrow:
        available_items = items_df[items_df['quantity'] > 0] if not items_df.empty else pd.DataFrame()
        if not available_items.empty:
            with st.form("borrow_form_shared", clear_on_submit=True):
                item_dict = {f"#{row['id']} {row['name']} (คงเหลือ: {row['quantity']} ชิ้น) [{row['category']}]": row['id']
                             for _, row in available_items.iterrows()}
                sel_item_label = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(item_dict.keys()))
                borrow_qty = st.number_input("จำนวนที่ต้องการยืม *", min_value=1,
                                             max_value=int(available_items['quantity'].max()), value=1)
                borrower_name = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                borrow_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายผู้ยืมหรือหลักฐานการยืม (ถ้ามี)", type=["jpg", "jpeg", "png"])
                st.info(f"📌 ผู้ทำรายการ/ผู้ให้ยืม: **{st.session_state.username}** (บันทึกอัตโนมัติ)")

                if st.form_submit_button("ยืนยันการยืมอุปกรณ์"):
                    selected_id = item_dict[sel_item_label]
                    cur = db.items.find_one({"id": selected_id}, {"_id": 0, "quantity": 1, "status": 1, "name": 1})
                    if not borrower_name.strip():
                        st.error("❌ กรุณากรอกชื่อผู้ยืมให้เรียบร้อย")
                    elif not cur or int(cur["quantity"]) < borrow_qty:
                        st.error(f"❌ จำนวนคงเหลือไม่พอ (คงเหลือ {cur['quantity'] if cur else 0} ชิ้น)")
                    else:
                        b_img_b64 = compress_image_to_base64(borrow_img_file)
                        tx_id = get_next_sequence("transactions_id")
                        db.transactions.insert_one({
                            "id": tx_id, "item_id": selected_id, "borrower_name": borrower_name,
                            "borrow_date": get_now_str("%Y-%m-%d %H:%M"), "return_date": None,
                            "status": "กำลังยืม", "borrower_image": b_img_b64, "quantity": borrow_qty,
                            "giver_name": st.session_state.username, "receiver_name": None, "return_image": None
                        })
                        new_qty = int(cur["quantity"]) - borrow_qty
                        new_status = 'ยืม' if new_qty == 0 else cur["status"]
                        db.items.update_one({"id": selected_id}, {"$set": {"quantity": new_qty, "status": new_status}})
                        refresh_items()
                        clear_tx_cache()
                        done(f"บันทึกการยืม {cur['name']} จำนวน {borrow_qty} ชิ้น เรียบร้อยแล้ว")
        else:
            st.info("ไม่มีอุปกรณ์ที่มีจำนวนคงเหลือให้ยืมในขณะนี้")

    with sub_return:
        st.markdown("#### รายการที่กำลังถูกยืมอยู่")
        active_txs = get_active_borrows()   # ใช้แคช ไม่ดึงรูปทั้งหมดทุก rerun

        if active_txs:
            for t in active_txs:
                item_name = item_name_map.get(t["item_id"], "Unknown")
                giver_str = f" | ผู้ให้ยืม: {t.get('giver_name')}" if t.get('giver_name') else ""
                with st.expander(f"📦 อุปกรณ์: {item_name} (จำนวนยืม: {t.get('quantity', 1)} ชิ้น) | ผู้ยืม: {t.get('borrower_name')}{giver_str}"):
                    col_r1, col_r2 = st.columns([1, 2])
                    with col_r1:
                        p_img = get_tx_image(t['id'])   # ดึงรูปทีละรายการ + แคช
                        if p_img:
                            st.image(p_img, caption=f"ผู้ยืม: {t.get('borrower_name')}", width=200)
                        else:
                            st.write("*(ไม่มีรูปถ่าย)*")
                    with col_r2:
                        st.write(f"**ชื่ออุปกรณ์:** {item_name}")
                        st.write(f"**จำนวนที่ยืม:** {t.get('quantity', 1)} ชิ้น")
                        st.write(f"**ผู้ยืม:** {t.get('borrower_name')}")
                        if t.get('giver_name'):
                            st.write(f"**ผู้ให้ยืม/บันทึก:** {t.get('giver_name')}")
                        st.write(f"**วันที่ยืม:** {t.get('borrow_date')}")

                        with st.form(key=f"return_form_{t['id']}"):
                            st.info(f"📌 ผู้รับคืน: **{st.session_state.username}** (บันทึกอัตโนมัติ)")
                            ret_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายตอนคืนอุปกรณ์ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"ret_img_{t['id']}")

                            if st.form_submit_button("✅ รับคืนอุปกรณ์รายการนี้"):
                                r_img_b64 = compress_image_to_base64(ret_img_file)
                                db.transactions.update_one(
                                    {"id": t['id']},
                                    {"$set": {"return_date": get_now_str("%Y-%m-%d %H:%M"), "status": "คืนแล้ว",
                                              "receiver_name": st.session_state.username, "return_image": r_img_b64}})
                                tx_qty = int(t.get('quantity', 1))
                                db.items.update_one({"id": t['item_id']}, {"$inc": {"quantity": tx_qty}, "$set": {"status": "ปกติ"}})
                                refresh_items()
                                clear_tx_cache()
                                done(f"รับคืน {item_name} จำนวน {tx_qty} ชิ้น เรียบร้อยแล้ว")
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืมในขณะนี้")

    with sub_history:
        st.markdown("#### ประวัติการยืม-คืนทั้งหมด (แสดง 300 รายการล่าสุด)")
        all_txs = get_tx_history()
        tx_history = pd.DataFrame([{
            "รหัส": t["id"],
            "ชื่ออุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
            "จำนวน": t.get("quantity", 1),
            "ผู้ยืม": t.get("borrower_name"),
            "ผู้ให้ยืม": t.get("giver_name"),
            "ผู้รับคืน": t.get("receiver_name"),
            "วันที่ยืม": t.get("borrow_date"),
            "วันที่คืน": t.get("return_date"),
            "สถานะ": t.get("status"),
        } for t in all_txs])
        st.dataframe(tx_history, use_container_width=True, hide_index=True)

# --- ลิสต์ตรวจเช็คอุปกรณ์ช่าง (fragment) ---
@fragment
def render_tool_inspection_list(tools_all_df):
    tech_search = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
    tools_df = tools_all_df
    if tech_search.strip():
        tools_df = tools_df[tools_df['name'].str.contains(tech_search.strip(), case=False, na=False)]

    with keyed_container("tech_check_list", height=500):
        for _, row in tools_df.iterrows():
            rid = row['id']
            current_status = row['status']
            is_currently_flagged = current_status != "ปกติ"

            col_item, col_flag = st.columns([5, 1.4])
            with col_item:
                status_badge = f" (สถานะเดิม: {current_status})" if is_currently_flagged else ""
                with st.expander(f"🛠️ {row['name']}{status_badge} (คงเหลือ: {row['quantity']})"):
                    img_bytes = get_item_image(rid)
                    if img_bytes:
                        st.image(img_bytes, width=220, caption=f"รูปภาพ: {row['name']}")
                    else:
                        st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
            with col_flag:
                is_flagged = st.checkbox("แจ้งปัญหา", value=is_currently_flagged, key=f"flag_{rid}")

            if is_flagged:
                options_list = ["-- เลือกประเภท --", "กำลังใช้งาน", "อุปกรณ์หมด", "ชำรุด", "สูญหาย"]
                if row['subcategory'] == "เครื่องมือช่าง":
                    options_list.remove("อุปกรณ์หมด")
                default_idx = 0
                detail_default = ""
                if current_status.startswith("กำลังใช้งาน"):
                    default_idx = 1
                    m_detail = re.search(r'\((.*?)\)', current_status)
                    if m_detail:
                        detail_default = m_detail.group(1)
                elif current_status in options_list:
                    default_idx = options_list.index(current_status)

                issue_type = st.selectbox("ประเภทปัญหา *", options_list, index=default_idx, key=f"issue_type_{rid}")
                item_total_q = int(row['quantity'])

                if issue_type == "กำลังใช้งาน":
                    st.text_input("ระบุรายละเอียดการใช้งาน *", value=detail_default, key=f"issue_detail_{rid}")
                    if item_total_q > 1:
                        st.number_input("จำนวนชิ้นที่นำไปใช้งาน *", min_value=1, max_value=item_total_q, value=1, key=f"issue_qty_{rid}")
                elif issue_type in ["ชำรุด", "สูญหาย"]:
                    if item_total_q > 1:
                        st.number_input(f"จำนวนชิ้นที่{issue_type} *", min_value=1, max_value=item_total_q, value=1, key=f"issue_qty_{rid}")
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

# --- ลิสต์จำนวนอุปกรณ์สระว่ายน้ำ (fragment) ---
@fragment
def render_pool_list(pool_all_df):
    tech_pool_search = st.text_input("🔍 ค้นหาอุปกรณ์สระว่ายน้ำ...", key="tech_pool_search_box")
    pool_df = pool_all_df
    if tech_pool_search.strip():
        pool_df = pool_df[pool_df['name'].str.contains(tech_pool_search.strip(), case=False, na=False)]

    with keyed_container("pool_check_list", height=500):
        for _, row in pool_df.iterrows():
            col_item, col_qty = st.columns([5, 1.6])
            with col_item:
                with st.expander(f"📦 {row['name']}"):
                    img_bytes = get_item_image(row['id'])
                    if img_bytes:
                        st.image(img_bytes, width=220, caption=f"รูปภาพ: {row['name']}")
                    else:
                        st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
            with col_qty:
                st.number_input(f"จำนวนคงเหลือ: {row['name']}", min_value=0, value=int(row['quantity']),
                                key=f"pool_q_{row['id']}", label_visibility="collapsed")
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

def clear_inspection_widget_state():
    prefixes = ("flag_", "issue_type_", "issue_detail_", "issue_qty_", "pool_q_")
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(prefixes):
            del st.session_state[k]

# --- DIVISION BY ROLE ---
if st.session_state.role == ROLE_ADMIN:
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
            if not filtered_df.empty:
                if search_kw.strip():
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_kw.strip(), case=False, na=False)]
                if cat_filter != "ทั้งหมด":
                    filtered_df = filtered_df[filtered_df['category'] == cat_filter]
                if status_filter != "ทั้งหมด":
                    filtered_df = filtered_df[filtered_df['status'] == status_filter]

            st.caption(f"แสดงรายการอุปกรณ์ทั้งหมด {len(filtered_df)} จาก {len(items_df)} รายการ (💡 คลิกเลือกแถวในตารางด้านล่าง เพื่อเปิดหน้าต่างแก้ไขข้อมูลทันที)")

            cols_show = ['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note']
            show_df = filtered_df[cols_show].copy() if not filtered_df.empty else pd.DataFrame(columns=cols_show)
            if not show_df.empty:
                show_df['alert_zero'] = show_df['alert_zero'].astype(bool)

            table_event = st.dataframe(
                show_df, use_container_width=True, hide_index=True, height=350,
                on_select="rerun", selection_mode="single-row",
                key=f"items_tbl_{st.session_state.get('items_tbl_ver', 0)}",
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
            if selected_rows and selected_rows[0] < len(filtered_df):
                st.session_state.quick_edit_id = int(filtered_df.iloc[selected_rows[0]]['id'])

            if st.session_state.get("quick_edit_id"):
                qe_id = st.session_state.quick_edit_id
                qe_row = db.items.find_one({"id": qe_id}, {"_id": 0, "image": 0})
                if qe_row:
                    st.markdown("---")
                    with st.expander(f"📌 หน้าต่างแก้ไขข้อมูลอุปกรณ์: #{qe_row['id']} - {qe_row['name']}", expanded=True):
                        with st.form(f"quick_edit_form_{qe_id}"):
                            qe_name = st.text_input("ชื่ออุปกรณ์", value=qe_row['name'])
                            qe_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if qe_row['category'] == "อุปกรณ์ช่าง" else 1)

                            if qe_category == "อุปกรณ์ช่าง":
                                sub_idx = 0 if qe_row.get('subcategory') == "เครื่องมือช่าง" else 1
                                qe_subcat = st.selectbox("หมวดหมู่ย่อย", ["เครื่องมือช่าง", "อุปกรณ์ช่างทั่วไป"], index=sub_idx)
                            else:
                                qe_subcat = "เคมีภัณฑ์"
                                st.info("📌 หมวดหมู่ย่อยถูกกำหนดเป็น: **เคมีภัณฑ์** โดยอัตโนมัติ")

                            qe_quantity = st.number_input("จำนวน", min_value=0, value=int(qe_row['quantity']))
                            status_list = ["ปกติ", "ชำรุด", "สูญหาย", "ยืม", "อุปกรณ์หมด"]
                            qe_status = st.selectbox("สถานะ", status_list, index=status_list.index(qe_row['status']) if qe_row['status'] in status_list else 0)
                            qe_alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0", value=bool(qe_row.get('alert_zero', 0)))
                            qe_note = st.text_area("หมายเหตุ", value=nz(qe_row.get('note')))

                            cur_img = get_item_image(qe_id)
                            if cur_img:
                                st.image(cur_img, width=150, caption="รูปภาพปัจจุบัน")
                            qe_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"qe_file_{qe_id}")

                            col_qe1, col_qe2, col_qe3 = st.columns([1, 1, 2])
                            if col_qe1.form_submit_button("💾 บันทึกการแก้ไข", type="primary"):
                                upd = {"name": qe_name, "category": qe_category, "subcategory": qe_subcat,
                                       "quantity": qe_quantity, "status": qe_status,
                                       "alert_zero": 1 if qe_alert_zero else 0, "note": qe_note}
                                if qe_file is not None:
                                    upd["image"] = compress_image_to_base64(qe_file)
                                db.items.update_one({"id": qe_id}, {"$set": upd})
                                refresh_items(images=qe_file is not None)
                                close_quick_edit()
                                done("อัปเดตข้อมูลสำเร็จ!")
                            if col_qe2.form_submit_button("🗑️ ลบอุปกรณ์นี้", type="secondary"):
                                db.items.delete_one({"id": qe_id})
                                refresh_items(images=True)
                                close_quick_edit()
                                done("ลบเรียบร้อยแล้ว!")
                            if col_qe3.form_submit_button("❌ ปิดหน้าต่าง"):
                                close_quick_edit()
                                st.rerun()

        with tab_add_edit:
            sub_a, sub_e, sub_bulk = st.tabs(["➕ เพิ่มอุปกรณ์ใหม่", "✏️ แก้ไข/ลบ รายการ", "🖼️ อัปโหลดรูปภาพแบบกลุ่ม"])
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
                            new_id = get_next_sequence("items_id")
                            db.items.insert_one({
                                "id": new_id, "name": name, "category": category, "subcategory": subcategory,
                                "quantity": quantity, "status": status, "alert_zero": 1 if alert_zero else 0,
                                "note": note, "image": compress_image_to_base64(uploaded_file)
                            })
                            refresh_items(images=uploaded_file is not None)
                            done("เพิ่มอุปกรณ์สำเร็จ!")
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
                            e_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if current_item['category'] == "อุปกรณ์ช่าง" else 1)

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
                            e_note = st.text_area("หมายเหตุ", value=nz(current_item['note']))

                            cur_img = get_item_image(item_id_int)
                            if cur_img:
                                st.image(cur_img, width=150, caption="รูปภาพปัจจุบัน")
                            e_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"file_{item_id_int}")

                            col_e1, col_e2 = st.columns(2)
                            if col_e1.form_submit_button("บันทึกการแก้ไข", type="primary"):
                                upd = {"name": e_name, "category": e_category, "subcategory": e_subcat,
                                       "quantity": e_quantity, "status": e_status,
                                       "alert_zero": 1 if e_alert_zero else 0, "note": e_note}
                                if e_file is not None:
                                    upd["image"] = compress_image_to_base64(e_file)
                                db.items.update_one({"id": item_id_int}, {"$set": upd})
                                refresh_items(images=e_file is not None)
                                done("อัปเดตข้อมูลสำเร็จ!")
                            if col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary"):
                                db.items.delete_one({"id": item_id_int})
                                refresh_items(images=True)
                                done("ลบเรียบร้อยแล้ว!")

            with sub_bulk:
                st.markdown("### 📁 อัปโหลดรูปภาพอุปกรณ์แบบกลุ่ม (ตามชื่อไฟล์รหัสอุปกรณ์)")
                st.write("ตั้งชื่อไฟล์รูปภาพตามรหัสอุปกรณ์ เช่น `1.jpg` สำหรับ ปลั๊กโรลElecton, `2.png` สำหรับ สว่านแบตMakita ฯลฯ แล้วเลือกไฟล์ทั้งหมดพร้อมกันได้เลย")

                bulk_files = st.file_uploader("เลือกไฟล์รูปภาพทั้งหมด", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="bulk_img_files")
                if bulk_files:
                    st.info(f"เลือกไฟล์ทั้งหมด: **{len(bulk_files)} รูป**")
                    if st.button("🚀 ยืนยันจับคู่และอัปโหลดรูปภาพเข้าระบบ", type="primary"):
                        valid_ids = set(items_df['id'].tolist()) if not items_df.empty else set()
                        ops = []
                        with st.spinner("กำลังบีบอัดและอัปโหลดรูปภาพ..."):
                            for img_f in bulk_files:
                                pure_name = img_f.name.rsplit('.', 1)[0]
                                if pure_name.isdigit() and int(pure_name) in valid_ids:
                                    ops.append(pymongo.operations.UpdateOne(
                                        {"id": int(pure_name)}, {"$set": {"image": compress_image_to_base64(img_f)}}))
                            if ops:
                                db.items.bulk_write(ops, ordered=False)
                        refresh_items(images=True)
                        done(f"อัปเดตรูปภาพตามชื่อไฟล์สำเร็จทั้งหมด {len(ops)} รายการ!")

        with tab_excel_import:
            st.markdown("### ⚡ โหลดชุดข้อมูลตั้งต้นทั้งหมด (ลำดับใหม่)")
            st.write("การคลิกปุ่มนี้จะล้างข้อมูลเดิมและโหลดรายการพร้อมลำดับใหม่ทั้งหมด")
            if st.button("🚀 รีเซ็ตและโหลดอุปกรณ์ทั้งหมดตามรายการใหม่", type="primary"):
                db.items.delete_many({})
                db.items.insert_many(build_default_docs())
                db.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
                refresh_items(images=True)
                done("นำเข้าอุปกรณ์และลำดับใหม่สำเร็จ!")

    with admin_menu[1]:
        st.subheader("📊 รายการตรวจเช็คสภาพอุปกรณ์")
        report_type = st.radio("เลือกมุมมองรายงาน", ["รายวัน (Daily)", "รายเดือน (Monthly)", "รายปี (Yearly)", "ประวัติทั้งหมด"], horizontal=True)
        inspections_df = pd.DataFrame(get_inspections_list())

        if not inspections_df.empty:
            inspections_df['inspection_date'] = pd.to_datetime(inspections_df['inspection_date'])
            now_dt = get_now_th()
            if report_type == "รายวัน (Daily)":
                target_date = st.date_input("เลือกวันที่", value=now_dt.date())
                filtered_insp = inspections_df[inspections_df['inspection_date'].dt.date == target_date]
            elif report_type == "รายเดือน (Monthly)":
                col_m1, col_m2 = st.columns(2)
                selected_month = col_m1.selectbox("เดือน", list(range(1, 13)), index=now_dt.month - 1)
                selected_year = col_m2.number_input("ปี (ค.ศ.)", value=now_dt.year)
                filtered_insp = inspections_df[(inspections_df['inspection_date'].dt.month == selected_month) & (inspections_df['inspection_date'].dt.year == selected_year)]
            elif report_type == "รายปี (Yearly)":
                selected_year = st.number_input("ปี ค.ศ.", value=now_dt.year)
                filtered_insp = inspections_df[inspections_df['inspection_date'].dt.year == selected_year]
            else:
                filtered_insp = inspections_df

            st.dataframe(
                filtered_insp[['id', 'tech_name', 'category', 'inspection_date', 'session_num', 'details']],
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
            st.caption("แสดงสูงสุด 30 รายการล่าสุดของตัวกรองนี้ · ติ๊ก 'โหลดรูปถ่าย' เพื่อดึงรูปเฉพาะรายการที่ต้องการ")
            for _, row in filtered_insp.head(30).iterrows():
                date_str_show = row['inspection_date'].strftime("%Y-%m-%d %H:%M:%S")
                with st.expander(f"📌 {date_str_show} | ผู้ตรวจ: {row['tech_name']} | หมวด: {row['category']} (รอบที่ {row['session_num']})"):
                    st.write(f"📝 **รายละเอียดการตรวจ:** {row['details']}")
                    if st.checkbox("🖼️ โหลดรูปถ่าย", key=f"load_photos_{row['id']}"):
                        photo_imgs = get_inspection_photos(int(row['id']))
                        if photo_imgs:
                            st.write(f"จำนวนรูปถ่ายทั้งหมด: **{len(photo_imgs)} รูป**")
                            cols_p = st.columns(min(len(photo_imgs), 4))
                            for idx, p_img in enumerate(photo_imgs):
                                cols_p[idx % 4].image(p_img, caption=f"รูปที่ {idx + 1}", use_container_width=True)
                        else:
                            st.info("*(การตรวจเช็ครอบนี้ไม่ได้อัปโหลดรูปถ่ายรวม)*")
        else:
            st.info("ยังไม่มีประวัติการตรวจเช็คจากช่างในระบบ")

    with admin_menu[2]:
        st.subheader("📥 จัดการคำขอเพิ่มอุปกรณ์เข้าคลัง")
        sub_req_pending, sub_req_history = st.tabs(["📥 คำขอที่รออนุมัติ", "📜 ประวัติการอนุมัติคำขอ"])

        with sub_req_pending:
            pending_reqs = get_pending_reqs()
            current_qty_map = dict(zip(items_df['id'], items_df['quantity'])) if not items_df.empty else {}

            if pending_reqs:
                for req in pending_reqs:
                    item_name = item_name_map.get(req["item_id"], "Unknown")
                    current_stock = current_qty_map.get(req["item_id"], 0)

                    with st.container():
                        st.write(f"🆔 **รหัสคำขอ:** #{req['id']} | 👤 **ผู้ขอเพิ่ม:** {req['tech_name']} | 📅 **วันที่ขอ:** {req['request_date']}")
                        st.write(f"📦 **อุปกรณ์:** {item_name} | **จำนวนที่ขอเพิ่ม:** +{req['quantity']} ชิ้น (คงเหลือในคลังปัจจุบัน: {current_stock})")
                        st.write(f"📝 **หมายเหตุ/เหตุผล:** {req['note']}")

                        col_app1, col_app2 = st.columns(2)
                        if col_app1.button("✅ อนุมัติ (เพิ่มจำนวนเข้าคลัง)", key=f"approve_{req['id']}"):
                            # กันกดซ้ำ: อัปเดตเฉพาะคำขอที่ยังรออนุมัติอยู่จริง
                            res = db.requisition_requests.update_one(
                                {"id": req['id'], "status": "รออนุมัติ"},
                                {"$set": {"status": "อนุมัติ", "approval_date": get_now_str()}})
                            if res.modified_count:
                                db.items.update_one({"id": req['item_id']}, {"$inc": {"quantity": int(req['quantity'])}, "$set": {"status": "ปกติ"}})
                            refresh_items()
                            clear_req_cache()
                            done(f"อนุมัติคำขอ #{req['id']} เรียบร้อยแล้ว")

                        if col_app2.button("❌ ไม่อนุมัติ", key=f"reject_{req['id']}"):
                            db.requisition_requests.update_one({"id": req['id'], "status": "รออนุมัติ"}, {"$set": {"status": "ไม่อนุมัติ", "approval_date": get_now_str()}})
                            clear_req_cache()
                            done(f"ปฏิเสธคำขอ #{req['id']} เรียบร้อยแล้ว", icon="⚠️")
                        st.markdown("---")
            else:
                st.info("ไม่มีคำขอเพิ่มอุปกรณ์ที่รอการอนุมัติในขณะนี้")

        with sub_req_history:
            st.markdown("#### 📜 ประวัติการอนุมัติคำขอเพิ่มอุปกรณ์")
            req_history_list = get_req_history()
            req_history_df = pd.DataFrame([{
                "รหัส": r["id"], "ผู้ขอ": r.get("tech_name"),
                "ชื่ออุปกรณ์": item_name_map.get(r["item_id"], "Unknown"),
                "จำนวนที่ขอ": r.get("quantity"), "หมายเหตุ": r.get("note"),
                "วันที่ขอ": r.get("request_date"), "วันที่อนุมัติ": r.get("approval_date"),
                "สถานะ": r.get("status")
            } for r in req_history_list])
            if not req_history_df.empty:
                st.dataframe(req_history_df, use_container_width=True, hide_index=True)
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
                set_settings_val('low_stock_threshold', new_threshold)
                done("บันทึกค่าการแจ้งเตือนสำเร็จ!")

        st.markdown("---")
        st.markdown("#### 🔄 ตั้งค่าและเพิ่มโควต้าการตรวจเช็คประจำวัน (นับรวมทุกคน)")
        current_base_quota = int(get_settings_val('global_daily_quota', '3'))

        with st.form("global_quota_form"):
            new_base_quota = st.number_input("กำหนดโควต้ารอบตรวจมาตรฐานต่อวัน (รอบ)", min_value=1, value=current_base_quota)
            reset_date = st.date_input("เลือกวันที่ต้องการเพิ่มรอบตรวจพิเศษ", value=get_now_th().date())
            date_str = reset_date.strftime("%Y-%m-%d")
            current_extra = int(get_settings_val(f"extra_quota_{date_str}", '0'))
            add_more_quota = st.number_input("ระบุจำนวนรอบที่ต้องการเพิ่มให้ตรวจอีกสำหรับวันนี้ (รอบพิเศษ)", min_value=0, value=current_extra)

            if st.form_submit_button("บันทึกการตั้งค่าโควต้า"):
                set_settings_val('global_daily_quota', new_base_quota)
                set_settings_val(f"extra_quota_{date_str}", add_more_quota)
                done("บันทึกการตั้งค่าโควต้าเรียบร้อยแล้ว!")

        st.markdown("---")
        st.markdown("#### 🛠️ จัดการบัญชีช่าง (สร้าง / แก้ไข / นำเข้าจากไฟล์ .txt / ลบ)")
        st.markdown("**📋 รายชื่อบัญชีช่างทั้งหมดในระบบ**")
        all_techs_df = get_tech_users_df()
        if not all_techs_df.empty:
            st.dataframe(all_techs_df[['id', 'username']].rename(columns={'id': 'รหัส', 'username': 'ชื่อผู้ใช้งาน (Username)'}), use_container_width=True, hide_index=True)
        st.markdown("---")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**➕ เพิ่มบัญชีช่างใหม่ (รายบุคคล)**")
            with st.form("add_tech_form", clear_on_submit=True):
                new_t_user = st.text_input("Username ช่าง")
                new_t_pass = st.text_input("Password ช่าง", type="password")
                if st.form_submit_button("สร้างบัญชีช่าง"):
                    if new_t_user.strip() and new_t_pass.strip():
                        if not db.tech_users.find_one({"username": new_t_user}, {"_id": 1}):
                            t_id = get_next_sequence("tech_users_id")
                            db.tech_users.insert_one({"id": t_id, "username": new_t_user, "password": new_t_pass})
                            get_tech_users_df.clear()
                            done(f"สร้างบัญชีช่าง '{new_t_user}' สำเร็จ!")
                        else:
                            st.error("Username นี้มีอยู่ในระบบแล้ว")
                    else:
                        st.error("กรุณากรอกข้อมูลให้ครบถ้วน")

            st.markdown("---")
            st.markdown("**✏️ แก้ไข / ลบบัญชีช่างรายบุคคล**")
            tech_list_df = get_tech_users_df()
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
                            db.tech_users.update_one({"id": t_id_int}, {"$set": {"username": edit_u, "password": edit_p}})
                            get_tech_users_df.clear()
                            done("อัปเดตบัญชีช่างสำเร็จ!")
                        if col_tu2.form_submit_button("ลบบัญชีนี้"):
                            if db.tech_users.count_documents({}) <= 1:
                                st.error("ต้องเหลือบัญชีช่างไว้อย่างน้อย 1 บัญชี")
                            else:
                                db.tech_users.delete_one({"id": t_id_int})
                                get_tech_users_df.clear()
                                done("ลบบัญชีช่างเรียบร้อยแล้ว!")

        with col_t2:
            st.markdown("**📁 นำเข้ารายชื่อช่างจากไฟล์ .txt**")
            st.write("อัปโหลดไฟล์ `.txt` ที่มีรูปแบบ `username = \"...\"` และ `password = \"...\"` เช่นไฟล์ `tech.txt`")
            uploaded_tech_txt = st.file_uploader("เลือกไฟล์รายชื่อช่าง (.txt)", type=["txt"])

            if uploaded_tech_txt is not None:
                content_str = uploaded_tech_txt.getvalue().decode("utf-8")
                parsed_techs = parse_tech_txt_content(content_str)
                st.info(f"ตรวจพบข้อมูลช่างในไฟล์จำนวน: **{len(parsed_techs)} บัญชี**")

                if parsed_techs:
                    preview_df = pd.DataFrame(parsed_techs, columns=["Username", "Password"])
                    preview_df["Password"] = "••••••••"
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                    if st.button("🚀 ยืนยันนำเข้าบัญชีช่างทั้งหมดลงฐานข้อมูล", type="primary"):
                        existing_users = {d["username"] for d in db.tech_users.find({}, {"username": 1, "_id": 0})}
                        success_count, dup_count = 0, 0
                        for u, p in parsed_techs:
                            if u in existing_users:
                                dup_count += 1
                            else:
                                db.tech_users.insert_one({"id": get_next_sequence("tech_users_id"), "username": u, "password": p})
                                existing_users.add(u)
                                success_count += 1
                        get_tech_users_df.clear()
                        done(f"นำเข้าสำเร็จ! เพิ่มใหม่ {success_count} บัญชี (ซ้ำ/มีอยู่แล้ว {dup_count} บัญชี)")

elif st.session_state.role in TECH_ROLES:
    if st.session_state.role == ROLE_TECH_SP:
        col_banner, col_btn_back = st.columns([3, 1])
        with col_banner:
            st.info("⭐ คุณเข้าใช้งานในสถานะ **ช่างประจำอาคารพิเศษ** (สิทธิ์พิเศษจากแอดมิน)")
        with col_btn_back:
            if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True, key="banner_switch_back"):
                switch_role(ROLE_ADMIN)

    tech_main_tab = st.tabs(["📋 ตรวจสอบอุปกรณ์", "📦 เบิกของ", "🔄 ระบบยืม-คืน อุปกรณ์"])

    with tech_main_tab[2]:
        render_borrow_return_system()

    with tech_main_tab[1]:
        st.markdown("### 📦 เบิกของ (อุปกรณ์ช่างทั่วไป & อุปกรณ์สระว่ายน้ำ)")
        st.write("ค้นหาและเลือกอุปกรณ์ช่างทั่วไป หรืออุปกรณ์สระว่ายน้ำที่ต้องการเพิ่มจำนวนเข้าคลัง ระบบจะส่งคำขอไปยังผู้ออกแบบ/ดูแลระบบเพื่อรออนุมัติบวกสต็อก")

        tools_requisition_df = items_df[
            ((items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['subcategory'] == 'อุปกรณ์ช่างทั่วไป')) |
            (items_df['category'] == 'อุปกรณ์สระว่ายน้ำ')
        ] if not items_df.empty else pd.DataFrame()

        req_search_keyword = st.text_input("🔍 ค้นหาชื่ออุปกรณ์...", placeholder="พิมพ์ชื่ออุปกรณ์เพื่อค้นหา", key="req_general_search")
        if not tools_requisition_df.empty and req_search_keyword.strip():
            tools_requisition_df = tools_requisition_df[tools_requisition_df['name'].str.contains(req_search_keyword.strip(), case=False, na=False)]

        if not tools_requisition_df.empty:
            with st.form("requisition_request_form", clear_on_submit=True):
                req_item_dict = {f"#{row['id']} {row['name']} [{row['category']}] (คงเหลือในคลัง: {row['quantity']} ชิ้น)": row['id']
                                 for _, row in tools_requisition_df.iterrows()}
                sel_req_label = st.selectbox("เลือกอุปกรณ์ที่ต้องการเพิ่มจำนวน *", list(req_item_dict.keys()))
                req_qty = st.number_input("จำนวนที่ต้องการเพิ่มเข้าคลัง *", min_value=1, value=1)
                req_note = st.text_area("หมายเหตุ / เหตุผลที่ขอเพิ่ม *")

                if st.form_submit_button("📤 ส่งคำขอเบิกของ (รอผู้ออกแบบ/ดูแลระบบอนุมัติ)"):
                    if req_note.strip():
                        req_selected_id = req_item_dict[sel_req_label]
                        db.requisition_requests.insert_one({
                            "id": get_next_sequence("requisition_requests_id"),
                            "tech_name": st.session_state.username, "item_id": req_selected_id,
                            "quantity": req_qty, "note": req_note, "status": "รออนุมัติ",
                            "request_date": get_now_str("%Y-%m-%d %H:%M"), "approval_date": None
                        })
                        clear_req_cache()
                        done(f"ส่งคำขอเบิกของ '{item_name_map.get(req_selected_id, '')}' จำนวน +{req_qty} ชิ้น เรียบร้อยแล้ว!")
                    else:
                        st.error("กรุณาระบุหมายเหตุหรือเหตุผลที่ขอเบิกของ")
        else:
            st.info("ไม่พบรายการอุปกรณ์ตามค้นหา")

        st.markdown("---")
        st.markdown("#### 📜 ประวัติคำขอเบิกของของคุณ")
        my_reqs_list = get_my_reqs(st.session_state.username)
        my_requests = pd.DataFrame([{
            "รหัส": r["id"], "ชื่ออุปกรณ์": item_name_map.get(r["item_id"], "Unknown"),
            "จำนวนที่ขอ": r.get("quantity"), "หมายเหตุ": r.get("note"),
            "วันที่ขอ": r.get("request_date"), "วันที่อนุมัติ": r.get("approval_date"),
            "สถานะ": r.get("status")
        } for r in my_reqs_list])
        if not my_requests.empty:
            st.dataframe(my_requests, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการส่งคำขอเบิกของ")

    with tech_main_tab[0]:
        tech_category_choice = st.radio("เลือกหมวดหมู่การทำงาน", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
        st.markdown("---")
        today_str = get_now_str("%Y-%m-%d")

        if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
            st.markdown("### 🔧 หมวดอุปกรณ์ช่าง")

            global_count = get_inspection_count("อุปกรณ์ช่าง", today_str)
            base_quota = int(get_settings_val('global_daily_quota', '3'))
            extra_quota = int(get_settings_val(f"extra_quota_{today_str}", '0'))
            total_allowed = base_quota + extra_quota

            if global_count >= total_allowed:
                st.error("⚠️ ครบโควตารอบการตรวจสำหรับวันนี้แล้ว (กรุณาติดต่อผู้ออกแบบ/ดูแลระบบเพื่อเพิ่มรอบตรวจพิเศษ)")
            else:
                tools_all_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['quantity'] > 0)] if not items_df.empty else pd.DataFrame()

                if not tools_all_df.empty:
                    render_tool_inspection_list(tools_all_df)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 📸 รูปถ่ายอุปกรณ์ที่ตรวจเช็ค")

                    photo_files = []
                    tool_photo_labels = ["รูปถ่ายแผงไม้เครื่องมือ", "รูปถ่ายชั้นเครื่องมือชั้นบน",
                                         "รูปถ่ายชั้นเครื่องมือชั้นกลาง", "รูปถ่ายชั้นเครื่องมือชั้นล่าง"]
                    for i in range(4):
                        up_file = st.file_uploader(tool_photo_labels[i], type=["jpg", "jpeg", "png"],
                                                   key=f"tech_p_{i}_{st.session_state.uploader_version}")
                        if up_file is not None:
                            photo_files.append(up_file)

                    st.progress(len(photo_files) / 4, text=f"📸 แนบรูปแล้ว {len(photo_files)}/4 รูป")
                    if st.button(f"💾 ยืนยันส่งผลตรวจ (รอบที่ {global_count + 1})", type="primary", use_container_width=True):
                        item_reports = {}
                        for _, row in tools_all_df.iterrows():
                            rid = row['id']
                            if f"flag_{rid}" not in st.session_state:
                                continue
                            item_reports[rid] = {
                                "flagged": bool(st.session_state.get(f"flag_{rid}")),
                                "status": st.session_state.get(f"issue_type_{rid}", "ปกติ"),
                                "detail": st.session_state.get(f"issue_detail_{rid}", "") or "",
                                "qty": int(st.session_state.get(f"issue_qty_{rid}", 1) or 1),
                            }

                        error_msg = ""
                        for data in item_reports.values():
                            if data["flagged"]:
                                if data["status"] in ("-- เลือกประเภท --", "ปกติ"):
                                    error_msg = "❌ กรุณาเลือกประเภทปัญหาให้ครบถ้วนสำหรับรายการที่ติ๊ก"
                                    break
                                if data["status"] == "กำลังใช้งาน" and not data["detail"].strip():
                                    error_msg = "❌ กรุณากรอกรายละเอียดการใช้งานสำหรับรายการที่เลือก 'กำลังใช้งาน'"
                                    break
                        if not error_msg and len(photo_files) < 4:
                            error_msg = "❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานให้ครบทั้ง 4 รูป จึงจะสามารถยืนยันผลตรวจได้"

                        if error_msg:
                            st.error(error_msg)
                        else:
                            with st.spinner("กำลังบันทึกผลการตรวจ..."):
                                photos_b64 = [compress_image_to_base64(f, max_size=(1000, 1000), quality=70) for f in photo_files]
                                flagged_summaries = []
                                bulk_operations = []
                                row_map = tools_all_df.set_index('id')

                                for item_id, data in item_reports.items():
                                    curr_q = int(row_map.loc[item_id, 'quantity'])
                                    item_name = row_map.loc[item_id, 'name']

                                    if data["flagged"]:
                                        final_st = data["status"]
                                        if data["status"] == "กำลังใช้งาน" and data["detail"].strip():
                                            final_st = f"กำลังใช้งาน ({data['detail']})"
                                        if data["status"] == "อุปกรณ์หมด":
                                            new_q = 0
                                        else:
                                            new_q = max(0, curr_q - data["qty"])
                                        bulk_operations.append(pymongo.operations.UpdateOne(
                                            {"id": item_id}, {"$set": {"status": final_st, "quantity": new_q}}))
                                        detail_txt = f"{item_name}: {data['status']}" + (f" ({data['detail']})" if data['detail'] else "") + (f" [{data['status']} {data['qty']} ชิ้น]" if data['qty'] > 1 and data['status'] != "อุปกรณ์หมด" else "")
                                        flagged_summaries.append(detail_txt)
                                    else:
                                        bulk_operations.append(pymongo.operations.UpdateOne({"id": item_id}, {"$set": {"status": "ปกติ"}}))

                                if bulk_operations:
                                    db.items.bulk_write(bulk_operations, ordered=False)

                                summary_details = ", ".join(flagged_summaries) if flagged_summaries else "ปกติทุกรายการ"
                                db.inspections.insert_one({
                                    "id": get_next_sequence("inspections_id"),
                                    "tech_name": st.session_state.username,
                                    "category": "อุปกรณ์ช่าง",
                                    "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"),
                                    "session_num": global_count + 1,
                                    "details": f"รอบที่ {global_count + 1} | รายการผิดปกติ: {summary_details}",
                                    "photos": "|||".join(photos_b64)
                                })

                            refresh_items()
                            get_inspection_count.clear()
                            get_inspections_list.clear()
                            clear_inspection_widget_state()
                            st.session_state.uploader_version += 1
                            done("บันทึกผลการตรวจสอบเรียบร้อยแล้ว!")
                else:
                    st.info("ไม่มีอุปกรณ์ช่างให้ตรวจสอบในขณะนี้")

        else:
            st.markdown("### 🏊 หมวดอุปกรณ์สระว่ายน้ำ")

            pool_all_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ'] if not items_df.empty else pd.DataFrame()
            if not pool_all_df.empty:
                render_pool_list(pool_all_df)

                st.markdown("### 📸 รูปถ่ายอุปกรณ์ที่ตรวจเช็ค")
                pool_photo_files = []
                for i in range(4):
                    up_file = st.file_uploader(f"รูปถ่ายอุปกรณ์ที่ {i+1}", type=["jpg", "jpeg", "png"],
                                               key=f"tech_pool_p_{i}_{st.session_state.uploader_version}")
                    if up_file is not None:
                        pool_photo_files.append(up_file)

                st.progress(len(pool_photo_files) / 4, text=f"📸 แนบรูปแล้ว {len(pool_photo_files)}/4 รูป")
                if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                    if len(pool_photo_files) < 4:
                        st.error("❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานสระว่ายน้ำให้ครบทั้ง 4 รูป")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูล..."):
                            photos_b64 = [compress_image_to_base64(f, max_size=(1000, 1000), quality=70) for f in pool_photo_files]
                            pool_summaries = []
                            bulk_pool_ops = []
                            row_map = pool_all_df.set_index('id')

                            for item_id in pool_all_df['id']:
                                key = f"pool_q_{item_id}"
                                if key not in st.session_state:
                                    continue
                                q_val = int(st.session_state[key])
                                old_q = int(row_map.loc[item_id, 'quantity'])
                                if q_val != old_q:
                                    bulk_pool_ops.append(pymongo.operations.UpdateOne({"id": item_id}, {"$set": {"quantity": q_val}}))
                                    pool_summaries.append(f"{row_map.loc[item_id, 'name']}: ปรับจาก {old_q} เหลือ {q_val}")

                            if bulk_pool_ops:
                                db.items.bulk_write(bulk_pool_ops, ordered=False)

                            summary_note = "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ" + (f" | การเปลี่ยนแปลง: {', '.join(pool_summaries)}" if pool_summaries else "")
                            db.inspections.insert_one({
                                "id": get_next_sequence("inspections_id"),
                                "tech_name": st.session_state.username,
                                "category": "อุปกรณ์สระว่ายน้ำ",
                                "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"),
                                "session_num": 1,
                                "details": summary_note,
                                "photos": "|||".join(photos_b64)
                            })

                        refresh_items()
                        get_inspection_count.clear()
                        get_inspections_list.clear()
                        clear_inspection_widget_state()
                        st.session_state.uploader_version += 1
                        done("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")
            else:
                st.info("ไม่มีอุปกรณ์สระว่ายน้ำในระบบ")