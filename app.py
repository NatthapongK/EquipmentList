# =====================================================================
#  KAVE TOWN SHIFT - CENTRAL ENTERPRISE COMMAND & INVENTORY SYSTEM V6
#  ปรับปรุงครบ 7 หัวข้อ: ความปลอดภัย/สิทธิ์/กันข้อมูลซ้ำ/เครื่องมือค้นหา/ธีม/ลิมิตการใช้งาน
# =====================================================================

import streamlit as st
import streamlit.components.v1 as components
import pymongo
import pymongo.operations
import pymongo.errors
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64, html as _html, re, io, os, ssl, time, json, hashlib, secrets, threading, uuid, tomllib
from PIL import Image, ImageOps

try:
    import requests
except ImportError:
    requests = None

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

try:
    from streamlit_local_storage import LocalStorage
except ImportError:
    LocalStorage = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

# --- Password hashing backends (เลือกอันที่ติดตั้งได้) ---
try:
    import argon2
    from argon2 import PasswordHasher
    _ARGON2_HASHER = PasswordHasher()
    HAS_ARGON2 = True
except Exception:
    HAS_ARGON2 = False

try:
    import bcrypt
    HAS_BCRYPT = True
except Exception:
    HAS_BCRYPT = False

TZ_TH = timezone(timedelta(hours=7))
def get_now_th(): return datetime.now(TZ_TH)
def get_now_str(fmt="%Y-%m-%d %H:%M:%S"): return get_now_th().strftime(fmt)

st.set_page_config(
    page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ",
    page_icon="🛠️", layout="wide", initial_sidebar_state="expanded"
)

# =====================================================================
#  ข้อ 1: SECURITY — ไม่มี credential/token รั่ว
# =====================================================================
def secret_get(section: str, key: str, default=None):
    """อ่านค่าจาก st.secrets อย่างปลอดภัย (ไม่ crash เมื่อไม่มีไฟล์)"""
    try:
        sec = st.secrets.get(section, {}) or {}
        val = sec.get(key, default)
        return default if val in (None, "") else val
    except Exception:
        return default

def env_get(*names, default=None):
    for n in names:
        v = os.environ.get(n)
        if v not in (None, ""):
            return v
    return default

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def mask_secret(v) -> str:
    """แสดงค่า credential แบบปิดบังบนหน้าจอ/ล็อก"""
    if not v:
        return "(ไม่ได้ตั้งค่า)"
    s = str(v)
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]

# =====================================================================
#  ข้อ 2: PASSWORD HASHING (Argon2 / bcrypt / PBKDF2) + กันใช้รหัสซ้ำ
# =====================================================================
PBKDF2_ROUNDS = 310_000
PASSWORD_HISTORY_KEEP = 5

def hash_password(password: str) -> str:
    if HAS_ARGON2:
        return "argon2$" + _ARGON2_HASHER.hash(password)
    if HAS_BCRYPT:
        return "bcrypt$" + bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS).hex()
    return f"pbkdf2${salt}${h}"

def verify_password(plain_password: str, stored_password: str) -> tuple[bool, bool]:
    """คืนค่า (ถูกต้อง, ต้องอัปเกรดเป็น hash ใหม่)"""
    if not stored_password:
        return False, False
    if stored_password.startswith("argon2$"):
        if not HAS_ARGON2:
            return False, False
        try:
            _ARGON2_HASHER.verify(stored_password.split("$", 1)[1], plain_password)
            return True, False
        except Exception:
            return False, False
    if stored_password.startswith("bcrypt$"):
        if not HAS_BCRYPT:
            return False, False
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.split("$", 1)[1].encode("utf-8")), False
        except Exception:
            return False, False
    if stored_password.startswith("pbkdf2$"):
        try:
            _, salt, expected = stored_password.split("$")
            h = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS).hex()
            return secrets.compare_digest(h, expected), False
        except Exception:
            return False, False
    # Legacy plain text → ต้องอัปเกรดทันที
    return (plain_password == stored_password), True

def password_strength(pwd: str) -> tuple[int, str]:
    score, tips = 0, []
    if len(pwd) >= 8: score += 1
    else: tips.append("อย่างน้อย 8 ตัวอักษร")
    if len(pwd) >= 12: score += 1
    else: tips.append("แนะนำ 12 ตัวขึ้นไป")
    if re.search(r"[A-Z]", pwd): score += 1
    else: tips.append("ต้องมีตัวพิมพ์ใหญ่")
    if re.search(r"[a-z]", pwd): score += 1
    else: tips.append("ต้องมีตัวพิมพ์เล็ก")
    if re.search(r"[0-9]", pwd): score += 1
    else: tips.append("ต้องมีตัวเลข")
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd): score += 1
    else: tips.append("ควรมีอักขระพิเศษ")
    return min(score, 5), ", ".join(tips)

# =====================================================================
#  ข้อ 3: ROLES & PERMISSIONS
# =====================================================================
ROLE_ADMIN = "ผู้ดูแลระบบ"
ROLE_IOT = "ผู้ควบคุม IoT"
ROLE_STORE = "ผู้ดูแลคลัง"
ROLE_TECH = "ช่างประจำอาคาร"
ROLE_TECH_SP = "ช่างประจำอาคารพิเศษ"
ROLE_AUDIT = "ผู้ตรวจสอบ (Audit)"

ALL_ROLES = [ROLE_ADMIN, ROLE_IOT, ROLE_STORE, ROLE_TECH, ROLE_TECH_SP, ROLE_AUDIT]
TECH_ROLES = [ROLE_TECH, ROLE_TECH_SP]

PERMISSIONS = {
    ROLE_ADMIN:    ["dashboard", "inventory", "inventory_edit", "borrow", "requisition", "approve", "iot", "solar", "users", "settings", "audit", "export"],
    ROLE_IOT:      ["dashboard", "iot", "solar", "audit", "export"],
    ROLE_STORE:    ["dashboard", "inventory", "inventory_edit", "borrow", "requisition", "approve", "audit", "export"],
    ROLE_TECH:     ["dashboard", "inventory", "borrow", "requisition"],
    ROLE_TECH_SP:  ["dashboard", "inventory", "borrow", "requisition"],
    ROLE_AUDIT:    ["dashboard", "audit", "export"],
}

def has_perm(perm: str) -> bool:
    role = st.session_state.get("role")
    if not role:
        return False
    if role == ROLE_ADMIN:
        return True
    return perm in PERMISSIONS.get(role, [])

def role_label(role: str) -> str:
    return {
        ROLE_ADMIN: "ผู้ดูแลระบบ", ROLE_IOT: "ผู้ควบคุม IoT", ROLE_STORE: "ผู้ดูแลคลัง",
        ROLE_TECH: "ช่างประจำอาคาร", ROLE_TECH_SP: "ช่างประจำอาคารพิเศษ",
        ROLE_AUDIT: "ผู้ตรวจสอบ (Audit)"
    }.get(role, role)

# =====================================================================
#  ข้อ 6: THEME ENGINE (สร้าง CSS แบบ Dynamic)
# =====================================================================
THEME_PRESETS = {
    "🌊 Ocean (ค่าเริ่มต้น)": {"bg": "#08121E", "surface": "rgba(16,30,48,0.66)", "accent": "#38BDF8", "accent2": "#0EA5E9", "ink": "#F8FAFC", "muted": "#94A3B8"},
    "🌿 Nature (สีเขียว)":     {"bg": "#07140F", "surface": "rgba(16,42,32,0.66)", "accent": "#34D399", "accent2": "#10B981", "ink": "#ECFDF5", "muted": "#94A3B8"},
    "🌅 Sunset (สีส้ม)":       {"bg": "#170C08", "surface": "rgba(48,26,18,0.66)", "accent": "#FB923C", "accent2": "#F97316", "ink": "#FFF7ED", "muted": "#A8A29E"},
    "🌸 Rose (สีชมพู)":        {"bg": "#150A12", "surface": "rgba(48,20,36,0.66)", "accent": "#F472B6", "accent2": "#EC4899", "ink": "#FDF2F8", "muted": "#A8A29E"},
    "🩺 Teal (สีเขียวน้ำทะเล)": {"bg": "#041414", "surface": "rgba(10,42,42,0.66)", "accent": "#2DD4BF", "accent2": "#14B8A6", "ink": "#F0FDFA", "muted": "#94A3B8"},
    "⬛ Minimal (ขาวดำ)":      {"bg": "#0A0A0A", "surface": "rgba(24,24,24,0.82)", "accent": "#E5E5E5", "accent2": "#A3A3A3", "ink": "#FAFAFA", "muted": "#A3A3A3"},
}

def build_css(theme: dict, accent: str, density: str = "ปกติ") -> str:
    gap = "0.55rem" if density == "กระชับ" else "0.85rem"
    pad = "0.65rem 0.9rem" if density == "กระชับ" else "0.9rem 1.15rem"
    fsize = "0.92rem" if density == "กระชับ" else "1rem"
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
:root {{
  color-scheme: dark;
  --bg-main: {theme['bg']};
  --glass-surface: {theme['surface']};
  --glass-border: rgba(148,163,184,0.16);
  --ink: {theme['ink']};
  --muted: {theme['muted']};
  --accent: {accent};
  --accent2: {theme['accent2']};
  --ok:#10B981; --warn:#F59E0B; --bad:#EF4444;
}}
.stApp, .stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp li,
.stApp input,.stApp textarea,.stApp button,.stApp [data-baseweb="tab"],.stApp [data-baseweb="select"] {{
  font-family:'IBM Plex Sans Thai','Plus Jakarta Sans',system-ui,-apple-system,sans-serif;
  font-size:{fsize}; color:var(--ink) !important;
}}
.stApp {{ background-color:var(--bg-main) !important; color:var(--ink);
  background-image: radial-gradient(at 12% 8%, {accent}22 0px, transparent 50%),
                    radial-gradient(at 88% 14%, {theme['accent2']}18 0px, transparent 48%),
                    linear-gradient(160deg, {theme['bg']} 0%, #0C1B2E 55%, {theme['bg']} 100%) !important;
  background-attachment: fixed !important;
}}
header[data-testid="stHeader"] {{ background:transparent !important; height:1.3rem !important; }}
footer {{ visibility:hidden !important; display:none !important; }}
#MainMenu,.stDeployButton,[data-testid="stStatusWidget"] {{ display:none !important; }}
.block-container {{ padding-top:0.6rem !important; padding-bottom:3rem !important; max-width:1400px !important; }}
section[data-testid="stSidebar"] {{ background:rgba(8,16,28,0.94) !important; border-right:1px solid var(--glass-border) !important; }}
.brand-box {{ display:flex; align-items:center; gap:.7rem; padding:.7rem .85rem; margin-bottom:.7rem;
  border-radius:13px; background:{accent}18; border:1px solid {accent}44; }}
.brand-logo {{ width:2.3rem; height:2.3rem; border-radius:10px; background:linear-gradient(135deg,var(--accent2),{accent});
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#fff; }}
.brand-title {{ font-weight:800; font-size:.95rem; color:#F8FAFC; }}
.brand-sub {{ font-size:.72rem; color:var(--muted); }}
.user-card {{ display:flex; align-items:center; gap:.7rem; padding:.65rem .8rem; border:1px solid var(--glass-border);
  border-radius:13px; background:rgba(255,255,255,.03); margin-bottom:.7rem; }}
.avatar {{ width:2.25rem; height:2.25rem; border-radius:50%; background:{accent}22; border:1px solid {accent}55;
  color:{accent} !important; display:flex; align-items:center; justify-content:center; font-weight:800; flex:none; }}
.u-name {{ font-weight:700; font-size:.88rem; }}
.u-role {{ font-size:.72rem; color:var(--muted); }}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {{
  padding:.5rem .7rem !important; border-radius:10px !important; margin-bottom:.2rem !important;
  border:1px solid transparent !important; background:transparent !important; }}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {{
  background:{accent}22 !important; border:1px solid {accent}66 !important; box-shadow:inset 3px 0 0 {accent} !important; }}
.app-hero {{ background:var(--glass-surface); backdrop-filter:blur(20px); border-radius:15px; padding:{pad};
  border:1px solid var(--glass-border); display:flex; justify-content:space-between; align-items:center;
  gap:.7rem; flex-wrap:wrap; margin-bottom:{gap}; }}
.app-hero .t {{ font-size:1.15rem; font-weight:800; color:#fff; }}
.app-hero .s {{ font-size:.76rem; color:var(--muted); }}
.badge-row {{ display:flex; gap:.4rem; align-items:center; flex-wrap:wrap; }}
.status-pill-top {{ padding:.22rem .65rem; border-radius:999px; font-size:.72rem; font-weight:600;
  display:inline-flex; align-items:center; gap:.3rem; border:1px solid var(--glass-border); background:rgba(15,23,42,.6); }}
.status-pill-top.ok {{ color:#34D399 !important; border-color:#10B98166; background:#10B98118; }}
.status-pill-top.warn {{ color:#FBBF24 !important; border-color:#F59E0B66; background:#F59E0B18; }}
.status-pill-top.bad {{ color:#F87171 !important; border-color:#EF444477; background:#EF444424; }}
.status-pill-top.info {{ color:{accent} !important; border-color:{accent}66; background:{accent}18; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:{gap}; margin-bottom:{gap}; }}
.glass-kpi {{ background:linear-gradient(145deg,rgba(22,38,60,.62),rgba(14,25,42,.76)); backdrop-filter:blur(18px);
  border:1px solid var(--glass-border); border-radius:15px; padding:.85rem 1rem; }}
.glass-kpi .top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.35rem; }}
.glass-kpi .lbl {{ font-size:.73rem; color:var(--muted); font-weight:600; }}
.glass-kpi .ic-badge {{ width:1.8rem; height:1.8rem; border-radius:9px; background:{accent}18;
  border:1px solid {accent}33; display:flex; align-items:center; justify-content:center; }}
.glass-kpi .val {{ font-size:1.5rem; font-weight:800; color:#fff; line-height:1.15; }}
.glass-kpi .sub {{ font-size:.72rem; color:var(--muted); margin-top:.25rem; }}
.iot-card {{ background:var(--glass-surface); border:1px solid var(--glass-border); border-radius:13px; padding:.8rem .95rem; }}
.iot-card .hd {{ font-size:.7rem; color:var(--muted); text-transform:uppercase; font-weight:700; margin-bottom:.35rem; }}
.iot-card .nm {{ font-size:.92rem; font-weight:700; color:#F8FAFC; }}
.pill {{ padding:.18rem .6rem; border-radius:999px; font-size:.72rem; font-weight:700; display:inline-block; }}
.pill-normal {{ background:#10B98124; color:#34D399 !important; border:1px solid #10B98173; }}
.pill-alarm {{ background:#EF444433; color:#FCA5A5 !important; border:1px solid #EF44448C; animation:pulse-red 1.5s infinite; }}
.pill-off {{ background:#94A3B820; color:#94A3B8 !important; border:1px solid #94A3B84D; }}
@keyframes pulse-red {{ 0%,100%{{box-shadow:0 0 0 0 #EF444473}} 50%{{box-shadow:0 0 0 7px #EF444400}} }}
.stTabs [data-baseweb="tab-list"] {{ gap:.3rem; background:rgba(11,22,36,.68); padding:.3rem; border-radius:12px;
  border:1px solid var(--glass-border); overflow-x:auto; flex-wrap:nowrap; }}
.stTabs [data-baseweb="tab"] {{ height:auto; padding:.42rem .9rem; border-radius:9px; color:var(--muted) !important;
  background:transparent !important; border:1px solid transparent !important; white-space:nowrap; }}
.stTabs [aria-selected="true"] {{ color:#fff !important; font-weight:600 !important; background:{accent}14 !important;
  border-color:{accent}44 !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ display:none !important; }}
[data-testid="stExpander"] {{ border:1px solid var(--glass-border) !important; border-radius:12px !important;
  background:var(--glass-surface) !important; margin-bottom:.4rem !important; }}
[data-testid="stForm"] {{ border:1px solid var(--glass-border) !important; border-radius:13px !important;
  background:var(--glass-surface) !important; padding:.85rem !important; }}
[data-testid="stDataFrame"],.stTable {{ border:1px solid var(--glass-border) !important; border-radius:11px !important; overflow-x:auto !important; }}
.stApp button {{ border-radius:10px !important; font-weight:600 !important; border:1px solid var(--glass-border) !important;
  background:rgba(20,35,56,.72) !important; }}
.stApp button[kind="primary"],.stApp button[data-testid="stBaseButton-primary"],.stApp button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background:linear-gradient(135deg,var(--accent2),var(--accent)) !important; color:#fff !important; }}
.req-banner {{ display:flex; align-items:center; gap:.8rem; padding:.65rem .95rem; margin-bottom:.7rem; border-radius:11px;
  border:1px solid {accent}66; background:linear-gradient(90deg,{accent}33,rgba(15,23,42,.75)); }}
@media (max-width:768px) {{ .block-container{{padding-left:.3rem !important; padding-right:.3rem !important;}} }}
</style>
"""

# =====================================================================
#  MONGODB INITIALIZATION
# =====================================================================
DEFAULT_INITIAL_ITEMS = [
    ("ปลั๊กโรลElecton","อุปกรณ์ช่าง","เครื่องมือช่าง",2,"ปกติ","-",None),
    ("สว่านแบตMakita","อุปกรณ์ช่าง","เครื่องมือช่าง",2,"ปกติ","-",None),
    ("บันได3ขั้น","อุปกรณ์ช่าง","เครื่องมือช่าง",1,"ปกติ","-",None),
    ("เครื่องตรวจเช็กเต้ารับไฟฟ้า","อุปกรณ์ช่าง","เครื่องมือช่าง",1,"ปกติ","-",None),
    ("โบลเวอร์เป่าลม","อุปกรณ์ช่าง","เครื่องมือช่าง",1,"ปกติ","-",None),
    ("ไขควงแฉก","อุปกรณ์ช่าง","เครื่องมือช่าง",4,"ปกติ","-",None),
    ("ไขควงแบน","อุปกรณ์ช่าง","เครื่องมือช่าง",3,"ปกติ","-",None),
    ("ตลับเมตร","อุปกรณ์ช่าง","เครื่องมือช่าง",3,"ปกติ","-",None),
    ("แปลงทาสี","อุปกรณ์ช่าง","เครื่องมือช่าง",3,"ปกติ","-",None),
    ("ปืนยิงPU","อุปกรณ์ช่าง","เครื่องมือช่าง",1,"ปกติ","-",None),
    ("ชุดประแจหกเหลี่ยม","อุปกรณ์ช่าง","เครื่องมือช่าง",1,"ปกติ","-",None),
    ("กาวร้อน","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",1,"ปกติ","-",None),
    ("เทปพันสายไฟ","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",1,"ปกติ","-",None),
    ("เทปพันเกลียว","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",6,"ปกติ","-",None),
    ("สกรูเกลียวปล่อย6x1นิ้ว","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",100,"ปกติ","-",None),
    ("ใบตัดเหล็ก","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",7,"ปกติ","-",None),
    ("จารบี","อุปกรณ์ช่าง","อุปกรณ์ช่างทั่วไป",1,"ปกติ","-",None),
    ("คลอรีนผง 90%","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",3,"ปกติ","-",None),
    ("สารส้ม","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",4,"ปกติ","-",None),
    ("กรดเกลือผง","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",4,"ปกติ","-",None),
    ("เกลือบริสุทธิ์","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",50,"ปกติ","-",None),
    ("ชุดทดสอบคลอรีนและ PH","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",2,"ปกติ","-",None),
    ("ขวดน้ำยาคลอรีน","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",3,"ปกติ","-",None),
    ("ขวดน้ำยาpH","อุปกรณ์สระว่ายน้ำ","เคมีภัณฑ์",3,"ปกติ","-",None),
]

def build_default_docs():
    return [{"id": i, "name": n, "category": c, "subcategory": s, "quantity": q, "orig_quantity": q,
             "status": stt, "min_stock": 1, "alert_zero": 0, "note": note, "image": img, "version": 1}
            for i, (n, c, s, q, stt, note, img) in enumerate(DEFAULT_INITIAL_ITEMS, start=1)]

@st.cache_resource
def init_mongo():
    uri = secret_get("mongo", "uri") or env_get("MONGO_URI")
    if not uri:
        st.error("❌ ไม่พบ `st.secrets['mongo']['uri']` หรือ env `MONGO_URI` — ตั้งค่าใน `.streamlit/secrets.toml`")
        st.stop()
    client = pymongo.MongoClient(uri, maxPoolSize=20, serverSelectionTimeoutMS=8000)
    database = client["inventory_pro"]

    database.items.create_index("id", unique=True)
    database.transactions.create_index("id")
    database.transactions.create_index([("item_id", 1), ("status", 1)])
    database.inspections.create_index("id")
    database.inspections.create_index([("tech_name", 1), ("inspection_date", -1)])
    database.requisition_requests.create_index("id")
    database.tech_users.create_index("username", unique=True)
    database.settings.create_index("key", unique=True)
    database.sessions.create_index("token_hash", unique=True)
    database.sessions.create_index("created", expireAfterSeconds=60*60*24*30)
    database.iot_logs.create_index([("system", 1), ("datetime", -1)])
    database.audit_logs.create_index([("datetime", -1)])
    database.audit_logs.create_index([("actor", 1), ("datetime", -1)])
    database.idempotency_keys.create_index("key", unique=True)
    database.idempotency_keys.create_index("created", expireAfterSeconds=60*60*24)
    database.rate_limits.create_index("key", unique=True)
    database.password_history.create_index([("username", 1), ("created", -1)])
    database.admin_users.create_index("username", unique=True)

    if database.items.count_documents({}, limit=1) == 0:
        database.items.insert_many(build_default_docs())
        database.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
    else:
        database.items.update_many({"orig_quantity": {"$exists": False}}, [{"$set": {"orig_quantity": "$quantity"}}])
        database.items.update_many({"min_stock": {"$exists": False}}, [{"$set": {"min_stock": 1}}])
        database.items.update_many({"version": {"$exists": False}}, [{"$set": {"version": 1}}])

    database.settings.update_one({"key": "low_stock_threshold"}, {"$setOnInsert": {"value": "1"}}, upsert=True)
    database.settings.update_one({"key": "global_daily_quota"}, {"$setOnInsert": {"value": "3"}}, upsert=True)
    database.settings.update_one({"key": "ui_theme"}, {"$setOnInsert": {"value": list(THEME_PRESETS.keys())[0]}}, upsert=True)
    database.settings.update_one({"key": "ui_accent"}, {"$setOnInsert": {"value": "#38BDF8"}}, upsert=True)
    database.settings.update_one({"key": "ui_density"}, {"$setOnInsert": {"value": "ปกติ"}}, upsert=True)
    database.settings.update_one({"key": "session_idle_minutes"}, {"$setOnInsert": {"value": "30"}}, upsert=True)
    database.settings.update_one({"key": "max_rows_per_page"}, {"$setOnInsert": {"value": "500"}}, upsert=True)
    database.settings.update_one({"key": "max_export_rows"}, {"$setOnInsert": {"value": "5000"}}, upsert=True)
    database.settings.update_one({"key": "iot_cooldown_sec"}, {"$setOnInsert": {"value": "3"}}, upsert=True)
    return database

db = init_mongo()

# =====================================================================
#  ข้อ 1: IoT CONFIG — อ่านจาก st.secrets / env เท่านั้น (ไม่มี credential default)
# =====================================================================
IOT_TOPIC_DEFAULTS = {
    "topic_servo_cmd": "esp8266/servo",
    "topic_servo_status": "esp8266/servo/status",
    "topic_water": "Water alarm",
    "topic_check_clients": "CheckClients",
    "topic_fire": "Firealarm",
    "topic_fire_relay": "nodemcu/control/relay",
}

def get_iot_config(require_credentials: bool = True) -> dict:
    """
    ข้อ 1: ไม่มี DEFAULT_IOT_CONFIG ที่บรรจุ credential จริง
    ลำดับแหล่งข้อมูล: st.secrets['iot'] -> environment variables -> (ไฟล์ credentials.toml ถ้าเปิดใช้)
    """
    cfg = dict(IOT_TOPIC_DEFAULTS)
    cfg.update({
        "mqtt_server": "", "mqtt_port": 8883, "mqtt_user": "", "mqtt_pass": "",
        "line_token": "", "line_group_id": "",
        "growatt_user": "", "growatt_pass": "", "growatt_sn": "",
        "google_webapp_url": "",
    })

    # (ก) st.secrets
    for k in list(cfg.keys()):
        v = secret_get("iot", k)
        if v is not None:
            cfg[k] = v

    # (ข) environment variables
    env_map = {
        "mqtt_server": ("MQTT_SERVER",), "mqtt_user": ("MQTT_USER",), "mqtt_pass": ("MQTT_PASS",),
        "line_token": ("LINE_TOKEN",), "line_group_id": ("LINE_GROUP_ID",),
        "growatt_user": ("GROWATT_USER",), "growatt_pass": ("GROWATT_PASS",), "growatt_sn": ("GROWATT_SN",),
        "google_webapp_url": ("GOOGLE_WEBAPP_URL",),
    }
    for k, names in env_map.items():
        v = env_get(*names)
        if v is not None:
            cfg[k] = v
    v = env_get("MQTT_PORT")
    if v is not None and str(v).isdigit():
        cfg["mqtt_port"] = int(v)

    # (ค) ไฟล์ credential แยก (ต้องเปิดใช้งานด้วย env USE_CREDENTIALS_FILE=1 และอยู่นอก git)
    if env_get("USE_CREDENTIALS_FILE") == "1":
        cpath = os.path.join(os.path.dirname(__file__), ".streamlit", "credentials.toml")
        try:
            with open(cpath, "rb") as f:
                local = tomllib.load(f).get("iot", {}) or {}
            for k in list(cfg.keys()):
                if local.get(k):
                    cfg[k] = local[k]
        except Exception:
            pass

    # (ง) ค่าจาก DB settings (ไม่ใช่ credential — เช่น topic/port)
    for k in list(cfg.keys()):
        saved = get_settings_val(f"iot_{k}", None)
        if saved not in (None, "None", ""):
            cfg[k] = int(saved) if isinstance(cfg[k], int) and str(saved).isdigit() else saved

    cfg["mqtt_port"] = int(cfg.get("mqtt_port") or 8883)
    cfg["_has_mqtt"] = bool(cfg["mqtt_server"] and cfg["mqtt_user"] and cfg["mqtt_pass"])
    cfg["_has_line"] = bool(cfg["line_token"] and cfg["line_group_id"])
    cfg["_has_growatt"] = bool(cfg["growatt_user"] and cfg["growatt_pass"] and cfg["growatt_sn"])
    if require_credentials and not (cfg["_has_mqtt"] or cfg["_has_line"] or cfg["_has_growatt"]):
        cfg["_error"] = "ไม่พบ Credential ของ IoT — กรุณาตั้งค่าใน st.secrets['iot'] หรือ Environment Variables"
    return cfg

# =====================================================================
#  ข้อ 3: AUDIT LOG
# =====================================================================
def log_audit(action: str, target: str, before_val=None, after_val=None, detail: str = "", ok: bool = True):
    try:
        db.audit_logs.insert_one({
            "datetime": get_now_str("%Y-%m-%d %H:%M:%S"),
            "actor": st.session_state.get("username", "system"),
            "role": st.session_state.get("role", "-"),
            "action": action, "target": target,
            "before": before_val, "after": after_val,
            "detail": detail, "ok": ok,
        })
    except Exception:
        pass

# =====================================================================
#  ข้อ 4: IDEMPOTENCY / ATOMIC / ROLLBACK HELPERS
# =====================================================================
def new_idem_key(prefix: str = "op") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"

def idempotent_run(key: str, operation: str, fn):
    """ป้องกันการ commit ซ้ำ — ถ้า key เดิมถูกใช้แล้ว จะคืนผลเดิม (replay) ไม่ทำซ้ำ"""
    if not key:
        key = new_idem_key(operation)
    existing = db.idempotency_keys.find_one({"key": key})
    if existing:
        return existing.get("result"), True
    result = fn()
    try:
        db.idempotency_keys.insert_one({"key": key, "operation": operation, "result": result,
                                        "created": datetime.now(timezone.utc)})
    except pymongo.errors.DuplicateKeyError:
        ex = db.idempotency_keys.find_one({"key": key})
        return (ex.get("result") if ex else result), True
    return result, False

def atomic_decrement(item_id: int, qty: int) -> dict | None:
    """ลดจำนวนแบบ atomic พร้อมเงื่อนไขกันติดลบ และเพิ่ม version กันเขียนทับ"""
    return db.items.find_one_and_update(
        {"id": item_id, "quantity": {"$gte": qty}},
        {"$inc": {"quantity": -qty, "version": 1}},
        return_document=pymongo.ReturnDocument.AFTER,
        projection={"_id": 0, "id": 1, "name": 1, "quantity": 1, "orig_quantity": 1, "status": 1}
    )

def atomic_increment(item_id: int, qty: int) -> dict | None:
    return db.items.find_one_and_update(
        {"id": item_id},
        {"$inc": {"quantity": qty, "version": 1}},
        return_document=pymongo.ReturnDocument.AFTER,
        projection={"_id": 0, "id": 1, "name": 1, "quantity": 1}
    )

# =====================================================================
#  ข้อ 7: RATE LIMIT / QUOTA / SESSION LIMITS
# =====================================================================
def rate_limit(key: str, limit: int, window_sec: int) -> bool:
    now = time.time()
    doc = db.rate_limits.find_one({"key": key})
    if not doc or (now - float(doc.get("window_start", 0))) > window_sec:
        db.rate_limits.update_one({"key": key}, {"$set": {"window_start": now, "count": 1}}, upsert=True)
        return True
    if int(doc.get("count", 0)) >= limit:
        return False
    db.rate_limits.update_one({"key": key}, {"$inc": {"count": 1}})
    return True

def quota_used(username: str, category: str, day_str: str) -> int:
    return db.inspections.count_documents({
        "tech_name": username, "category": category,
        "inspection_date": {"$regex": f"^{re.escape(day_str)}"}
    })

def max_rows() -> int:
    try:
        return max(50, min(5000, int(get_settings_val("max_rows_per_page", "500"))))
    except Exception:
        return 500

def max_export_rows() -> int:
    try:
        return max(100, min(50000, int(get_settings_val("max_export_rows", "5000"))))
    except Exception:
        return 5000

# =====================================================================
#  ข้อ 2: PASSWORD HISTORY / REUSE PREVENTION
# =====================================================================
def password_used_before(username: str, plain: str) -> bool:
    hist = db.password_history.find({"username": username}).sort("created", -1).limit(PASSWORD_HISTORY_KEEP)
    for h in hist:
        ok, _ = verify_password(plain, h.get("hash", ""))
        if ok:
            return True
    return False

def store_password_history(username: str, hashed: str):
    try:
        db.password_history.insert_one({"username": username, "hash": hashed,
                                        "created": datetime.now(timezone.utc)})
        db.password_history.delete_many({"username": username, "created": {"$lt": datetime.now(timezone.utc)
                                          - timedelta(days=365)}})
    except Exception:
        pass

def admin_auth_record():
    """ดึงบัญชีผู้ดูแลระบบ (hash) จาก DB; ถ้ายังไม่มี ให้ bootstrap จาก secrets แล้ว hash เก็บทันที"""
    admin_user = secret_get("admin", "username") or env_get("ADMIN_USERNAME", default="admin")
    rec = db.admin_users.find_one({"username": admin_user})
    if rec:
        return rec
    raw = secret_get("admin", "password") or env_get("ADMIN_PASSWORD")
    if raw:
        hashed = hash_password(raw)
        db.admin_users.update_one({"username": admin_user},
            {"$set": {"username": admin_user, "password": hashed, "role": ROLE_ADMIN,
                      "must_change": False, "updated": get_now_str()}}, upsert=True)
        return db.admin_users.find_one({"username": admin_user})
    return None

# =====================================================================
#  get_next_sequence / settings
# =====================================================================
def get_next_sequence(name):
    c = db.counters.find_one_and_update({"_id": name}, {"$inc": {"seq": 1}}, upsert=True,
                                         return_document=pymongo.ReturnDocument.AFTER)
    return c["seq"]

@st.cache_data(ttl=30, show_spinner=False)
def get_settings_val(key, default="1"):
    res = db.settings.find_one({"key": key})
    return res["value"] if res else default

def set_settings_val(key, val):
    db.settings.update_one({"key": key}, {"$set": {"value": str(val)}}, upsert=True)
    get_settings_val.clear()

# =====================================================================
#  IMAGE & DATA HELPERS
# =====================================================================
def compress_image_to_base64(uploaded_file, max_size=(800, 800), quality=80):
    if uploaded_file is None: return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img.draft("RGB", (max_size[0]*2, max_size[1]*2))
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB": img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.BILINEAR)
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        uploaded_file.seek(0)
        return base64.b64encode(uploaded_file.read()).decode("utf-8")

def b64_to_bytes(b64):
    if not b64: return None
    try: return base64.b64decode(b64)
    except Exception: return None

@st.cache_resource(ttl=600, show_spinner=False)
def get_image_store():
    store = {}
    for d in db.items.find({"image": {"$nin": [None, ""]}}, {"_id": 0, "id": 1, "image": 1}):
        b = b64_to_bytes(d.get("image"))
        if b: store[int(d["id"])] = b
    return store

def get_item_image(item_id): return get_image_store().get(int(item_id))

@st.cache_data(ttl=30, show_spinner=False)
def get_items_df():
    df = pd.DataFrame(list(db.items.find({}, {"_id": 0, "image": 0})))
    if not df.empty:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        df['orig_quantity'] = pd.to_numeric(df.get('orig_quantity', df['quantity']), errors='coerce').fillna(0).astype(int)
        df['min_stock'] = pd.to_numeric(df.get('min_stock', 1), errors='coerce').fillna(1).astype(int)
        df['alert_zero'] = pd.to_numeric(df.get('alert_zero', 0), errors='coerce').fillna(0).astype(int)
        df['note'] = df['note'].fillna("") if 'note' in df.columns else ""
    return df

@st.cache_data(ttl=60, show_spinner=False)
def get_tech_users_df():
    return pd.DataFrame(list(db.tech_users.find({}, {"_id": 0})))

@st.cache_data(ttl=15, show_spinner=False)
def get_active_borrows():
    return list(db.transactions.find({"status": "กำลังยืม"},
                                     {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_pending_reqs():
    return list(db.requisition_requests.find({"status": "รออนุมัติ"}, {"_id": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_inspection_count(category, today_str):
    return db.inspections.count_documents({"category": category, "inspection_date": {"$regex": f"^{re.escape(today_str)}"}})

@st.cache_data(ttl=30, show_spinner=False)
def get_tx_history(limit=500):
    lim = min(int(limit), max_rows())
    return list(db.transactions.find({}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1).limit(lim))

@st.cache_data(ttl=600, max_entries=300, show_spinner=False)
def get_tx_image(tx_id):
    d = db.transactions.find_one({"id": tx_id}, {"_id": 0, "borrower_image": 1})
    return b64_to_bytes(d.get("borrower_image")) if d else None

@st.cache_data(ttl=30, show_spinner=False)
def get_inspections_list(limit=1000):
    lim = min(int(limit), max_rows())
    return list(db.inspections.find({}, {"_id": 0, "photos": 0}).sort("id", -1).limit(lim))

@st.cache_data(ttl=600, max_entries=100, show_spinner=False)
def get_inspection_photos(insp_id):
    doc = db.inspections.find_one({"id": insp_id}, {"_id": 0, "photos": 1})
    raw = doc.get("photos") if doc else None
    if not raw or not str(raw).strip(): return []
    return [b for b in (b64_to_bytes(p) for p in str(raw).split("|||")) if b]

@st.cache_data(ttl=30, show_spinner=False)
def get_req_history(limit=300):
    lim = min(int(limit), max_rows())
    return list(db.requisition_requests.find({"status": {"$ne": "รออนุมัติ"}}, {"_id": 0}).sort("id", -1).limit(lim))

@st.cache_data(ttl=30, show_spinner=False)
def get_my_reqs(username):
    return list(db.requisition_requests.find({"tech_name": username}, {"_id": 0}).sort("id", -1).limit(200))

def refresh_items(images=False):
    get_items_df.clear()
    if images: get_image_store.clear()

def done(msg, icon="✅"):
    st.session_state["_flash"] = (msg, icon); st.rerun()

def close_quick_edit():
    st.session_state.pop("quick_edit_id", None)
    st.session_state.items_tbl_ver = st.session_state.get("items_tbl_ver", 0) + 1

def nz(v): return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
def esc(t): return _html.escape(str(t))
def keyed_container(key, **kw):
    try: return st.container(key=key, **kw)
    except TypeError: return st.container(**kw)

fragment = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None) or (lambda f: f)

def parse_tech_txt_content(text_content):
    out, u, p = [], None, None
    for line in text_content.splitlines():
        s = line.strip()
        if not s: continue
        if "username" in s:
            m = re.search(r'["\']([^"\']+)["\']', s)
            if m: u = m.group(1)
        elif "password" in s:
            m = re.search(r'["\']([^"\']+)["\']', s)
            if m: p = m.group(1)
        if u and p:
            out.append((u, p)); u = p = None
    return out

# =====================================================================
#  ข้อ 5: EXPORT HELPERS (Excel + CSV)
# =====================================================================
def export_buttons(df: pd.DataFrame, base_name: str, key_prefix: str = "exp"):
    if df is None or df.empty:
        st.info("ไม่มีข้อมูลให้ส่งออก")
        return
    cap = max_export_rows()
    shown = df.head(cap)
    if len(df) > cap:
        st.warning(f"⚠️ ข้อมูลมี {len(df):,} แถว — ส่งออกเฉพาะ {cap:,} แถวแรก (ตั้งค่าได้ที่ ⚙️ ตั้งค่าระบบ)")
    stamp = get_now_str("%Y%m%d_%H%M")
    csv_bytes = shown.to_csv(index=False).encode("utf-8-sig")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ CSV", data=csv_bytes, file_name=f"{base_name}_{stamp}.csv",
                           mime="text/csv", key=f"{key_prefix}_csv", use_container_width=True)
    with c2:
        if openpyxl:
            buf = io.BytesIO()
            try:
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    shown.to_excel(w, index=False, sheet_name="ข้อมูล")
                st.download_button("⬇️ Excel", data=buf.getvalue(), file_name=f"{base_name}_{stamp}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key=f"{key_prefix}_xlsx", use_container_width=True)
            except Exception as e:
                st.error(f"สร้างไฟล์ Excel ไม่สำเร็จ: {e}")
        else:
            st.caption("ติดตั้ง `openpyxl` เพื่อเปิดใช้การส่งออก Excel")

# =====================================================================
#  IoT ENGINE (CentralIoTManager)
# =====================================================================
def send_line_push(message_text, token=None, group_id=None):
    if requests is None: return False, "requests library not installed"
    cfg = get_iot_config()
    tk = token or cfg["line_token"]; gid = group_id or cfg["line_group_id"]
    if not tk or not gid: return False, "Missing LINE Token or Group ID"
    try:
        r = requests.post("https://api.line.me/v2/bot/message/push",
            headers={"Content-Type": "application/json; charset=UTF-8", "Authorization": f"Bearer {tk}"},
            json={"to": gid, "messages": [{"type": "text", "text": message_text}]}, timeout=6)
        return (200 <= r.status_code < 300), f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

class CentralIoTManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.connected = False; self.last_connect_err = ""; self.client = None
        self.servo_status = "DOWN"; self.servo_last_update = "--:--:--"
        self.water_status = {"A":"NORMAL","B":"NORMAL","C":"NORMAL","D":"NORMAL","UNDERGROUND":"NORMAL"}
        self.water_online = {"A":True,"B":True,"C":True,"D":True,"UNDERGROUND":True}
        self.water_last_msg = "พร้อมทำงาน (Ready)"
        self.fire_status = "CLEAR"; self.fire_location = "- (ระบบปกติ)"
        self.fire_zones = {"A":"NORMAL","B":"NORMAL","C":"NORMAL","D":"NORMAL","CLUB":"NORMAL","LIBRARY":"NORMAL","ST":"NORMAL","UNKNOWN":"NORMAL"}
        self.raw_mqtt_feed = []

    def add_feed(self, topic, msg):
        with self.lock:
            self.raw_mqtt_feed.insert(0, {"datetime": get_now_str("%Y-%m-%d %H:%M:%S"), "topic": topic, "message": msg})
            if len(self.raw_mqtt_feed) > 150: self.raw_mqtt_feed.pop()

    def log_to_db(self, system_name, location, status, raw_msg=""):
        try:
            db.iot_logs.insert_one({"datetime": get_now_str("%Y-%m-%d %H:%M:%S"), "system": system_name,
                                     "location": location, "status": status, "raw": raw_msg})
        except Exception: pass

    def handle_message(self, topic, payload_str):
        msg = payload_str.strip(); msg_up = msg.upper(); t_low = topic.lower()
        self.add_feed(topic, msg)
        if topic in ["esp8266/servo", "esp8266/servo/status"]:
            if msg_up in ["UP", "DOWN"]:
                with self.lock:
                    self.servo_status = msg_up; self.servo_last_update = get_now_str("%H:%M:%S")
                if topic.endswith("status"): self.log_to_db("SERVO", "Drawer Servo D4", msg_up, msg)
            return
        if t_low == "water alarm" or t_low.startswith("water alarm/status/"):
            with self.lock: self.water_last_msg = msg
            if t_low.startswith("water alarm/status/"):
                sub = topic.split("/")[-1].upper()
                key = "UNDERGROUND" if "UNDERGROUND" in sub else sub.replace("TRANSFERPUMP", "").strip()
                if key in self.water_status and msg_up in ["ALARM", "NORMAL"]:
                    with self.lock:
                        prev = self.water_status[key]; self.water_status[key] = msg_up; self.water_online[key] = True
                    if prev != msg_up: self.log_to_db("WATER", key, msg_up, msg)
                return
            for prefix, k in [("TRANSFERPUMPA","A"),("TRANSFERPUMPB","B"),("TRANSFERPUMPC","C"),
                              ("TRANSFERPUMPD","D"),("UNDERGROUND PUMP","UNDERGROUND")]:
                if prefix in msg_up:
                    with self.lock:
                        if "OFFLINE" in msg_up: self.water_online[k] = False
                        elif "ONLINE" in msg_up: self.water_online[k] = True
                        else:
                            self.water_online[k] = True
                            new_st = "NORMAL" if "NORMAL" in msg_up else "ALARM"
                            prev = self.water_status.get(k, "NORMAL"); self.water_status[k] = new_st
                            if prev != new_st: self.log_to_db("WATER", k, new_st, msg)
                    break
            return
        if "fire" in t_low:
            if any(w in msg_up for w in ["RESET","CLEAR","NORMAL"]) or "สถานะปกติ" in msg:
                with self.lock:
                    self.fire_status = "CLEAR"; self.fire_location = "- (ระบบปกติ)"
                    for zk in self.fire_zones: self.fire_zones[zk] = "NORMAL"
                self.log_to_db("FIRE", msg, "CLEAR", msg)
            else:
                with self.lock:
                    self.fire_status = "ALERT"; self.fire_location = msg
                    matched = False
                    for key, pats in [("A",["อาคาร A","BUILDING A","BLDGA"]),("B",["อาคาร B","BUILDING B","BLDGB"]),
                                      ("C",["อาคาร C","BUILDING C","BLDGC"]),("D",["อาคาร D","BUILDING D","BLDGD"]),
                                      ("CLUB",["สโมสร","CLUB","PAVILION"]),("LIBRARY",["ห้องสมุด","LIBRARY"]),
                                      ("ST",["ST","บันไดหนีไฟ"])]:
                        if any(p in msg_up for p in pats): self.fire_zones[key] = "ALERT"; matched = True
                    if not matched: self.fire_zones["UNKNOWN"] = "ALERT"
                self.log_to_db("FIRE", msg, "ALERT", msg)

    def connect(self):
        if mqtt is None:
            self.last_connect_err = "ยังไม่ได้ติดตั้ง paho-mqtt"; return False
        cfg = get_iot_config()
        if not cfg.get("_has_mqtt"):
            self.last_connect_err = "ไม่พบ MQTT Credential (ตั้งใน st.secrets หรือ env)"; return False
        try:
            if self.client:
                try: self.client.loop_stop(); self.client.disconnect()
                except Exception: pass
            cid = f"KaveAdmin_{secrets.token_hex(4)}"
            try: client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
            except AttributeError: client = mqtt.Client(client_id=cid)
            client.username_pw_set(cfg["mqtt_user"], cfg["mqtt_pass"])
            client.tls_set(cert_reqs=ssl.CERT_NONE); client.tls_insecure_set(True)

            def on_connect(c, ud, fl, rc):
                if rc == 0:
                    self.connected = True; self.last_connect_err = ""
                    c.subscribe([(cfg["topic_servo_cmd"],0),(cfg["topic_servo_status"],0),
                                 (cfg["topic_water"],0),("Water alarm/status/#",0),
                                 (cfg["topic_check_clients"],0),(cfg["topic_fire"],0),
                                 ("firealarm",0),("FireAlarm",0),("fire_alarm",0),(cfg["topic_fire_relay"],0)])
                else:
                    self.connected = False; self.last_connect_err = f"MQTT rc={rc}"
            def on_disconnect(c, ud, rc): self.connected = False
            def on_message(c, ud, msg):
                try: self.handle_message(msg.topic, msg.payload.decode("utf-8", errors="ignore"))
                except Exception: pass

            client.on_connect = on_connect; client.on_disconnect = on_disconnect; client.on_message = on_message
            client.connect_async(cfg["mqtt_server"], int(cfg["mqtt_port"]), keepalive=30)
            client.loop_start(); self.client = client
            return True
        except Exception as e:
            self.connected = False; self.last_connect_err = str(e); return False

    def publish(self, topic, payload, retain=False):
        cooldown = int(get_settings_val("iot_cooldown_sec", "3") or 3)
        if not rate_limit(f"iot_pub:{st.session_state.get('username','anon')}", 20, 60):
            return False, "ส่งคำสั่งถี่เกินไป (จำกัด 20 คำสั่ง/นาที)"
        if not self.client or not self.connected:
            self.connect(); time.sleep(0.4)
        if self.client:
            try:
                self.client.publish(topic, str(payload), retain=retain)
                self.handle_message(topic, str(payload))
                time.sleep(0.05)
                return True, "OK"
            except Exception as e:
                self.last_connect_err = str(e); return False, str(e)
        return False, "ไม่ได้เชื่อมต่อ MQTT"

@st.cache_resource
def get_iot_manager():
    mgr = CentralIoTManager(); mgr.connect(); return mgr

iot_mgr = get_iot_manager()

# =====================================================================
#  GROWATT
# =====================================================================
def growatt_md5(p):
    m = hashlib.md5(p.encode("utf-8")).hexdigest(); ch = list(m)
    for i in range(0, len(ch), 2):
        if ch[i] == '0': ch[i] = 'c'
    return "".join(ch)

def _find_key_ci(node, target):
    tl = target.lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() == tl and v is not None and not isinstance(v, (dict, list)): return v
        for v in node.values():
            r = _find_key_ci(v, target)
            if r is not None: return r
    elif isinstance(node, list):
        for it in node:
            r = _find_key_ci(it, target)
            if r is not None: return r
    return None

def _find_obj_by_sn(node, sn):
    sl = str(sn).strip().lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("sn","devicesn","storagesn","serialnum") and isinstance(v, str) and v.strip().lower() == sl:
                return node
        for v in node.values():
            r = _find_obj_by_sn(v, sn)
            if r is not None: return r
    elif isinstance(node, list):
        for it in node:
            r = _find_obj_by_sn(it, sn)
            if r is not None: return r
    return None

def _spf_scope(j, sn):
    d = _find_obj_by_sn(j, sn)
    if d is not None and (_find_key_ci(d, "vBat") is not None or _find_key_ci(d, "soc") is not None): return d
    return j

def _get_f(node, keys):
    for k in keys:
        v = _find_key_ci(node, k)
        if v is not None:
            try: return float(str(v).strip())
            except Exception: pass
    return None

def fetch_growatt_realtime(sync_sheets=False):
    if requests is None: return {"ok": False, "error": "requests library not installed"}
    cfg = get_iot_config()
    if not cfg.get("_has_growatt"):
        return {"ok": False, "error": "ไม่พบ Growatt Credential (ตั้งใน st.secrets หรือ env)"}
    hosts = ["server.growatt.com", "server-api.growatt.com", "openapi.growatt.com"]
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    pwd = growatt_md5(cfg["growatt_pass"]); sn = cfg["growatt_sn"]
    sess = requests.Session(); sess.headers.update({"User-Agent": ua, "X-Requested-With": "XMLHttpRequest"})
    host = ""; plant_id = ""; err = ""
    for h in hosts:
        try:
            r = sess.post(f"https://{h}/newTwoLoginAPI.do",
                data={"userName": cfg["growatt_user"], "password": pwd},
                headers={"Origin": f"https://{h}", "Referer": f"https://{h}/login"}, timeout=12)
            if r.status_code == 200:
                j = r.json()
                if j.get("back", {}).get("success"):
                    host = h
                    da = j.get("back", {}).get("data", [])
                    if da and isinstance(da, list): plant_id = str(da[0].get("plantId", ""))
                    break
                err = f"Login failed on {h}"
            else: err = f"HTTP {r.status_code} on {h}"
        except Exception as e: err = str(e)
    if not host: return {"ok": False, "error": err or "Cannot login to Growatt"}
    eps = [("GET", f"https://{host}/newStorageAPI.do?op=getStorageParams_sacolar&storageId={sn}", None),
           ("GET", f"https://{host}/newStorageAPI.do?op=getStorageInfo_sacolar&storageId={sn}", None),
           ("POST", f"https://{host}/newStorageAPI.do?op=getStorageParams_sacolar", {"storageId": sn}),
           ("POST", f"https://{host}/newStorageAPI.do?op=getStorageInfo_sacolar", {"storageId": sn}),
           ("GET", f"https://{host}/newTwoPlantAPI.do?op=getAllDeviceList&plantId={plant_id}&language=1&currPage=1", None)]
    for method, url, body in eps:
        try:
            r = sess.post(url, data=body, timeout=12) if method == "POST" else sess.get(url, timeout=12)
            if r.status_code != 200: continue
            j = _spf_scope(r.json(), sn)
            vBat = _get_f(j, ["vBat","vBattery","vbatSys","vAkku"]); soc = _get_f(j, ["capacity","soc","batterySoc"])
            if soc is not None and not (0 <= soc <= 100): soc = None
            if vBat is None and soc is None: continue
            pvV = _get_f(j, ["vPv1","vPv","pvVoltage"]) or 0.0; pvP = _get_f(j, ["ppv1","pPv1","ppv","pvPower","pCharge1"]) or 0.0
            load = _get_f(j, ["outPutPower","pLoad","pLocalLoad","loadPower","activePower"]) or 0.0
            loadPct = _get_f(j, ["loadPercent"]) or 0.0; gridP = _get_f(j, ["pAcInPut"]) or 0.0
            gridV = _get_f(j, ["vGrid"]) or 0.0; invT = _get_f(j, ["invTemperature"]) or 0.0
            pch = _get_f(j, ["pCharge"]) or 0.0; pdis = _get_f(j, ["pDischarge"]) or 0.0
            iChg = _get_f(j, ["iChargePV1","iCharge1","icharge1"])
            vBat = vBat or 0.0; soc = soc or 0.0
            pvI = iChg if (iChg and iChg > 0) else (pvP/vBat if (pvP>0 and vBat>10) else (pvP/pvV if (pvP>0 and pvV>1) else 0.0))
            batMode, batP = ("DISCHARGING", pdis) if pdis > .5 else (("CHARGING", pch) if pch > .5 else ("IDLE", 0.0))
            res = {"ok": True, "host": host, "updated": get_now_str("%Y-%m-%d %H:%M:%S"),
                   "vBat": round(vBat,1), "soc": round(soc,0), "pvV": round(pvV,1), "pvI": round(pvI,1),
                   "pvP": round(pvP,0), "load": round(load,0), "loadPct": round(loadPct,1),
                   "gridP": round(gridP,0), "gridV": round(gridV,0), "invTemp": round(invT,1),
                   "batMode": batMode, "batP": round(batP,0)}
            try:
                db.iot_logs.insert_one({"datetime": res["updated"], "system": "SOLAR", "location": sn,
                                        "status": batMode, "data": res})
            except Exception: pass
            if sync_sheets and cfg.get("google_webapp_url"):
                try:
                    requests.post(cfg["google_webapp_url"], json={"vBat":res["vBat"],"soc":res["soc"],
                        "pvP":res["pvP"],"pvI":res["pvI"],"load":res["load"]}, timeout=10)
                    res["sheets_synced"] = True
                except Exception as ex:
                    res["sheets_synced"] = False; res["sheets_err"] = str(ex)
            return res
        except Exception as e: err = str(e)
    return {"ok": False, "error": err or "No SPF5000ES data found"}

# =====================================================================
#  SESSION / LOGIN (ข้อ 1 + 7)
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False; st.session_state.role = None
    st.session_state.username = ""; st.session_state.original_role = None; st.session_state.token = None

LS_KEY = "inv_token"
local_store = LocalStorage() if LocalStorage is not None else None
saved_token = None
if local_store is not None:
    try: saved_token = local_store.getItem(LS_KEY)
    except Exception: saved_token = None

# ข้อ 1: ไม่อ่าน token จาก URL (กันรั่วผ่าน referrer/log) + ล้าง query param ทิ้ง
try:
    if "token" in st.query_params:
        st.query_params.clear()
except Exception:
    pass

def get_session_doc(token: str):
    if not token: return None
    return db.sessions.find_one({"token_hash": sha256_hex(token)})

if not st.session_state.logged_in and saved_token:
    sess = get_session_doc(saved_token)
    if sess and sess.get("role"):
        idle = int(get_settings_val("session_idle_minutes", "30") or 30)
        last_seen = sess.get("last_seen") or sess.get("created")
        if isinstance(last_seen, datetime):
            if (datetime.now(timezone.utc) - last_seen) > timedelta(minutes=idle):
                db.sessions.delete_one({"_id": sess["_id"]})
            else:
                st.session_state.logged_in = True; st.session_state.role = sess["role"]
                st.session_state.username = sess["username"]; st.session_state.token = saved_token
                st.session_state.original_role = sess.get("original_role")
                db.sessions.update_one({"_id": sess["_id"]}, {"$set": {"last_seen": datetime.now(timezone.utc)}})
        else:
            st.session_state.logged_in = True; st.session_state.role = sess["role"]
            st.session_state.username = sess["username"]; st.session_state.token = saved_token
            st.session_state.original_role = sess.get("original_role")
    else:
        try: local_store.deleteItem(LS_KEY, key="ls_del_token")
        except Exception: pass

_flash = st.session_state.pop("_flash", None)
if _flash: st.toast(_flash[0], icon=_flash[1])

# =====================================================================
#  THEME APPLY
# =====================================================================
theme_name = get_settings_val("ui_theme", list(THEME_PRESETS.keys())[0])
theme = THEME_PRESETS.get(theme_name, THEME_PRESETS[list(THEME_PRESETS.keys())[0]])
accent = get_settings_val("ui_accent", theme["accent"])
density = get_settings_val("ui_density", "ปกติ")
st.markdown(build_css(theme, accent, density), unsafe_allow_html=True)

# =====================================================================
#  LOGIN SCREEN
# =====================================================================
if not st.session_state.logged_in or not st.session_state.role:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown(f"""
        <div class="app-hero" style="margin-top:1.6rem;">
          <div>
            <div class="t">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>
            <div class="s">เข้าสู่ระบบเพื่อตรวจเช็ค ยืม-คืน และบริหารจัดการระบบ</div>
          </div>
          <div class="badge-row"><span class="status-pill-top info">🔐 Secure Login</span></div>
        </div>""", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)

        if submitted:
            # ข้อ 7: จำกัดความถี่การลองรหัสผ่าน
            if not rate_limit(f"login_attempt:{sha256_hex(username.strip().lower())}", 8, 300):
                st.error("❌ ลองเข้าสู่ระบบบ่อยเกินไป กรุณารอ 5 นาทีแล้วลองใหม่")
            else:
                role_val, user_val, upgrade = "", "", False
                admin_rec = admin_auth_record()
                if admin_rec and username.strip() == admin_rec.get("username"):
                    ok, upgrade = verify_password(password, admin_rec.get("password", ""))
                    if ok:
                        role_val, user_val = ROLE_ADMIN, admin_rec["username"]
                if not role_val:
                    tdf = get_tech_users_df()
                    if not tdf.empty:
                        m = tdf[tdf['username'] == username.strip()]
                        if not m.empty:
                            ok, upgrade = verify_password(password, m.iloc[0]['password'])
                            if ok:
                                role_val, user_val = ROLE_TECH, username.strip()
                                if upgrade:
                                    nh = hash_password(password)
                                    db.tech_users.update_one({"username": user_val}, {"$set": {"password": nh}})
                                    store_password_history(user_val, nh)
                if role_val:
                    token = secrets.token_urlsafe(32)
                    db.sessions.insert_one({
                        "token_hash": sha256_hex(token), "username": user_val, "role": role_val,
                        "original_role": role_val if role_val == ROLE_ADMIN else None,
                        "created": datetime.now(timezone.utc), "last_seen": datetime.now(timezone.utc),
                        "ip": "n/a"})
                    st.session_state.logged_in = True; st.session_state.role = role_val
                    st.session_state.username = user_val; st.session_state.token = token
                    st.session_state.original_role = role_val if role_val == ROLE_ADMIN else None
                    if local_store is not None:
                        try: local_store.setItem(LS_KEY, token, key="ls_set_token")
                        except Exception: pass
                    log_audit("LOGIN", user_val, detail=f"เข้าสู่ระบบในฐานะ {role_label(role_val)}")
                    st.success("เข้าสู่ระบบสำเร็จ!"); st.rerun()
                else:
                    log_audit("LOGIN_FAIL", username.strip(), detail="เข้าสู่ระบบไม่สำเร็จ", ok=False)
                    st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# ข้อ 7: Idle timeout
_idle = int(get_settings_val("session_idle_minutes", "30") or 30)
_now = datetime.now(timezone.utc)
_last = st.session_state.get("_last_seen_dt")
if _last and (_now - _last) > timedelta(minutes=_idle):
    log_audit("SESSION_TIMEOUT", st.session_state.username, detail="หมดเวลาไม่มีการใช้งาน ระบบออกอัตโนมัติ")
    if st.session_state.get("token"):
        db.sessions.delete_one({"token_hash": sha256_hex(st.session_state["token"])})
    try: local_store.deleteItem(LS_KEY, key="ls_del_token")
    except Exception: pass
    st.session_state.clear(); st.session_state.logged_in = False
    st.warning(f"⏱️ หมดเวลาไม่มีการใช้งาน ({_idle} นาที) กรุณาเข้าสู่ระบบใหม่"); st.rerun()
st.session_state._last_seen_dt = _now
if st.session_state.get("token"):
    db.sessions.update_one({"token_hash": sha256_hex(st.session_state["token"])},
                            {"$set": {"last_seen": _now}})

# =====================================================================
#  DATA FETCH
# =====================================================================
low_stock_limit = int(get_settings_val('low_stock_threshold', '1'))
items_df = get_items_df()
item_name_map = dict(zip(items_df['id'], items_df['name'])) if not items_df.empty else {}
active_borrows = get_active_borrows()
borrowed_item_map, borrower_details_map = {}, {}
for t in active_borrows:
    iid = t["item_id"]; qb = t.get("quantity", 1)
    borrowed_item_map[iid] = borrowed_item_map.get(iid, 0) + qb
    borrower_details_map.setdefault(iid, []).append(f"{t.get('borrower_name')} ({qb} ชิ้น)")

is_tech_view = st.session_state.role in TECH_ROLES
abn_statuses = ['ชำรุด', 'อุปกรณ์หมด'] if is_tech_view else ['ชำรุด', 'สูญหาย', 'อุปกรณ์หมด']
abn_label = "ชำรุด / กำลังใช้งาน / หมด"; abn_title = "อุปกรณ์ชำรุด/กำลังใช้งาน/หมด"
if not items_df.empty:
    abnormal_items = items_df[items_df['status'].isin(abn_statuses) |
                              items_df['status'].str.contains('กำลังใช้งาน', na=False)]
    low_stock_items = items_df[(items_df['subcategory'] != 'เครื่องมือช่าง') &
                               (items_df['quantity'] <= items_df['min_stock'].where(items_df['min_stock'] > 1, low_stock_limit))]
else:
    abnormal_items = pd.DataFrame(); low_stock_items = pd.DataFrame()
borrowed_cnt = len(active_borrows); abn_cnt = len(abnormal_items); low_cnt = len(low_stock_items)
pending_reqs_all = get_pending_reqs()

# =====================================================================
#  SIDEBAR
# =====================================================================
def show_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="brand-box">
          <div class="brand-logo">K</div>
          <div><div class="brand-title">KAVE TOWN SHIFT</div><div class="brand-sub">Central Command System</div></div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="user-card">
          <div class="avatar">{(st.session_state.username or 'U')[0].upper()}</div>
          <div><div class="u-name">{esc(st.session_state.username)}</div>
               <div class="u-role">{esc(role_label(st.session_state.role))}</div></div>
        </div>""", unsafe_allow_html=True)

        nav = []
        if has_perm("dashboard"): nav.append("📊 ภาพรวมระบบ")
        if has_perm("inventory"): nav.append("🛠️ คลังอุปกรณ์")
        if has_perm("requisition"): nav.append("📦 คำขอเพิ่มสต็อก")
        if has_perm("borrow"): nav.append("🔄 ยืม-คืนอุปกรณ์")
        if has_perm("iot"): nav.append("🗄️ ควบคุมลิ้นชัก")
        if has_perm("iot"): nav.append("💧 Water Alarm")
        if has_perm("iot"): nav.append("🚨 Fire Alarm")
        if has_perm("solar"): nav.append("☀️ ระบบโซล่าเซลล์")
        if has_perm("audit"): nav.append("🔍 ค้นหา & ประวัติ")
        if has_perm("settings"): nav.append("⚙️ ตั้งค่าระบบ & บัญชี")

        page = st.radio("เมนูหลัก", nav, label_visibility="collapsed") if nav else None

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 รีเฟรช", use_container_width=True):
                st.cache_data.clear(); get_image_store.clear(); st.rerun()
        with c2:
            if st.button("🚪 ออกจากระบบ", type="primary", use_container_width=True):
                if st.session_state.get("token"):
                    db.sessions.delete_one({"token_hash": sha256_hex(st.session_state["token"])})
                log_audit("LOGOUT", st.session_state.username)
                try: local_store.deleteItem(LS_KEY, key="ls_del_token")
                except Exception: pass
                st.session_state.clear(); st.session_state.logged_in = False
                st.rerun()
    return page

# =====================================================================
#  SHARED COMPONENTS
# =====================================================================
def render_borrow_return_system():
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sb, sr, sh = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])

    with sb:
        av = items_df[items_df['quantity'] > 0] if not items_df.empty else pd.DataFrame()
        if not av.empty:
            with st.form("borrow_form_shared", clear_on_submit=True):
                idem_key = st.session_state.setdefault("_idem_borrow", new_idem_key("borrow"))
                idict = {f"{r['name']} (คงเหลือ: {r['quantity']} ชิ้น)": r['id'] for _, r in av.iterrows()}
                sel = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(idict.keys()))
                bqty = st.number_input("จำนวนที่ต้องการยืม *", min_value=1,
                                       max_value=int(av['quantity'].max()), value=1)
                bname = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                bimg = st.file_uploader("แนบรูปถ่ายผู้ยืม (ถ้ามี)", type=["jpg","jpeg","png"])
                st.info(f"📌 ผู้บันทึก: **{st.session_state.username}**")
                if st.form_submit_button("ยืนยันการยืมอุปกรณ์", type="primary"):
                    if not bname.strip():
                        st.error("❌ กรุณากรอกชื่อผู้ยืม")
                    elif not rate_limit(f"borrow:{st.session_state.username}", 30, 300):
                        st.error("❌ ทำรายการถี่เกินไป กรุณารอสักครู่")
                    else:
                        sid = idict[sel]
                        def _do_borrow():
                            # ข้อ 4: atomic decrement + compensation rollback
                            upd = atomic_decrement(int(sid), int(bqty))
                            if not upd:
                                return {"ok": False, "msg": "จำนวนคงเหลือไม่พอ หรือมีการเปลี่ยนแปลงพร้อมกัน"}
                            try:
                                txid = get_next_sequence("transactions_id")
                                db.transactions.insert_one({
                                    "id": txid, "item_id": sid, "borrower_name": bname.strip(),
                                    "borrow_date": get_now_str("%Y-%m-%d %H:%M"), "return_date": None,
                                    "status": "กำลังยืม", "borrower_image": compress_image_to_base64(bimg),
                                    "quantity": int(bqty), "giver_name": st.session_state.username,
                                    "receiver_name": None, "return_image": None,
                                    "idem_key": idem_key})
                                if upd["quantity"] == 0:
                                    db.items.update_one({"id": sid}, {"$set": {"status": "ยืม"}})
                                return {"ok": True, "msg": f"บันทึกการยืม {upd['name']} จำนวน {bqty} ชิ้น เรียบร้อยแล้ว", "txid": txid}
                            except Exception as e:
                                atomic_increment(int(sid), int(bqty))   # rollback
                                return {"ok": False, "msg": f"บันทึกไม่สำเร็จ ยกเลิกการยืมแล้วคืนจำนวน: {e}"}
                        res, replayed = idempotent_run(idem_key, "BORROW", _do_borrow)
                        refresh_items(); get_active_borrows.clear(); get_tx_history.clear()
                        if res.get("ok"):
                            log_audit("BORROW", item_name_map.get(sid, sid), after_val=f"ยืม {bqty} ชิ้น",
                                      detail=f"ผู้ยืม: {bname.strip()}{' (replay)' if replayed else ''}")
                            st.session_state._idem_borrow = new_idem_key("borrow")
                            done(res["msg"])
                        else:
                            log_audit("BORROW_FAIL", item_name_map.get(sid, sid), detail=res.get("msg"), ok=False)
                            st.error("❌ " + res.get("msg", "เกิดข้อผิดพลาด"))
        else:
            st.info("ไม่มีอุปกรณ์ที่มีจำนวนคงเหลือให้ยืมในขณะนี้")

    with sr:
        st.markdown("#### รายการที่กำลังถูกยืมอยู่")
        ats = get_active_borrows()
        if ats:
            for t in ats:
                iname = item_name_map.get(t["item_id"], "Unknown")
                with st.expander(f"📦 {iname} ({t.get('quantity',1)} ชิ้น) | ผู้ยืม: {t.get('borrower_name')}"):
                    with st.form(key=f"return_form_{t['id']}"):
                        rimg = st.file_uploader("รูปถ่ายตอนคืน (ถ้ามี)", type=["jpg","jpeg","png"], key=f"ret_img_{t['id']}")
                        if st.form_submit_button("✅ รับคืนอุปกรณ์รายการนี้", type="primary"):
                            key = f"return_{t['id']}"
                            def _do_return():
                                q = int(t.get('quantity', 1))
                                try:
                                    db.transactions.update_one({"id": t['id'], "status": "กำลังยืม"},
                                        {"$set": {"return_date": get_now_str("%Y-%m-%d %H:%M"), "status": "คืนแล้ว",
                                                  "receiver_name": st.session_state.username,
                                                  "return_image": compress_image_to_base64(rimg)}})
                                    atomic_increment(int(t["item_id"]), q)
                                    db.items.update_one({"id": t["item_id"]}, {"$set": {"status": "ปกติ"}})
                                    return {"ok": True, "msg": f"รับคืน {iname} จำนวน {q} ชิ้น เรียบร้อยแล้ว"}
                                except Exception as e:
                                    return {"ok": False, "msg": str(e)}
                            res, replayed = idempotent_run(key, "RETURN", _do_return)
                            refresh_items(); get_active_borrows.clear(); get_tx_history.clear()
                            if res.get("ok"):
                                log_audit("RETURN", iname, after_val=f"คืน {t.get('quantity',1)} ชิ้น",
                                          detail=f"ผู้รับคืน: {st.session_state.username}")
                                done(res["msg"])
                            else:
                                st.error("❌ " + res.get("msg", "เกิดข้อผิดพลาด"))
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืม")

    with sh:
        st.markdown("#### 📜 ประวัติการยืม-คืน")
        all_t = get_tx_history()
        tx_df = pd.DataFrame([{"รหัส": t["id"], "ชื่ออุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
                               "จำนวน": t.get("quantity",1), "ผู้ยืม": t.get("borrower_name"),
                               "ผู้ให้ยืม": t.get("giver_name"), "ผู้รับคืน": t.get("receiver_name"),
                               "วันที่ยืม": t.get("borrow_date"), "วันที่คืน": t.get("return_date"),
                               "สถานะ": t.get("status")} for t in all_t])
        st.dataframe(tx_df, use_container_width=True, hide_index=True)
        if has_perm("export"): export_buttons(tx_df, "ประวัติยืมคืน", "tx")

# =====================================================================
#  PAGES
# =====================================================================
def page_overview():
    st.markdown('<div class="app-hero"><div><div class="t">📊 ภาพรวมระบบ</div><div class="s">ภาพรวมทั้งหมดในจุดเดียว</div></div></div>', unsafe_allow_html=True)
    k = [("อุปกรณ์ทั้งหมด", len(items_df), "🛠️", "#fff"), ("ผิดปกติ", abn_cnt, "⚠️", "#F87171" if abn_cnt else "#34D399"),
         ("กำลังถูกยืม", borrowed_cnt, "📤", "#38BDF8"), ("ใกล้หมด", low_cnt, "📉", "#FBBF24" if low_cnt else "#34D399"),
         ("คำขอรออนุมัติ", len(pending_reqs_all), "📥", "#FBBF24")]
    cols = st.columns(len(k))
    for c, (l, v, i, col) in zip(cols, k):
        c.markdown(f'<div class="glass-kpi"><div class="top"><span class="lbl">{l}</span><span class="ic-badge">{i}</span></div>'
                   f'<div class="val" style="color:{col} !important;">{v}</div></div>')
    if has_perm("borrow"): render_borrow_return_system()

def page_inventory():
    st.markdown('<div class="app-hero"><div><div class="t">🛠️ คลังอุปกรณ์ช่าง & สระว่ายน้ำ</div></div></div>', unsafe_allow_html=True)
    if items_df.empty:
        st.info("ยังไม่มีข้อมูลอุปกรณ์"); return
    q = st.text_input("🔍 ค้นหาชื่ออุปกรณ์", key="inv_search")
    c1, c2, c3 = st.columns([1,1,1])
    cf = c1.selectbox("หมวด", ["ทั้งหมด","อุปกรณ์ช่าง","อุปกรณ์สระว่ายน้ำ"])
    sf = c2.selectbox("สถานะ", ["ทั้งหมด","ปกติ","ชำรุด","สูญหาย","ยืม","อุปกรณ์หมด"])
    sbf = c3.selectbox("หมวดย่อย", ["ทั้งหมด","เครื่องมือช่าง","อุปกรณ์ช่างทั่วไป","เคมีภัณฑ์"])
    df = items_df.copy()
    if q.strip(): df = df[df['name'].str.contains(q.strip(), case=False, na=False)]
    if cf != "ทั้งหมด": df = df[df['category'] == cf]
    if sf != "ทั้งหมด": df = df[df['status'] == sf]
    if sbf != "ทั้งหมด": df = df[df['subcategory'] == sbf]
    st.caption(f"แสดง {len(df)} จาก {len(items_df)} รายการ")
    st.dataframe(df[['id','name','category','subcategory','quantity','orig_quantity','status','min_stock','note']],
                 use_container_width=True, hide_index=True)
    if has_perm("export"): export_buttons(df, "รายการอุปกรณ์", "inv")

def page_requisition():
    st.markdown('<div class="app-hero"><div><div class="t">📦 คำขอเพิ่มสต็อก</div></div></div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["📤 ส่งคำขอ", "📥 รายการรออนุมัติ"])
    with t1:
        tdf = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['subcategory'] == 'อุปกรณ์ช่างทั่วไป')
                       | (items_df['category'] == 'อุปกรณ์สระว่ายน้ำ')] if not items_df.empty else pd.DataFrame()
        if tdf.empty:
            st.info("ไม่พบรายการ"); return
        with st.form("req_form", clear_on_submit=True):
            idict = {f"{r['name']} (คงเหลือ: {r['quantity']})": r['id'] for _, r in tdf.iterrows()}
            sel = st.selectbox("เลือกอุปกรณ์ *", list(idict.keys()))
            qty = st.number_input("จำนวนที่ต้องการเพิ่ม *", min_value=1, value=1)
            note = st.text_area("เหตุผล *")
            if st.form_submit_button("📤 ส่งคำขอ", type="primary"):
                if not note.strip(): st.error("กรุณาระบุเหตุผล")
                elif not rate_limit(f"req:{st.session_state.username}", 20, 300):
                    st.error("ส่งคำขอถี่เกินไป")
                else:
                    sid = idict[sel]
                    db.requisition_requests.insert_one({"id": get_next_sequence("requisition_requests_id"),
                        "tech_name": st.session_state.username, "item_id": sid, "quantity": int(qty),
                        "note": note.strip(), "status": "รออนุมัติ", "request_date": get_now_str("%Y-%m-%d %H:%M"),
                        "approval_date": None})
                    log_audit("REQUISITION", item_name_map.get(sid, sid), after_val=f"ขอเพิ่ม {qty} ชิ้น")
                    get_pending_reqs.clear(); done("ส่งคำขอเรียบร้อยแล้ว")
    with t2:
        if has_perm("approve"):
            reqs = get_pending_reqs()
            for r in reqs:
                with st.container():
                    st.write(f"**#{r['id']}** | {r.get('tech_name')} | {item_name_map.get(r['item_id'],'?')} | +{r.get('quantity')} ชิ้น")
                    st.caption(r.get("note", ""))
                    cA, cB = st.columns(2)
                    with cA:
                        if st.button("✅ อนุมัติ", key=f"ap_{r['id']}"):
                            res = db.requisition_requests.update_one({"id": r['id'], "status": "รออนุมัติ"},
                                {"$set": {"status": "อนุมัติ", "approval_date": get_now_str()}})
                            if res.modified_count:
                                db.items.update_one({"id": r['item_id']},
                                    {"$inc": {"quantity": int(r['quantity']), "orig_quantity": int(r['quantity']), "version": 1},
                                     "$set": {"status": "ปกติ"}})
                            log_audit("REQ_APPROVE", item_name_map.get(r['item_id'], r['item_id']), after_val=f"+{r.get('quantity')}")
                            refresh_items(); get_pending_reqs.clear(); done("อนุมัติแล้ว")
                    with cB:
                        if st.button("❌ ไม่อนุมัติ", key=f"rj_{r['id']}"):
                            db.requisition_requests.update_one({"id": r['id'], "status": "รออนุมัติ"},
                                {"$set": {"status": "ไม่อนุมัติ", "approval_date": get_now_str()}})
                            log_audit("REQ_REJECT", item_name_map.get(r['item_id'], r['item_id']))
                            get_pending_reqs.clear(); done("ปฏิเสธคำขอแล้ว", icon="⚠️")
        else:
            my = get_my_reqs(st.session_state.username)
            st.dataframe(pd.DataFrame([{"รหัส": r["id"], "อุปกรณ์": item_name_map.get(r["item_id"],"?"),
                "จำนวน": r.get("quantity"), "หมายเหตุ": r.get("note"), "วันที่ขอ": r.get("request_date"),
                "สถานะ": r.get("status")} for r in my]), use_container_width=True, hide_index=True)

def page_iot_drawer():
    st.markdown('<div class="app-hero"><div><div class="t">🗄️ ควบคุมลิ้นชัก (Drawer Servo)</div></div></div>', unsafe_allow_html=True)
    cfg = get_iot_config()
    if not cfg.get("_has_mqtt"):
        st.warning(f"⚠️ {cfg.get('_error', 'ไม่พบ MQTT Credential')}")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f'<div class="iot-card"><div class="hd">สถานะ Servo</div><div class="bd"><span class="nm">Drawer D4</span>'
                    f'<span class="pill {"pill-normal" if iot_mgr.servo_status=="UP" else "pill-alarm"}">{iot_mgr.servo_status}</span></div>'
                    f'<div class="u-role" style="margin-top:.3rem;">อัปเดต {iot_mgr.servo_last_update}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="iot-card"><div class="hd">MQTT Connection</div><div class="bd"><span class="nm">Broker</span>'
                    f'<span class="pill {"pill-normal" if iot_mgr.connected else "pill-off"}">{"ONLINE" if iot_mgr.connected else "OFFLINE"}</span></div>'
                    f'<div class="u-role" style="margin-top:.3rem;">{esc(iot_mgr.last_connect_err or cfg["mqtt_server"])}</div></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("🔼 เปิดลิ้นชัก (UP)", use_container_width=True):
            ok, msg = iot_mgr.publish(cfg["topic_servo_cmd"], "UP")
            log_audit("IOT_SERVO", "Drawer D4", after_val="UP", detail=msg, ok=ok)
            st.toast("ส่งคำสั่งแล้ว" if ok else f"ผิดพลาด: {msg}", icon="✅" if ok else "⚠️")
    with b2:
        if st.button("🔽 ปิดลิ้นชัก (DOWN)", use_container_width=True):
            ok, msg = iot_mgr.publish(cfg["topic_servo_cmd"], "DOWN")
            log_audit("IOT_SERVO", "Drawer D4", after_val="DOWN", detail=msg, ok=ok)
            st.toast("ส่งคำสั่งแล้ว" if ok else f"ผิดพลาด: {msg}", icon="✅" if ok else "⚠️")
    st.markdown("#### 📡 MQTT Feed (ล่าสุด)")
    feed = iot_mgr.raw_mqtt_feed[:40]
    st.dataframe(pd.DataFrame(feed), use_container_width=True, hide_index=True)

def page_water_alarm():
    st.markdown('<div class="app-hero"><div><div class="t">💧 Water Alarm System</div></div></div>', unsafe_allow_html=True)
    cols = st.columns(len(iot_mgr.water_status))
    for c, (k, v) in zip(cols, iot_mgr.water_status.items()):
        online = iot_mgr.water_online.get(k, True)
        cls = "pill-normal" if (v == "NORMAL" and online) else ("pill-off" if not online else "pill-alarm")
        label = "ปกติ" if (v == "NORMAL" and online) else ("ออฟไลน์" if not online else "ALARM")
        c.markdown(f'<div class="iot-card"><div class="hd">{esc(k)}</div><div class="bd"><span class="nm">Pump</span>'
                   f'<span class="pill {cls}">{label}</span></div></div>', unsafe_allow_html=True)
    st.caption(f"ข้อความล่าสุด: {iot_mgr.water_last_msg}")
    logs = list(db.iot_logs.find({"system": "WATER"}).sort("datetime", -1).limit(200))
    if logs:
        df = pd.DataFrame(logs).drop(columns=["_id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
        if has_perm("export"): export_buttons(df, "water_alarm_logs", "wl")

def page_fire_alarm():
    st.markdown('<div class="app-hero"><div><div class="t">🚨 Fire Alarm System</div></div></div>', unsafe_allow_html=True)
    cls = "pill-normal" if iot_mgr.fire_status == "CLEAR" else "pill-alarm"
    st.markdown(f'<div class="iot-card"><div class="hd">สถานะรวม</div><div class="bd"><span class="nm">{esc(iot_mgr.fire_location)}</span>'
                f'<span class="pill {cls}">{iot_mgr.fire_status}</span></div></div>', unsafe_allow_html=True)
    cols = st.columns(len(iot_mgr.fire_zones))
    for c, (k, v) in zip(cols, iot_mgr.fire_zones.items()):
        c.markdown(f'<div class="iot-card"><div class="hd">{esc(k)}</div><div class="bd"><span class="nm">Zone</span>'
                   f'<span class="pill {"pill-normal" if v=="NORMAL" else "pill-alarm"}">{v}</span></div></div>', unsafe_allow_html=True)
    logs = list(db.iot_logs.find({"system": "FIRE"}).sort("datetime", -1).limit(200))
    if logs:
        df = pd.DataFrame(logs).drop(columns=["_id"], errors="ignore")
        st.dataframe(df, use_container_width=True, hide_index=True)
        if has_perm("export"): export_buttons(df, "fire_alarm_logs", "fl")

def page_solar():
    st.markdown('<div class="app-hero"><div><div class="t">☀️ ระบบโซล่าเซลล์ (Growatt)</div></div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1,3])
    with c1:
        if st.button("🔄 ดึงข้อมูลล่าสุด", type="primary", use_container_width=True):
            with st.spinner("กำลังดึงข้อมูล..."):
                st.session_state["_solar"] = fetch_growatt_realtime(sync_sheets=False)
            log_audit("SOLAR_FETCH", "Growatt")
    with c2:
        res = st.session_state.get("_solar")
        if not res:
            res = fetch_growatt_realtime()
        if res.get("ok"):
            k = [("แรงดันแบตเตอรี่", f"{res['vBat']} V"), ("SOC", f"{res['soc']}%"),
                 ("PV", f"{res['pvP']} W"), ("โหลด", f"{res['load']} W"), ("กริด", f"{res['gridP']} W"),
                 ("โหมดแบต", res["batMode"])]
            cols = st.columns(len(k))
            for c, (l, v) in zip(cols, k):
                c.markdown(f'<div class="glass-kpi"><div class="lbl">{l}</div><div class="val" style="font-size:1.15rem;">{v}</div></div>')
        else:
            st.warning(res.get("error", "ไม่สามารถดึงข้อมูลได้"))

def page_audit():
    st.markdown('<div class="app-hero"><div><div class="t">🔍 ค้นหา & ประวัติการทำรายการ</div></div></div>', unsafe_allow_html=True)
    src = st.selectbox("แหล่งข้อมูล", ["🧾 Audit Log (ทุก action)", "🔄 ประวัติยืม-คืน", "📋 ประวัติตรวจเช็ค", "📥 คำขอเพิ่มสต็อก"])
    today = get_now_th().date()
    d1, d2 = st.columns(2)
    dflt_from = today - timedelta(days=30)
    date_from = d1.date_input("ตั้งแต่วันที่", value=dflt_from, key="srch_from")
    date_to = d2.date_input("ถึงวันที่", value=today, key="srch_to")
    kw = st.text_input("🔎 ค้นหาคำค้น (ชื่อผู้ใช้ / รายการ / รายละเอียด)", key="srch_kw")
    frm = date_from.strftime("%Y-%m-%d"); to = date_to.strftime("%Y-%m-%d") + " 23:59:59"

    if src.startswith("🧾"):
        q = {"datetime": {"$gte": frm, "$lte": to}}
        if kw.strip():
            q["$or"] = [{"actor": {"$regex": re.escape(kw.strip()), "$options": "i"}},
                        {"action": {"$regex": re.escape(kw.strip()), "$options": "i"}},
                        {"target": {"$regex": re.escape(kw.strip()), "$options": "i"}},
                        {"detail": {"$regex": re.escape(kw.strip()), "$options": "i"}}]
        logs = list(db.audit_logs.find(q).sort("datetime", -1).limit(max_rows()))
        df = pd.DataFrame(logs).drop(columns=["_id"], errors="ignore") if logs else pd.DataFrame()
    elif src.startswith("🔄"):
        logs = list(db.transactions.find({"borrow_date": {"$gte": frm, "$lte": to}}).sort("id", -1).limit(max_rows()))
        df = pd.DataFrame([{"รหัส": t["id"], "อุปกรณ์": item_name_map.get(t["item_id"],"?"), "จำนวน": t.get("quantity"),
            "ผู้ยืม": t.get("borrower_name"), "ผู้รับคืน": t.get("receiver_name"),
            "วันที่ยืม": t.get("borrow_date"), "วันที่คืน": t.get("return_date"), "สถานะ": t.get("status")} for t in logs])
    elif src.startswith("📋"):
        logs = list(db.inspections.find({"inspection_date": {"$gte": frm, "$lte": to}}).sort("id", -1).limit(max_rows()))
        df = pd.DataFrame([{"รหัส": t["id"], "ผู้ตรวจ": t.get("tech_name"), "หมวด": t.get("category"),
            "วันที่": t.get("inspection_date"), "รอบ": t.get("session_num"), "รายละเอียด": t.get("details")} for t in logs])
    else:
        logs = list(db.requisition_requests.find({"request_date": {"$gte": frm, "$lte": to}}).sort("id", -1).limit(max_rows()))
        df = pd.DataFrame([{"รหัส": t["id"], "ผู้ขอ": t.get("tech_name"), "อุปกรณ์": item_name_map.get(t["item_id"],"?"),
            "จำนวน": t.get("quantity"), "หมายเหตุ": t.get("note"), "วันที่ขอ": t.get("request_date"),
            "สถานะ": t.get("status")} for t in logs])

    if not df.empty and kw.strip() and not src.startswith("🧾"):
        mask = df.astype(str).apply(lambda c: c.str.contains(re.escape(kw.strip()), case=False, na=False)).any(axis=1)
        df = df[mask]
    st.dataframe(df, use_container_width=True, hide_index=True)
    if has_perm("export"): export_buttons(df, f"รายงาน_{src.split()[0]}", "aud")

    # ข้อ 3: ประวัติรายผู้ใช้
    with st.expander("👤 ประวัติการใช้งานรายบุคคล"):
        users = sorted({l.get("actor","") for l in db.audit_logs.find({}, {"actor":1}).limit(5000)} - {""})
        if users:
            u = st.selectbox("เลือกผู้ใช้", users)
            ul = list(db.audit_logs.find({"actor": u}).sort("datetime", -1).limit(max_rows()))
            udf = pd.DataFrame(ul).drop(columns=["_id"], errors="ignore")
            st.dataframe(udf, use_container_width=True, hide_index=True)
            if has_perm("export"): export_buttons(udf, f"audit_{u}", "uau")

def page_settings():
    st.markdown('<div class="app-hero"><div><div class="t">⚙️ ตั้งค่าระบบ & บัญชีผู้ใช้งาน</div></div></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🎨 ธีม & ระบบ", "🔐 บัญชีผู้ใช้", "🔌 สถานะ IoT Credential"])

    with t1:
        st.markdown("#### 🎨 การตั้งค่าธีม (ข้อ 6)")
        c1, c2, c3 = st.columns(3)
        with c1:
            th = st.selectbox("ธีมหลัก", list(THEME_PRESETS.keys()), index=list(THEME_PRESETS.keys()).index(theme_name) if theme_name in THEME_PRESETS else 0)
        with c2:
            ac = st.color_picker("สี Accent", accent)
        with c3:
            dn = st.selectbox("ความหนาแน่น", ["ปกติ", "กระชับ"], index=0 if density == "ปกติ" else 1)
        if st.button("💾 บันทึกการตั้งค่าธีม", type="primary"):
            set_settings_val("ui_theme", th); set_settings_val("ui_accent", ac); set_settings_val("ui_density", dn)
            log_audit("SET_THEME", th, detail=f"accent={ac} density={dn}")
            done("บันทึกธีมเรียบร้อยแล้ว")
        st.markdown("#### ⚙️ ข้อ 7: ขอบเขตการใช้งาน")
        with st.form("limits_form"):
            a1, a2 = st.columns(2)
            idle_m = a1.number_input("Idle Timeout (นาที)", min_value=1, max_value=240, value=int(get_settings_val("session_idle_minutes","30")))
            quota_m = a2.number_input("โควตาตรวจเช็ค/วัน (รอบ)", min_value=1, max_value=20, value=int(get_settings_val("global_daily_quota","3")))
            b1, b2 = st.columns(2)
            maxrow = b1.number_input("แถวสูงสุดต่อหน้า", min_value=50, max_value=5000, value=max_rows())
            maxexp = b2.number_input("แถวสูงสุดต่อการส่งออก", min_value=100, max_value=50000, value=max_export_rows())
            cooldown = st.number_input("Cooldown คำสั่ง IoT (วินาที)", min_value=0, max_value=60, value=int(get_settings_val("iot_cooldown_sec","3")))
            if st.form_submit_button("💾 บันทึกข้อจำกัด", type="primary"):
                set_settings_val("session_idle_minutes", idle_m); set_settings_val("global_daily_quota", quota_m)
                set_settings_val("max_rows_per_page", maxrow); set_settings_val("max_export_rows", maxexp)
                set_settings_val("iot_cooldown_sec", cooldown)
                log_audit("SET_LIMITS", "system", detail=f"idle={idle_m} quota={quota_m} rows={maxrow} exp={maxexp}")
                done("บันทึกข้อจำกัดเรียบร้อยแล้ว")

    with t2:
        st.markdown("#### 👥 บัญชีผู้ใช้งาน")
        tdf = get_tech_users_df()
        if not tdf.empty:
            show = tdf.copy()
            if "password" in show.columns:
                show["password"] = show["password"].apply(lambda v: "🔒 (เข้ารหัสแล้ว)" if str(v).startswith(("argon2$","bcrypt$","pbkdf2$")) else "⚠️ (ข้อความธรรมดา)")
            st.dataframe(show, use_container_width=True, hide_index=True)
        with st.form("add_tech_form", clear_on_submit=True):
            nu = st.text_input("Username ใหม่")
            npw = st.text_input("Password ใหม่", type="password")
            nr = st.selectbox("สิทธิ์", [ROLE_TECH, ROLE_TECH_SP, ROLE_STORE, ROLE_IOT, ROLE_AUDIT])
            if st.form_submit_button("➕ สร้างบัญชี"):
                sc, tip = password_strength(npw)
                if not nu.strip() or not npw:
                    st.error("กรุณากรอกข้อมูลให้ครบ")
                elif sc < 4:
                    st.error(f"รหัสผ่านอ่อนเกินไป: {tip}")
                elif db.tech_users.find_one({"username": nu.strip()}):
                    st.error("Username นี้มีอยู่แล้ว")
                else:
                    h = hash_password(npw)
                    db.tech_users.insert_one({"id": get_next_sequence("tech_users_id"), "username": nu.strip(),
                        "password": h, "role": nr, "created": get_now_str()})
                    store_password_history(nu.strip(), h)
                    get_tech_users_df.clear(); log_audit("USER_CREATE", nu.strip(), detail=role_label(nr))
                    done(f"สร้างบัญชี '{nu}' สำเร็จ")
        st.markdown("#### 🔁 เปลี่ยนรหัสผ่าน (บังคับไม่ใช้รหัสผ่านเดิมซ้ำ — ข้อ 2)")
        with st.form("chpwd_form"):
            cu = st.text_input("Username")
            old = st.text_input("รหัสผ่านเดิม", type="password")
            new = st.text_input("รหัสผ่านใหม่", type="password")
            if st.form_submit_button("🔐 เปลี่ยนรหัสผ่าน", type="primary"):
                sc, tip = password_strength(new)
                rec = db.tech_users.find_one({"username": cu.strip()}) if cu.strip() else None
                if not rec:
                    st.error("ไม่พบผู้ใช้")
                elif not verify_password(old, rec.get("password",""))[0]:
                    st.error("รหัสผ่านเดิมไม่ถูกต้อง")
                elif sc < 4:
                    st.error(f"รหัสผ่านใหม่อ่อนเกินไป: {tip}")
                elif password_used_before(cu.strip(), new):
                    st.error("❌ ห้ามใช้รหัสผ่านที่เคยใช้มาแล้ว (5 รอบล่าสุด)")
                else:
                    h = hash_password(new)
                    db.tech_users.update_one({"username": cu.strip()}, {"$set": {"password": h}})
                    store_password_history(cu.strip(), h)
                    db.sessions.delete_many({"username": cu.strip()})
                    log_audit("PASSWORD_CHANGE", cu.strip())
                    done("เปลี่ยนรหัสผ่านและบังคับให้ออกจากระบบทุกเครื่องแล้ว")

    with t3:
        st.markdown("#### 🔌 สถานะ Credential ของบริการภายนอก (ข้อ 1)")
        st.info("ค่า Credential จะไม่ถูกแสดงเป็นข้อความตามจริง และระบบจะอ่านจาก `st.secrets['iot']` หรือ Environment Variables เท่านั้น")
        cfg = get_iot_config()
        rows = [{"บริการ": "MQTT Broker", "ตั้งค่า": "✅ พร้อม" if cfg.get("_has_mqtt") else "❌ ไม่ครบ",
                 "Server": mask_secret(cfg.get("mqtt_server")), "User": mask_secret(cfg.get("mqtt_user"))},
                {"บริการ": "LINE Notify", "ตั้งค่า": "✅ พร้อม" if cfg.get("_has_line") else "❌ ไม่ครบ",
                 "Token": mask_secret(cfg.get("line_token")), "Group": mask_secret(cfg.get("line_group_id"))},
                {"บริการ": "Growatt Cloud", "ตั้งค่า": "✅ พร้อม" if cfg.get("_has_growatt") else "❌ ไม่ครบ",
                 "User": mask_secret(cfg.get("growatt_user")), "SN": mask_secret(cfg.get("growatt_sn"))}]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("แนะนำ: อย่าเก็บ credential ในฐานข้อมูล — ให้ใช้ secrets/environment เท่านั้น และหมุนเวียนรหัสผ่านเป็นระยะ")

# =====================================================================
#  TECH VIEW
# =====================================================================
def render_tool_inspection_list(tools_df):
    q = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
    df = tools_df
    if q.strip(): df = df[df['name'].str.contains(q.strip(), case=False, na=False)]
    with keyed_container("tech_check_list", height=520):
        for _, row in df.iterrows():
            rid = int(row['id']); cur = row['status']; sub = str(row.get('subcategory',''))
            bq = borrowed_item_map.get(rid, 0); binfo = ", ".join(borrower_details_map.get(rid, []))
            if bq > 0: badge, txt = "🔵", f"[ถูกยืมโดย {binfo}]"
            elif cur == "ปกติ": badge, txt = "🟢", "[ปกติ]"
            elif str(cur).startswith("กำลังใช้งาน"): badge, txt = "🟡", f"[{cur}]"
            elif cur == "อุปกรณ์หมด": badge, txt = "🟠", "[อุปกรณ์หมด]"
            else: badge, txt = "🔴", f"[{cur}]"
            with st.expander(f"{badge} {row['name']} (คงเหลือ: {row['quantity']})  {txt}"):
                if sub == "อุปกรณ์ช่างทั่วไป":
                    st.number_input("ปรับจำนวนคงเหลือจริง *", min_value=0, value=int(row['quantity']), key=f"gen_q_{rid}")
                else:
                    base = cur.split(" (")[0] if "(" in str(cur) else cur
                    opts = ["ปกติ","ชำรุด","สูญหาย","อุปกรณ์หมด","กำลังใช้งาน"]
                    if sub == "เครื่องมือช่าง" and "อุปกรณ์หมด" in opts: opts.remove("อุปกรณ์หมด")
                    idx = opts.index(base) if base in opts else 0
                    sel = st.selectbox("สถานะการตรวจสอบ *", opts, index=idx, key=f"status_sel_{rid}")
                    if sel != "ปกติ":
                        if sel == "กำลังใช้งาน":
                            d0 = cur.split("(")[1].replace(")","") if "กำลังใช้งาน (" in str(cur) else ""
                            st.text_input("ระบุรายละเอียดการใช้งาน *", value=d0, key=f"issue_detail_{rid}")
                            if int(row['orig_quantity']) > 1:
                                st.number_input("จำนวนชิ้นที่นำไปใช้งาน *", min_value=1, max_value=int(row['orig_quantity']), value=1, key=f"issue_qty_{rid}")
                        elif sel in ["ชำรุด","สูญหาย"]:
                            if int(row['orig_quantity']) > 1:
                                st.number_input(f"จำนวนชิ้นที่{sel} *", min_value=1, max_value=int(row['orig_quantity']), value=1, key=f"issue_qty_{rid}")
                ib = get_item_image(rid)
                if ib:
                    with st.popover("📷 ดูรูปภาพอุปกรณ์"):
                        st.image(ib, caption=row['name'], use_container_width=True)

def render_pool_list(pool_df):
    q = st.text_input("🔍 ค้นหาอุปกรณ์สระว่ายน้ำ...", key="pool_search_box")
    df = pool_df
    if q.strip(): df = df[df['name'].str.contains(q.strip(), case=False, na=False)]
    with keyed_container("pool_check_list", height=520):
        for _, row in df.iterrows():
            rid = int(row['id'])
            with st.expander(f"🏊 {row['name']} (ปัจจุบัน: {row['quantity']} ชิ้น)"):
                st.number_input("ปรับจำนวนคงเหลือจริง *", min_value=0, value=int(row['quantity']), key=f"pool_q_{rid}")
                ib = get_item_image(rid)
                if ib:
                    with st.popover("📷 ดูรูปภาพอุปกรณ์"):
                        st.image(ib, caption=row['name'], use_container_width=True)

def clear_inspection_widget_state():
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(("issue_type_","issue_detail_","issue_qty_","pool_q_","status_sel_","gen_q_")):
            del st.session_state[k]

def tech_view():
    st.markdown(f"""
    <div class="app-hero">
      <div><div class="t">🛠️ ระบบเช็คสถานะอุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ</div>
           <div class="s">ประจำวันที่ {get_now_str("%d/%m/%Y")}</div></div>
      <div class="badge-row"><span class="status-pill-top info">👷 {esc(st.session_state.username)} ({esc(role_label(st.session_state.role))})</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="kpi-grid">
      <div class="glass-kpi"><div class="top"><span class="lbl">อุปกรณ์ทั้งหมด</span><span class="ic-badge">🛠️</span></div><div class="val">{len(items_df)}</div></div>
      <div class="glass-kpi"><div class="top"><span class="lbl">{abn_label}</span><span class="ic-badge">⚠️</span></div>
        <div class="val" style="color:{'#F87171' if abn_cnt else '#34D399'} !important;">{abn_cnt}</div></div>
      <div class="glass-kpi"><div class="top"><span class="lbl">กำลังถูกยืมอยู่</span><span class="ic-badge">📤</span></div><div class="val">{borrowed_cnt}</div></div>
    </div>""", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["📋 ตรวจสอบอุปกรณ์", "📦 เบิกอุปกรณ์", "🔄 ระบบยืม-คืน อุปกรณ์"])
    with t3: render_borrow_return_system()
    with t2: page_requisition()
    with t1:
        cat = st.radio("เลือกหมวด", ["🔧 อุปกรณ์ช่าง", "🏊 อุปกรณ์สระว่ายน้ำ"], horizontal=True)
        today = get_now_str("%Y-%m-%d")
        if cat.startswith("🔧"):
            cnt = get_inspection_count("อุปกรณ์ช่าง", today)
            base = int(get_settings_val("global_daily_quota","3"))
            extra = int(get_settings_val(f"extra_quota_{today}","0"))
            mine = quota_used(st.session_state.username, "อุปกรณ์ช่าง", today)
            st.caption(f"📊 วันนี้คุณตรวจไปแล้ว {mine} รอบ · โควตารวมทั้งระบบ {base+extra} รอบ")
            if cnt >= base + extra:
                st.error("⚠️ ครบโควตารอบตรวจของวันนี้แล้ว")
            else:
                tdf = items_df[(items_df['category']=='อุปกรณ์ช่าง') & (items_df['orig_quantity']>0)] if not items_df.empty else pd.DataFrame()
                if tdf.empty: st.info("ไม่มีอุปกรณ์ช่าง")
                else:
                    render_tool_inspection_list(tdf)
                    st.markdown("### 📸 รูปถ่ายหน้างาน")
                    pf = st.file_uploader("เลือก/ถ่ายรูป (ครบ 4 รูป)", type=["jpg","jpeg","png"],
                                         accept_multiple_files=True, key=f"tech_up_{st.session_state.uploader_version}")
                    npf = len(pf) if pf else 0
                    st.progress(min(npf/4.0, 1.0), text=f"📸 แนบรูปแล้ว {npf}/4 รูป")
                    if st.button(f"💾 ยืนยันส่งผลตรวจ (รอบที่ {cnt+1})", type="primary", use_container_width=True):
                        if npf < 4:
                            st.error("❌ กรุณาแนบรูปให้ครบ 4 รูป")
                        elif not rate_limit(f"inspect:{st.session_state.username}", 10, 300):
                            st.error("❌ ส่งผลตรวจถี่เกินไป")
                        else:
                            reports = {}
                            for _, row in tdf.iterrows():
                                rid = int(row['id']); sub = str(row.get('subcategory',''))
                                if sub == "อุปกรณ์ช่างทั่วไป":
                                    reports[rid] = {"type":"general","quantity": int(st.session_state.get(f"gen_q_{rid}", row['quantity']))}
                                else:
                                    sel = st.session_state.get(f"status_sel_{rid}", "ปกติ")
                                    reports[rid] = {"type":"tool","flagged": sel!="ปกติ","status": sel,
                                        "detail": st.session_state.get(f"issue_detail_{rid}","") or "",
                                        "qty": int(st.session_state.get(f"issue_qty_{rid}",1) or 1)}
                            err = ""
                            for iid, d in reports.items():
                                if d["type"]=="tool" and d["flagged"] and d["status"]=="กำลังใช้งาน" and not d["detail"].strip():
                                    err = "❌ กรุณากรอกรายละเอียดการใช้งาน"; break
                            if err: st.error(err)
                            else:
                                ops, changes, summ = [], [], []
                                rm = tdf.set_index('id')
                                for iid, d in reports.items():
                                    oq = int(rm.loc[iid,'orig_quantity']); nm = rm.loc[iid,'name']; cq = int(rm.loc[iid,'quantity'])
                                    if d["type"]=="general":
                                        nq = d["quantity"]
                                        ops.append(pymongo.operations.UpdateOne({"id": iid},
                                            {"$set": {"quantity": nq, "orig_quantity": nq, "status": "ปกติ"}, "$inc": {"version": 1}}))
                                        if nq != cq: summ.append(f"{nm}: ปรับเหลือ {nq} ชิ้น")
                                        if nq < cq: changes.append({"item_id": iid, "name": nm, "old_qty": cq, "new_qty": nq, "reason": "ปรับสต็อก"})
                                    elif d["flagged"]:
                                        fs = f"กำลังใช้งาน ({d['detail']})" if (d["status"]=="กำลังใช้งาน" and d["detail"].strip()) else d["status"]
                                        nq = 0 if d["status"]=="อุปกรณ์หมด" else max(0, oq - d["qty"])
                                        ops.append(pymongo.operations.UpdateOne({"id": iid},
                                            {"$set": {"status": fs, "quantity": nq}, "$inc": {"version": 1}}))
                                        summ.append(f"{nm}: {d['status']}")
                                        if nq < cq: changes.append({"item_id": iid, "name": nm, "old_qty": cq, "new_qty": nq, "reason": d["status"]})
                                    else:
                                        ops.append(pymongo.operations.UpdateOne({"id": iid},
                                            {"$set": {"status": "ปกติ", "quantity": oq}, "$inc": {"version": 1}}))
                                if ops: db.items.bulk_write(ops, ordered=False)
                                photos = "|||".join(compress_image_to_base64(f, max_size=(1000,1000), quality=70) for f in pf)
                                db.inspections.insert_one({"id": get_next_sequence("inspections_id"),
                                    "tech_name": st.session_state.username, "category": "อุปกรณ์ช่าง",
                                    "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"), "session_num": cnt+1,
                                    "details": f"รอบที่ {cnt+1} | รายการผิดปกติ: {', '.join(summ) if summ else 'ปกติทุกรายการ'}",
                                    "changes": changes, "photos": photos})
                                log_audit("INSPECTION", "อุปกรณ์ช่าง", after_val=f"{len(summ)} รายการผิดปกติ")
                                refresh_items(); get_inspection_count.clear(); get_inspections_list.clear()
                                clear_inspection_widget_state(); st.session_state.uploader_version += 1
                                done("บันทึกผลการตรวจสอบเรียบร้อยแล้ว!")
        else:
            pdf = items_df[items_df['category']=='อุปกรณ์สระว่ายน้ำ'] if not items_df.empty else pd.DataFrame()
            if pdf.empty: st.info("ไม่มีอุปกรณ์สระว่ายน้ำ")
            else:
                render_pool_list(pdf)
                st.markdown("### 📸 รูปถ่ายหน้างาน")
                pf = st.file_uploader("เลือก/ถ่ายรูป (ครบ 4 รูป)", type=["jpg","jpeg","png"],
                                     accept_multiple_files=True, key=f"pool_up_{st.session_state.uploader_version}")
                npf = len(pf) if pf else 0
                st.progress(min(npf/4.0, 1.0), text=f"📸 แนบรูปแล้ว {npf}/4 รูป")
                if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                    if npf < 4: st.error("❌ กรุณาแนบรูปให้ครบ 4 รูป")
                    else:
                        ops, changes, summ = [], [], []
                        rm = pdf.set_index('id')
                        for iid in pdf['id']:
                            rid = int(iid); k = f"pool_q_{rid}"
                            if k not in st.session_state: continue
                            qv = int(st.session_state[k]); oq = int(rm.loc[rid,'quantity'])
                            if qv != oq:
                                ops.append(pymongo.operations.UpdateOne({"id": rid},
                                    {"$set": {"quantity": qv, "orig_quantity": qv}, "$inc": {"version": 1}}))
                                summ.append(f"{rm.loc[rid,'name']}: {oq} → {qv}")
                                if qv < oq: changes.append({"item_id": rid, "name": rm.loc[rid,'name'], "old_qty": oq, "new_qty": qv, "reason": "ปรับจำนวน"})
                        if ops: db.items.bulk_write(ops, ordered=False)
                        photos = "|||".join(compress_image_to_base64(f, max_size=(1000,1000), quality=70) for f in pf)
                        db.inspections.insert_one({"id": get_next_sequence("inspections_id"),
                            "tech_name": st.session_state.username, "category": "อุปกรณ์สระว่ายน้ำ",
                            "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"), "session_num": 1,
                            "details": "อัปเดตจำนวนอุปกรณ์สระว่ายน้ำ" + (f" | {', '.join(summ)}" if summ else ""),
                            "changes": changes, "photos": photos})
                        log_audit("INSPECTION", "อุปกรณ์สระว่ายน้ำ")
                        refresh_items(); get_inspection_count.clear(); get_inspections_list.clear()
                        clear_inspection_widget_state(); st.session_state.uploader_version += 1
                        done("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")

# =====================================================================
#  ROUTING
# =====================================================================
if st.session_state.role in TECH_ROLES:
    st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)
    tech_view()
else:
    page = show_sidebar()
    if page == "📊 ภาพรวมระบบ": page_overview()
    elif page == "🛠️ คลังอุปกรณ์": page_inventory()
    elif page == "📦 คำขอเพิ่มสต็อก": page_requisition()
    elif page == "🔄 ยืม-คืนอุปกรณ์": render_borrow_return_system()
    elif page == "🗄️ ควบคุมลิ้นชัก": page_iot_drawer()
    elif page == "💧 Water Alarm": page_water_alarm()
    elif page == "🚨 Fire Alarm": page_fire_alarm()
    elif page == "☀️ ระบบโซล่าเซลล์": page_solar()
    elif page == "🔍 ค้นหา & ประวัติ": page_audit()
    elif page == "⚙️ ตั้งค่าระบบ & บัญชี": page_settings()