import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re
import io
from PIL import Image

# --- TIMEZONE CONFIG (Thailand UTC+7) ---
TZ_TH = timezone(timedelta(hours=7))

def get_now_th():
    return datetime.now(TZ_TH)

def get_now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return get_now_th().strftime(fmt)

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ", page_icon="🛠️", layout="wide")

# --- MONGODB ATLAS CONNECTION ---
MONGO_URI = "mongodb+srv://mrnatthapongk_db_user:MyPassword123@equipmentlist627.44qcj3k.mongodb.net/?retryWrites=true&w=majority"

@st.cache_resource
def init_mongo():
    client = pymongo.MongoClient(MONGO_URI)
    db = client["inventory_pro"]
    return db

db = init_mongo()

# Helper สำหรับ Auto-increment ID แบบจำลองคอลเลกชัน SQL
def get_next_sequence(name):
    counter = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return counter["seq"]

# --- OPTIMIZED IMAGE COMPRESSION HELPER ---
def compress_image_to_base64(uploaded_file, max_size=(800, 800), quality=80):
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        uploaded_file.seek(0)
        return base64.b64encode(uploaded_file.read()).decode("utf-8")

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

# --- INITIALIZE MONGODB DEFAULT DATA ---
def init_db():
    if db.items.count_documents({}) == 0:
        for i in DEFAULT_INITIAL_ITEMS:
            new_id = get_next_sequence("items_id")
            db.items.insert_one({
                "id": new_id,
                "name": i[0],
                "category": i[1],
                "subcategory": i[2],
                "quantity": i[3],
                "status": i[4],
                "alert_zero": 0,
                "note": i[5],
                "image": i[6]
            })
    
    if db.settings.count_documents({"key": "low_stock_threshold"}) == 0:
        db.settings.insert_one({"key": "low_stock_threshold", "value": "1"})
    if db.settings.count_documents({"key": "global_daily_quota"}) == 0:
        db.settings.insert_one({"key": "global_daily_quota", "value": "3"})

init_db()

# --- OPTIMIZED CACHED DATA FUNCTIONS (TTL ลดเหลือ 0 เพื่อดึงข้อมูลสดทันที) ---
@st.cache_data(ttl=0, show_spinner=False)
def get_items_df():
    df = pd.DataFrame(list(db.items.find({}, {"_id": 0})))
    if not df.empty:
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        if 'alert_zero' in df.columns:
            df['alert_zero'] = pd.to_numeric(df['alert_zero'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data(ttl=0, show_spinner=False)
def get_tech_users_df():
    return pd.DataFrame(list(db.tech_users.find({}, {"_id": 0})))

@st.cache_data(ttl=0, show_spinner=False)
def get_settings_val(key, default="1"):
    res = db.settings.find_one({"key": key})
    return res["value"] if res else default

def set_settings_val(key, val):
    db.settings.update_one({"key": key}, {"$set": {"value": str(val)}}, upsert=True)
    st.cache_data.clear()

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
    except:
        return None

# --- PERSISTENT LOGIN FRONTEND BRIDGE (LOCALSTORAGE) ---
st.markdown("""
<script>
window.addEventListener('DOMContentLoaded', () => {
    const savedUser = localStorage.getItem('inv_username');
    const savedRole = localStorage.getItem('inv_role');
    const currentParams = new URLSearchParams(window.location.search);
    
    if (savedUser && savedRole && !currentParams.has('logged_in')) {
        currentParams.set('logged_in', 'true');
        currentParams.set('username', savedUser);
        currentParams.set('role', savedRole);
        window.location.replace(window.location.pathname + '?' + currentParams.toString());
    }
});
</script>
""", unsafe_allow_html=True)

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

qp = st.query_params
if not st.session_state.logged_in and "logged_in" in qp and qp["logged_in"] == "true":
    try:
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
                role_val = "ผู้ออกแบบ/ดูแลระบบ"
                user_val = admin_user
            else:
                matched_tech = tech_df[(tech_df['username'] == username) & (tech_df['password'] == password)] if not tech_df.empty else pd.DataFrame()
                if not matched_tech.empty:
                    role_val = "ช่างประจำอาคาร"
                    user_val = username
            
            if role_val:
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                orig_role = role_val if role_val == "ผู้ออกแบบ/ดูแลระบบ" else ""
                st.session_state.original_role = orig_role if orig_role else None
                
                st.query_params["logged_in"] = "true"
                st.query_params["role"] = role_val
                st.query_params["username"] = user_val
                if orig_role:
                    st.query_params["original_role"] = orig_role
                
                st.markdown(f"""
                <script>
                localStorage.setItem('inv_username', '{user_val}');
                localStorage.setItem('inv_role', '{role_val}');
                </script>
                """, unsafe_allow_html=True)
                
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# --- DYNAMIC SIDEBAR CONTROL BY ROLE ---
if st.session_state.role in ["ช่างประจำอาคาร", "ช่างประจำอาคารพิเศษ"]:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
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
        
        is_admin_origin = (st.session_state.get("original_role") == "ผู้ออกแบบ/ดูแลระบบ") or (st.query_params.get("original_role") == "ผู้ออกแบบ/ดูแลระบบ") or (st.session_state.role == "ผู้ออกแบบ/ดูแลระบบ")
        
        if is_admin_origin:
            st.markdown("---")
            if st.session_state.role == "ผู้ออกแบบ/ดูแลระบบ":
                if st.button("🔀 สลับเป็น 'ช่างประจำอาคารพิเศษ'", type="secondary", use_container_width=True):
                    st.session_state.role = "ช่างประจำอาคารพิเศษ"
                    st.session_state.original_role = "ผู้ออกแบบ/ดูแลระบบ"
                    st.query_params["role"] = "ช่างประจำอาคารพิเศษ"
                    st.query_params["original_role"] = "ผู้ออกแบบ/ดูแลระบบ"
                    st.rerun()
            else:
                if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True):
                    st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                    st.session_state.original_role = "ผู้ออกแบบ/ดูแลระบบ"
                    st.query_params["role"] = "ผู้ออกแบบ/ดูแลระบบ"
                    st.query_params["original_role"] = "ผู้ออกแบบ/ดูแลระบบ"
                    st.rerun()
        
        st.markdown("---")
        if st.button("🚪 ออกจากระบบ (Logout)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
            st.markdown("""
            <script>
            localStorage.removeItem('inv_username');
            localStorage.removeItem('inv_role');
            </script>
            """, unsafe_allow_html=True)
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            st.session_state.original_role = None
            st.query_params.clear()
            st.rerun()

# --- HEADER BAR FOR TECH (WITHOUT LOGOUT BUTTON) ---
if st.session_state.role in ["ช่างประจำอาคาร", "ช่างประจำอาคารพิเศษ"]:
    st.markdown(
        f'<div class="app-hero"><div><div class="t">🛠️ ระบบบริหารจัดการและเช็คสถานะอุปกรณ์</div>'
        f'<div class="s">อุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ · {get_now_str("%d/%m/%Y")}</div></div>'
        f'<span class="chip">{esc(st.session_state.username)} ({esc(st.session_state.role)})</span></div>',
        unsafe_allow_html=True)
else:
    # เพิ่มปุ่มรีเฟรชข้อมูลด่วนสำหรับแอดมิน เพื่อดึงข้อมูลใหม่จากฐานข้อมูลทันทีโดยไม่ต้องกดรีเฟรชเบราว์เซอร์
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
            st.rerun()

# --- ALERT SYSTEM & DATA FETCH ---
low_stock_limit = int(get_settings_val('low_stock_threshold', '1'))
items_df = get_items_df()

abnormal_items = items_df[
    items_df['status'].isin(['ชำรุด', 'สูญหาย', 'ยืม', 'อุปกรณ์หมด']) | 
    items_df['status'].str.startswith('กำลังใช้งาน', na=False)
] if not items_df.empty else pd.DataFrame()

low_stock_list = []
if not items_df.empty:
    for _, row in items_df.iterrows():
        if row['subcategory'] == 'เครื่องมือช่าง':
            continue
        threshold = 0 if row.get('alert_zero', 0) == 1 else low_stock_limit
        if row['quantity'] <= threshold:
            low_stock_list.append(row)
low_stock_items = pd.DataFrame(low_stock_list)

borrowed_cnt = db.transactions.count_documents({"status": "กำลังยืม"})
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

# --- SHARED BORROW / RETURN COMPONENT ---
def render_borrow_return_system():
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])
    
    with sub_borrow:
        available_items = items_df[items_df['quantity'] > 0] if not items_df.empty else pd.DataFrame()
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
                        b_img_b64 = compress_image_to_base64(borrow_img_file)
                        now_time = get_now_str("%Y-%m-%d %H:%M")
                        
                        tx_id = get_next_sequence("transactions_id")
                        db.transactions.insert_one({
                            "id": tx_id,
                            "item_id": selected_id,
                            "borrower_name": borrower_name,
                            "borrow_date": now_time,
                            "return_date": None,
                            "status": "กำลังยืม",
                            "borrower_image": b_img_b64,
                            "quantity": borrow_qty,
                            "giver_name": st.session_state.username,
                            "receiver_name": None,
                            "return_image": None
                        })
                        
                        new_qty = max_q - borrow_qty
                        new_status = 'ยืม' if new_qty == 0 else item_info['status']
                        
                        db.items.update_one({"id": selected_id}, {"$set": {"quantity": new_qty, "status": new_status}})
                        st.cache_data.clear()
                        
                        st.success(f"บันทึกการยืม {item_info['name']} จำนวน {borrow_qty} ชิ้น เรียบร้อยแล้ว")
                        st.rerun()
                    else:
                        st.error("❌ กรุณากรอกชื่อผู้ยืมให้เรียบร้อย")
        else:
            st.info("ไม่มีอุปกรณ์ที่มีจำนวนคงเหลือให้ยืมในขณะนี้")
            
    with sub_return:
        st.markdown("#### รายการที่กำลังถูกยืมอยู่")
        active_txs = list(db.transactions.find({"status": "กำลังยืม"}, {"_id": 0}).sort("id", -1))
        
        if active_txs:
            for t in active_txs:
                item_info = db.items.find_one({"id": t["item_id"]})
                item_name = item_info["name"] if item_info else "Unknown"
                current_q = item_info["quantity"] if item_info else 0
                
                giver_str = f" | ผู้ให้ยืม: {t.get('giver_name')}" if t.get('giver_name') else ""
                with st.expander(f"📦 อุปกรณ์: {item_name} (จำนวนยืม: {t.get('quantity', 1)} ชิ้น) | ผู้ยืม: {t.get('borrower_name')}{giver_str}"):
                    col_r1, col_r2 = st.columns([1, 2])
                    with col_r1:
                        p_img = get_pil_image_from_base64(t.get('borrower_image'))
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
                            
                            if st.form_submit_button(f"✅ รับคืนอุปกรณ์รายการนี้"):
                                now_time = get_now_str("%Y-%m-%d %H:%M")
                                r_img_b64 = compress_image_to_base64(ret_img_file)
                                    
                                db.transactions.update_one(
                                    {"id": t['id']},
                                    {"$set": {
                                        "return_date": now_time,
                                        "status": "คืนแล้ว",
                                        "receiver_name": st.session_state.username,
                                        "return_image": r_img_b64
                                    }}
                                )
                                
                                tx_qty = int(t.get('quantity', 1))
                                new_q = current_q + tx_qty
                                db.items.update_one({"id": t['item_id']}, {"$set": {"quantity": new_q, "status": "ปกติ"}})
                                st.cache_data.clear()
                                
                                st.success(f"รับคืน {item_name} จำนวน {tx_qty} ชิ้น เรียบร้อยแล้ว")
                                st.rerun()
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืมในขณะนี้")
            
    with sub_history:
        st.markdown("#### ประวัติการยืม-คืนทั้งหมด")
        all_txs = list(db.transactions.find({}, {"_id": 0}).sort("id", -1))
        tx_history_data = []
        for t in all_txs:
            item_info = db.items.find_one({"id": t["item_id"]})
            tx_history_data.append({
                "รหัส": t["id"],
                "ชื่ออุปกรณ์": item_info["name"] if item_info else "Unknown",
                "จำนวน": t.get("quantity", 1),
                "ผู้ยืม": t.get("borrower_name"),
                "ผู้ให้ยืม": t.get("giver_name"),
                "ผู้รับคืน": t.get("receiver_name"),
                "วันที่ยืม": t.get("borrow_date"),
                "วันที่คืน": t.get("วันที่คืน") or t.get("return_date"),
                "สถานะ": t.get("status")
            })
        tx_history = pd.DataFrame(tx_history_data)
        st.dataframe(tx_history, use_container_width=True, hide_index=True)

# --- DIVISION BY ROLE ---
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
            if not filtered_df.empty:
                if search_kw.strip():
                    filtered_df = filtered_df[filtered_df['name'].str.contains(search_kw.strip(), case=False, na=False)]
                if cat_filter != "ทั้งหมด":
                    filtered_df = filtered_df[filtered_df['category'] == cat_filter]
                if status_filter != "ทั้งหมด":
                    filtered_df = filtered_df[filtered_df['status'] == status_filter]
                
            st.caption(f"แสดงรายการอุปกรณ์ทั้งหมด {len(filtered_df)} จาก {len(items_df)} รายการ (💡 คลิกเลือกแถวในตารางด้านล่าง เพื่อเปิดหน้าต่างป๊อปอัพแก้ไขข้อมูลทันที)")
            
            show_df = filtered_df[['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note']].copy() if not filtered_df.empty else pd.DataFrame(columns=['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note'])
            if not show_df.empty:
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
                selected_idx = selected_rows[0]
                qe_id = int(filtered_df.iloc[selected_idx]['id'])
                st.session_state.quick_edit_id = qe_id

            if "quick_edit_id" in st.session_state and st.session_state.quick_edit_id:
                qe_id = st.session_state.quick_edit_id
                qe_row = db.items.find_one({"id": qe_id}, {"_id": 0})
                if qe_row:
                    st.markdown("---")
                    with st.expander(f"📌 หน้าต่างป๊อปอัพแก้ไขข้อมูลอุปกรณ์: #{qe_row['id']} - {qe_row['name']}", expanded=True):
                        with st.form(f"quick_edit_form_{qe_id}"):
                            qe_name = st.text_input("ชื่ออุปกรณ์", value=qe_row['name'])
                            qe_category = st.selectbox("หมวดหมู่หลัก", ["อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"], index=0 if qe_row['category']=="อุปกรณ์ช่าง" else 1)
                            
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
                            qe_note = st.text_area("หมายเหตุ", value=qe_row.get('note') if qe_row.get('note') else "")
                            
                            pil_img = get_pil_image_from_base64(qe_row.get('image'))
                            if pil_img:
                                st.image(pil_img, width=150, caption="รูปภาพปัจจุบัน")
                            qe_file = st.file_uploader("เปลี่ยนรูปภาพใหม่ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"qe_file_{qe_id}")
                            
                            col_qe1, col_qe2, col_qe3 = st.columns([1, 1, 2])
                            if col_qe1.form_submit_button("💾 บันทึกการแก้ไข", type="primary"):
                                img_base64 = qe_row.get('image')
                                if qe_file is not None:
                                    img_base64 = compress_image_to_base64(qe_file)
                                az_val = 1 if qe_alert_zero else 0
                                db.items.update_one(
                                    {"id": qe_id},
                                    {"$set": {
                                        "name": qe_name,
                                        "category": qe_category,
                                        "subcategory": qe_subcat,
                                        "quantity": qe_quantity,
                                        "status": qe_status,
                                        "alert_zero": az_val,
                                        "note": qe_note,
                                        "image": img_base64
                                    }}
                                )
                                st.cache_data.clear()
                                st.success("อัปเดตข้อมูลสำเร็จ!")
                                del st.session_state.quick_edit_id
                                st.rerun()
                            if col_qe2.form_submit_button("🗑️ ลบอุปกรณ์นี้", type="secondary"):
                                db.items.delete_one({"id": qe_id})
                                st.cache_data.clear()
                                st.success("ลบเรียบร้อยแล้ว!")
                                del st.session_state.quick_edit_id
                                st.rerun()
                            if col_qe3.form_submit_button("❌ ปิดหน้าต่าง"):
                                del st.session_state.quick_edit_id
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
                            img_base64 = compress_image_to_base64(uploaded_file)
                            az_val = 1 if alert_zero else 0
                            new_id = get_next_sequence("items_id")
                            db.items.insert_one({
                                "id": new_id,
                                "name": name,
                                "category": category,
                                "subcategory": subcategory,
                                "quantity": quantity,
                                "status": status,
                                "alert_zero": az_val,
                                "note": note,
                                "image": img_base64
                            })
                            st.cache_data.clear()
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
                                    img_base64 = compress_image_to_base64(e_file)
                                az_val = 1 if e_alert_zero else 0
                                db.items.update_one(
                                    {"id": item_id_int},
                                    {"$set": {
                                        "name": e_name,
                                        "category": e_category,
                                        "subcategory": e_subcat,
                                        "quantity": e_quantity,
                                        "status": e_status,
                                        "alert_zero": az_val,
                                        "note": e_note,
                                        "image": img_base64
                                    }}
                                )
                                st.cache_data.clear()
                                st.success("อัปเดตข้อมูลสำเร็จ!")
                                st.rerun()
                            if col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary"):
                                db.items.delete_one({"id": item_id_int})
                                st.cache_data.clear()
                                st.success("ลบเรียบร้อยแล้ว!")
                                st.rerun()

            with sub_bulk:
                st.markdown("### 📁 อัปโหลดรูปภาพอุปกรณ์แบบกลุ่ม (ตามชื่อไฟล์รหัสอุปกรณ์)")
                st.write("ตั้งชื่อไฟล์รูปภาพตามรหัสอุปกรณ์ เช่น `1.jpg` สำหรับ ปลั๊กโรลElecton, `2.png` สำหรับ สว่านแบตMakita ฯลฯ แล้วเลือกไฟล์ทั้งหมดพร้อมกันได้เลย")
                
                bulk_files = st.file_uploader("เลือกไฟล์รูปภาพทั้งหมด", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="bulk_img_files")
                if bulk_files:
                    st.info(f"เลือกไฟล์ทั้งหมด: **{len(bulk_files)} รูป**")
                    if st.button("🚀 ยืนยันจับคู่และอัปโหลดรูปภาพเข้าระบบ", type="primary"):
                        success_up = 0
                        for img_f in bulk_files:
                            pure_name = img_f.name.split('.')[0]
                            if pure_name.isdigit():
                                t_id = int(pure_name)
                                img_b64 = compress_image_to_base64(img_f)
                                match_check = db.items.find_one({"id": t_id})
                                if match_check:
                                    db.items.update_one({"id": t_id}, {"$set": {"image": img_b64}})
                                    success_up += 1
                        st.cache_data.clear()
                        st.success(f"อัปเดตรูปภาพตามชื่อไฟล์สำเร็จทั้งหมด {success_up} รายการ!")
                        st.rerun()

        with tab_excel_import:
            st.markdown("### ⚡ โหลดชุดข้อมูลตั้งต้นทั้งหมด (ลำดับใหม่)")
            st.write("การคลิกปุ่มนี้จะล้างข้อมูลเดิมและโหลดรายการพร้อมลำดับใหม่ทั้งหมด")
            if st.button("🚀 รีเซ็ตและโหลดอุปกรณ์ทั้งหมดตามรายการใหม่", type="primary"):
                db.items.delete_many({})
                db.counters.delete_one({"_id": "items_id"})
                for i in DEFAULT_INITIAL_ITEMS:
                    new_id = get_next_sequence("items_id")
                    db.items.insert_one({
                        "id": new_id,
                        "name": i[0],
                        "category": i[1],
                        "subcategory": i[2],
                        "quantity": i[3],
                        "status": i[4],
                        "alert_zero": 0,
                        "note": i[5],
                        "image": i[6]
                    })
                st.cache_data.clear()
                st.success("นำเข้าอุปกรณ์และลำดับใหม่สำเร็จ!")
                st.rerun()

    with admin_menu[1]:
        st.subheader("📊 รายการตรวจเช็คสภาพอุปกรณ์")
        report_type = st.radio("เลือกมุมมองรายงาน", ["รายวัน (Daily)", "รายเดือน (Monthly)", "รายปี (Yearly)", "ประวัติทั้งหมด"], horizontal=True)
        inspections_df = pd.DataFrame(list(db.inspections.find({}, {"_id": 0}).sort("id", -1)))
        
        if not inspections_df.empty:
            inspections_df['inspection_date'] = pd.to_datetime(inspections_df['inspection_date'])
            now_dt = get_now_th()
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
                    photos_raw = row.get('photos')
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

    with admin_menu[2]:
        st.subheader("📥 จัดการคำขอเพิ่มอุปกรณ์เข้าคลัง")
        sub_req_pending, sub_req_history = st.tabs(["📥 คำขอที่รออนุมัติ", "📜 ประวัติการอนุมัติคำขอ"])
        
        with sub_req_pending:
            pending_reqs = list(db.requisition_requests.find({"status": "รออนุมัติ"}, {"_id": 0}).sort("id", -1))
            
            if pending_reqs:
                for req in pending_reqs:
                    item_info = db.items.find_one({"id": req["item_id"]})
                    item_name = item_info["name"] if item_info else "Unknown"
                    current_stock = item_info["quantity"] if item_info else 0
                    
                    with st.container():
                        st.write(f"🆔 **รหัสคำขอ:** #{req['id']} | 👤 **ผู้ขอเพิ่ม:** {req['tech_name']} | 📅 **วันที่ขอ:** {req['request_date']}")
                        st.write(f"📦 **อุปกรณ์:** {item_name} | **จำนวนที่ขอเพิ่ม:** +{req['quantity']} ชิ้น (คงเหลือในคลังปัจจุบัน: {current_stock})")
                        st.write(f"📝 **หมายเหตุ/เหตุผล:** {req['note']}")
                        
                        col_app1, col_app2 = st.columns(2)
                        if col_app1.button(f"✅ อนุมัติ (เพิ่มจำนวนเข้าคลัง)", key=f"approve_{req['id']}"):
                            new_stock = current_stock + int(req['quantity'])
                            now_time = get_now_str("%Y-%m-%d %H:%M:%S")
                            db.items.update_one({"id": req['item_id']}, {"$set": {"quantity": new_stock, "status": "ปกติ"}})
                            db.requisition_requests.update_one({"id": req['id']}, {"$set": {"status": "อนุมัติ", "approval_date": now_time}})
                            st.cache_data.clear()
                            st.success(f"อนุมัติคำขอ #{req['id']} เรียบร้อยแล้ว (เพิ่มจำนวนในคลังเป็น {new_stock} ชิ้น)")
                            st.rerun()
                            
                        if col_app2.button(f"❌ ไม่อนุมัติ", key=f"reject_{req['id']}"):
                            now_time = get_now_str("%Y-%m-%d %H:%M:%S")
                            db.requisition_requests.update_one({"id": req['id']}, {"$set": {"status": "ไม่อนุมัติ", "approval_date": now_time}})
                            st.cache_data.clear()
                            st.warning(f"ปฏิเสธคำขอ #{req['id']} เรียบร้อยแล้ว")
                            st.rerun()
                        st.markdown("---")
            else:
                st.info("ไม่มีคำขอเพิ่มอุปกรณ์ที่รอการอนุมัติในขณะนี้")
                
        with sub_req_history:
            st.markdown("#### 📜 ประวัติการอนุมัติคำขอเพิ่มอุปกรณ์")
            req_history_list = list(db.requisition_requests.find({"status": {"$ne": "รออนุมัติ"}}, {"_id": 0}).sort("id", -1))
            req_history_data = []
            for r in req_history_list:
                item_info = db.items.find_one({"id": r["item_id"]})
                req_history_data.append({
                    "รหัส": r["id"],
                    "ผู้ขอ": r.get("tech_name"),
                    "ชื่ออุปกรณ์": item_info["name"] if item_info else "Unknown",
                    "จำนวนที่ขอ": r.get("quantity"),
                    "หมายเหตุ": r.get("note"),
                    "วันที่ขอ": r.get("request_date"),
                    "วันที่อนุมัติ": r.get("approval_date"),
                    "สถานะ": r.get("status")
                })
            req_history_df = pd.DataFrame(req_history_data)
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
                st.success("บันทึกค่าการแจ้งเตือนสำเร็จ!")
                st.rerun()
                
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
                st.success("บันทึกการตั้งค่าโควต้าเรียบร้อยแล้ว!")
                st.rerun()
                
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
                        existing = db.tech_users.find_one({"username": new_t_user})
                        if not existing:
                            t_id = get_next_sequence("tech_users_id")
                            db.tech_users.insert_one({"id": t_id, "username": new_t_user, "password": new_t_pass})
                            st.cache_data.clear()
                            st.success(f"สร้างบัญชีช่าง '{new_t_user}' สำเร็จ!")
                            st.rerun()
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
                            st.cache_data.clear()
                            st.success("อัปเดตบัญชีช่างสำเร็จ!")
                            st.rerun()
                        if col_tu2.form_submit_button("ลบบัญชีนี้"):
                            if db.tech_users.count_documents({}) <= 1:
                                st.error("ต้องเหลือบัญชีช่างไว้อย่างน้อย 1 บัญชี")
                            else:
                                db.tech_users.delete_one({"id": t_id_int})
                                st.cache_data.clear()
                                st.success("ลบบัญชีช่างเรียบร้อยแล้ว!")
                                st.rerun()

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
                        success_count = 0
                        dup_count = 0
                        for u, p in parsed_techs:
                            existing = db.tech_users.find_one({"username": u})
                            if not existing:
                                t_id = get_next_sequence("tech_users_id")
                                db.tech_users.insert_one({"id": t_id, "username": u, "password": p})
                                success_count += 1
                            else:
                                dup_count += 1
                        st.cache_data.clear()
                        st.success(f"นำเข้าสำเร็จ! เพิ่มใหม่ {success_count} บัญชี (ซ้ำ/มีอยู่แล้ว {dup_count} บัญชี)")
                        st.rerun()

elif st.session_state.role in ["ช่างประจำอาคาร", "ช่างประจำอาคารพิเศษ"]:
    if st.session_state.role == "ช่างประจำอาคารพิเศษ":
        col_banner, col_btn_back = st.columns([3, 1])
        with col_banner:
            st.info("⭐ คุณเข้าใช้งานในสถานะ **ช่างประจำอาคารพิเศษ** (สิทธิ์พิเศษจากแอดมิน)")
        with col_btn_back:
            if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True, key="banner_switch_back"):
                st.session_state.role = "ผู้ออกแบบ/ดูแลระบบ"
                st.session_state.original_role = "ผู้ออกแบบ/ดูแลระบบ"
                st.query_params["role"] = "ผู้ออกแบบ/ดูแลระบบ"
                st.query_params["original_role"] = "ผู้ออกแบบ/ดูแลระบบ"
                st.rerun()
    
    st.subheader("📋 หน้าต่างปฏิบัติงานช่างประจำอาคาร")
    
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
                req_item_dict = {f"#{row['id']} {row['name']} [{row['category']}] (คงเหลือในคลัง: {row['quantity']} ชิ้น)": row['id'] for _, row in tools_requisition_df.iterrows()}
                sel_req_label = st.selectbox("เลือกอุปกรณ์ที่ต้องการเพิ่มจำนวน *", list(req_item_dict.keys()))
                
                req_selected_id = req_item_dict[sel_req_label]
                req_item_info = items_df[items_df['id'] == req_selected_id].iloc[0]
                
                req_qty = st.number_input("จำนวนที่ต้องการเพิ่มเข้าคลัง *", min_value=1, value=1)
                req_note = st.text_area("หมายเหตุ / เหตุผลที่ขอเพิ่ม *")
                
                if st.form_submit_button("📤 ส่งคำขอเบิกของ (รอผู้ออกแบบ/ดูแลระบบอนุมัติ)"):
                    if req_note.strip():
                        now_time = get_now_str("%Y-%m-%d %H:%M")
                        req_id = get_next_sequence("requisition_requests_id")
                        db.requisition_requests.insert_one({
                            "id": req_id,
                            "tech_name": st.session_state.username,
                            "item_id": req_selected_id,
                            "quantity": req_qty,
                            "note": req_note,
                            "status": "รออนุมัติ",
                            "request_date": now_time,
                            "approval_date": None
                        })
                        st.cache_data.clear()
                        st.success(f"ส่งคำขอเบิกของ '{req_item_info['name']}' จำนวน +{req_qty} ชิ้น ไปยังผู้ออกแบบ/ดูแลระบบเรียบร้อยแล้ว!")
                        st.rerun()
                    else:
                        st.error("กรุณาระบุหมายเหตุหรือเหตุผลที่ขอเบิกของ")
        else:
            st.info("ไม่พบรายการอุปกรณ์ตามคำค้นหา")
            
        st.markdown("---")
        st.markdown("#### 📜 ประวัติคำขอเบิกของของคุณ")
        my_reqs_list = list(db.requisition_requests.find({"tech_name": st.session_state.username}, {"_id": 0}).sort("id", -1))
        my_reqs_data = []
        for r in my_reqs_list:
            item_info = db.items.find_one({"id": r["item_id"]})
            my_reqs_data.append({
                "รหัส": r["id"],
                "ชื่ออุปกรณ์": item_info["name"] if item_info else "Unknown",
                "จำนวนที่ขอ": r.get("quantity"),
                "หมายเหตุ": r.get("note"),
                "วันที่ขอ": r.get("request_date"),
                "วันที่อนุมัติ": r.get("approval_date"),
                "สถานะ": r.get("status")
            })
        my_requests = pd.DataFrame(my_reqs_data)
        if not my_requests.empty:
            st.dataframe(my_requests, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการส่งคำขอเบิกของ")
        
    with tech_main_tab[0]:
        tech_category_choice = st.radio("เลือกหมวดหมู่การทำงาน", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True)
        st.markdown("---")
        
        today_str = get_now_str("%Y-%m-%d")
        
        if tech_category_choice == "🔧 หมวดอุปกรณ์ช่าง":
            st.markdown("### 🔧 หมวดอุปกรณ์ช่าง (คลิกชื่อเพื่อดูรูปภาพ & เช็คสถานะ)")
            
            global_count = db.inspections.count_documents({
                "category": "อุปกรณ์ช่าง",
                "inspection_date": {"$regex": f"^{today_str}"}
            })
            
            base_quota = int(get_settings_val('global_daily_quota', '3'))
            extra_quota = int(get_settings_val(f"extra_quota_{today_str}", '0'))
            total_allowed = base_quota + extra_quota
            
            if global_count >= total_allowed:
                st.error("⚠️ ครบโควตารอบการตรวจสำหรับวันนี้แล้ว (กรุณาติดต่อผู้ออกแบบ/ดูแลระบบเพื่อเพิ่มรอบตรวจพิเศษ)")
            else:
                tools_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['quantity'] > 0)] if not items_df.empty else pd.DataFrame()
                
                if not tools_df.empty:
                    tech_search = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
                    if tech_search.strip():
                        tools_df = tools_df[tools_df['name'].str.contains(tech_search.strip(), case=False, na=False)]
                    
                    with keyed_container("tech_check_list", height=500):
                        item_reports = {}
                        for _, row in tools_df.iterrows():
                            current_status = row['status']
                            is_currently_flagged = current_status != "ปกติ"
                            
                            col_item, col_flag = st.columns([5, 1.4])
                            
                            with col_item:
                                status_badge = f" (สถานะเดิม: {current_status})" if is_currently_flagged else ""
                                with st.expander(f"🛠️ {row['name']}{status_badge} (คงเหลือ: {row['quantity']})"):
                                    pil_img = get_pil_image_from_base64(row['image'])
                                    if pil_img:
                                        st.image(pil_img, width=220, caption=f"รูปภาพ: {row['name']}")
                                    else:
                                        st.info("*(ไม่มีรูปภาพประกอบสำหรับรายการนี้)*")
                            
                            with col_flag:
                                is_flagged = st.checkbox("แจ้งปัญหา", value=is_currently_flagged, key=f"flag_{row['id']}")
                            
                            issue_type = "ปกติ"
                            issue_detail = ""
                            issue_qty = 1
                            
                            if is_flagged:
                                options_list = ["-- เลือกประเภท --", "กำลังใช้งาน", "อุปกรณ์หมด", "ชำรุด", "สูญหาย"]
                                default_idx = 0
                                detail_default = ""
                                
                                if current_status.startswith("กำลังใช้งาน"):
                                    default_idx = 1
                                    m_detail = re.search(r'\((.*?)\)', current_status)
                                    if m_detail:
                                        detail_default = m_detail.group(1)
                                elif current_status in options_list:
                                    default_idx = options_list.index(current_status)
                                
                                issue_type = st.selectbox(
                                    "ประเภทปัญหา *", 
                                    options_list, 
                                    index=default_idx,
                                    key=f"issue_type_{row['id']}"
                                )
                                
                                item_total_q = int(row['quantity'])
                                
                                if issue_type == "กำลังใช้งาน":
                                    issue_detail = st.text_input("ระบุรายละเอียดการใช้งาน *", value=detail_default, key=f"issue_detail_{row['id']}")
                                    if item_total_q > 1:
                                        issue_qty = st.number_input("จำนวนชิ้นที่นำไปใช้งาน *", min_value=1, max_value=item_total_q, value=1, key=f"issue_qty_{row['id']}")
                                    else:
                                        issue_qty = 1
                                elif issue_type in ["ชำรุด", "สูญหาย", "อุปกรณ์หมด"]:
                                    if item_total_q > 1:
                                        issue_qty = st.number_input(f"จำนวนชิ้นที่{issue_type} *", min_value=1, max_value=item_total_q, value=1, key=f"issue_qty_{row['id']}")
                                    else:
                                        issue_qty = 1
                                    
                            item_reports[row['id']] = {
                                "flagged": is_flagged, 
                                "status": issue_type, 
                                "detail": issue_detail,
                                "qty": issue_qty
                            }
                            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
                            
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### 📸 รูปถ่ายรวมหน้างาน / ภาพประกอบการตรวจเช็ค (บังคับครบทั้ง 4 รูป)")
                    
                    uploaded_photos_b64 = []
                    for i in range(4):
                        up_file = st.file_uploader(f"รูปถ่ายรวมที่ {i+1} *", type=["jpg", "jpeg", "png"], key=f"tech_p_{i}")
                        if up_file is not None:
                            b64_str = compress_image_to_base64(up_file)
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
                            now_time = get_now_str("%Y-%m-%d %H:%M:%S")
                            flagged_summaries = []
                            
                            for item_id, data in item_reports.items():
                                item_row = items_df[items_df['id'] == item_id].iloc[0]
                                curr_q = int(item_row['quantity'])
                                item_name = item_row['name']
                                
                                if data["flagged"]:
                                    final_st = data["status"]
                                    if data["status"] == "กำลังใช้งาน" and data["detail"].strip():
                                        final_st = f"กำลังใช้งาน ({data['detail']})"
                                    
                                    u_qty = data["qty"]
                                    if data["status"] in ["ชำรุด", "สูญหาย", "อุปกรณ์หมด", "กำลังใช้งาน"]:
                                        new_q = max(0, curr_q - u_qty)
                                        db.items.update_one({"id": item_id}, {"$set": {"status": final_st, "quantity": new_q}})
                                    else:
                                        db.items.update_one({"id": item_id}, {"$set": {"status": final_st}})
                                        
                                    detail_txt = f"{item_name}: {data['status']}" + (f" ({data['detail']})" if data['detail'] else "") + (f" [{data['status']} {data['qty']} ชิ้น]" if data['qty'] > 1 else "")
                                    flagged_summaries.append(detail_txt)
                                else:
                                    db.items.update_one({"id": item_id}, {"$set": {"status": "ปกติ"}})
                                    
                            photos_str = "|||".join(uploaded_photos_b64)
                            summary_details = ", ".join(flagged_summaries) if flagged_summaries else "ปกติทุกรายการ"
                            summary_note = f"รอบที่ {global_count+1} | รายการผิดปกติ: {summary_details}"
                            
                            insp_id = get_next_sequence("inspections_id")
                            db.inspections.insert_one({
                                "id": insp_id,
                                "tech_name": st.session_state.username,
                                "category": "อุปกรณ์ช่าง",
                                "inspection_date": now_time,
                                "session_num": global_count + 1,
                                "details": summary_note,
                                "photos": photos_str
                            })
                            # เคลียร์แคชทันทีเพื่อให้แอดมินเห็นข้อมูลใหม่ทันที
                            st.cache_data.clear()
                            
                            # ล้างค่าไฟล์รูปถ่ายใน session_state เพื่อให้ช่องอัปโหลดว่างเปล่าหลังกดส่ง
                            for i in range(4):
                                if f"tech_p_{i}" in st.session_state:
                                    del st.session_state[f"tech_p_{i}"]
                            
                            st.success("บันทึกผลการตรวจสอบเรียบร้อยแล้ว!")
                            st.rerun()
                else:
                    st.info("ไม่มีอุปกรณ์ช่างให้ตรวจสอบในขณะนี้")
                    
        else:
            st.markdown("### 🏊 หมวดอุปกรณ์สระว่ายน้ำ (เช็คจำนวน & ดูรูปภาพ)")
            st.write("คลิกที่ชื่อรายการอุปกรณ์เพื่อดูรูปภาพ และปรับปรุงจำนวนคงเหลือ")
            
            pool_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ'] if not items_df.empty else pd.DataFrame()
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
                        b64_str = compress_image_to_base64(up_file)
                        uploaded_pool_photos_b64.append(b64_str)
                        
                st.progress(len(uploaded_pool_photos_b64) / 4, text=f"📸 แนบรูปแล้ว {len(uploaded_pool_photos_b64)}/4 รูป")
                if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                    if len(uploaded_pool_photos_b64) < 4:
                        st.error("❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานสระว่ายน้ำให้ครบทั้ง 4 รูป")
                    else:
                        now_time = get_now_str("%Y-%m-%d %H:%M:%S")
                        pool_summaries = []
                        for item_id, q_val in updated_quantities.items():
                            old_row = items_df[items_df['id'] == item_id].iloc[0]
                            db.items.update_one({"id": item_id}, {"$set": {"quantity": q_val}})
                            if q_val != int(old_row['quantity']):
                                pool_summaries.append(f"{old_row['name']}: ปรับจาก {old_row['quantity']} เหลือ {q_val}")
                                
                        photos_str = "|||".join(uploaded_pool_photos_b64)
                        summary_note = "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ" + (f" | การเปลี่ยนแปลง: {', '.join(pool_summaries)}" if pool_summaries else "")
                        
                        insp_id = get_next_sequence("inspections_id")
                        db.inspections.insert_one({
                            "id": insp_id,
                            "tech_name": st.session_state.username,
                            "category": "อุปกรณ์สระว่ายน้ำ",
                            "inspection_date": now_time,
                            "session_num": 1,
                            "details": summary_note,
                            "photos": photos_str
                        })
                        # เคลียร์แคชทันทีเพื่อให้แอดมินเห็นข้อมูลใหม่ทันที
                        st.cache_data.clear()
                        
                        # ล้างค่าไฟล์รูปถ่ายสระว่ายน้ำใน session_state หลังกดส่ง
                        for i in range(4):
                            if f"tech_pool_p_{i}" in st.session_state:
                                del st.session_state[f"tech_pool_p_{i}"]
                                  
                        st.success("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")
                        st.rerun()
            else:
                st.info("ไม่มีอุปกรณ์สระว่ายน้ำในระบบ")