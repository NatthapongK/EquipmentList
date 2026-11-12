import streamlit as st
import streamlit.components.v1 as components
import pymongo
import pymongo.operations
import pandas as pd
from datetime import datetime, timezone, timedelta
import base64
import html as _html
import re
import io
import os
import ssl
import time
import json
import hashlib
import secrets
import threading
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

# =====================================================================
#  KAVE TOWN SHIFT - CENTRAL ENTERPRISE COMMAND & INVENTORY SYSTEM V5
# =====================================================================

TZ_TH = timezone(timedelta(hours=7))

def get_now_th():
    return datetime.now(TZ_TH)

def get_now_str(fmt="%Y-%m-%d %H:%M:%S"):
    return get_now_th().strftime(fmt)

st.set_page_config(
    page_title="ระบบจัดการอุปกรณ์-เครื่องมือช่าง & สระว่ายน้ำ",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROLE_ADMIN = "ผู้ออกแบบ/ดูแลระบบ"
ROLE_TECH = "ช่างประจำอาคาร"
ROLE_TECH_SP = "ช่างประจำอาคารพิเศษ"
TECH_ROLES = [ROLE_TECH, ROLE_TECH_SP]

# --- PASSWORD HASHING UTILS (Feature 2) ---
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return f"pbkdf2${salt}${pwd_hash}"

def verify_password(plain_password: str, stored_password: str) -> tuple[bool, bool]:
    if not stored_password:
        return False, False
    if stored_password.startswith("pbkdf2$"):
        try:
            _, salt, expected_hash = stored_password.split("$")
            pwd_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
            return secrets.compare_digest(pwd_hash, expected_hash), False
        except Exception:
            return False, False
    # Backward compatibility for plain text passwords in legacy DB
    return (plain_password == stored_password), True

# --- SECURE CONFIG LOADER (Feature 1) ---
def get_iot_config():
    iot_sec = st.secrets.get("iot", {})
    cfg = {
        "mqtt_server": iot_sec.get("mqtt_server", os.environ.get("MQTT_SERVER", "dcb4e8c8b1594e88aef914771ce94103.s1.eu.hivemq.cloud")),
        "mqtt_port": int(iot_sec.get("mqtt_port", os.environ.get("MQTT_PORT", 8883))),
        "mqtt_user": iot_sec.get("mqtt_user", os.environ.get("MQTT_USER", "32bit7k")),
        "mqtt_pass": iot_sec.get("mqtt_pass", os.environ.get("MQTT_PASS", "")),
        "topic_servo_cmd": "esp8266/servo",
        "topic_servo_status": "esp8266/servo/status",
        "topic_water": "Water alarm",
        "topic_check_clients": "CheckClients",
        "topic_fire": "Firealarm",
        "topic_fire_relay": "nodemcu/control/relay",
        "line_token": iot_sec.get("line_token", os.environ.get("LINE_TOKEN", "")),
        "line_group_id": iot_sec.get("line_group_id", os.environ.get("LINE_GROUP_ID", "")),
        "growatt_user": iot_sec.get("growatt_user", os.environ.get("GROWATT_USER", "32bit7k")),
        "growatt_pass": iot_sec.get("growatt_pass", os.environ.get("GROWATT_PASS", "")),
        "growatt_sn": iot_sec.get("growatt_sn", os.environ.get("GROWATT_SN", "RKG7BL404R")),
        "google_webapp_url": iot_sec.get("google_webapp_url", os.environ.get("GOOGLE_WEBAPP_URL", "")),
    }
    for k, v in cfg.items():
        saved = db.settings.find_one({"key": f"iot_{k}"}) if 'db' in globals() else None
        if saved and saved.get("value") not in (None, "None", ""):
            val = saved["value"]
            cfg[k] = int(val) if isinstance(v, int) and str(val).isdigit() else val
    return cfg

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
    ("ขวดน้ำยาpH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("สายดูดตะกอน สั้น+ยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
]

def build_default_docs():
    docs = []
    for idx, i in enumerate(DEFAULT_INITIAL_ITEMS, start=1):
        docs.append({
            "id": idx, "name": i[0], "category": i[1], "subcategory": i[2],
            "quantity": i[3], "orig_quantity": i[3], "status": i[4], "min_stock": 1, "alert_zero": 0, "note": i[5], "image": i[6]
        })
    return docs

# =====================================================================
#  MONGODB INITIALIZATION
# =====================================================================
@st.cache_resource
def init_mongo():
    uri = None
    try:
        uri = st.secrets["mongo"]["uri"]
    except Exception:
        uri = os.environ.get("MONGO_URI", "")

    if not uri:
        st.error("❌ ไม่พบ `st.secrets['mongo']['uri']` กรุณาตั้งค่าใน `.streamlit/secrets.toml` หรือ Environment Variables")
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
    database.iot_logs.create_index([("system", 1), ("datetime", -1)])
    database.audit_logs.create_index([("datetime", -1)])  # Feature 3 Index

    if database.items.count_documents({}, limit=1) == 0:
        database.items.insert_many(build_default_docs())
        database.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
    else:
        database.items.update_many({"orig_quantity": {"$exists": False}}, [{"$set": {"orig_quantity": "$quantity"}}])
        database.items.update_many({"min_stock": {"$exists": False}}, [{"$set": {"min_stock": 1}}])

    database.settings.update_one({"key": "low_stock_threshold"}, {"$setOnInsert": {"value": "1"}}, upsert=True)
    database.settings.update_one({"key": "global_daily_quota"}, {"$setOnInsert": {"value": "3"}}, upsert=True)
    return database

db = init_mongo()

# --- AUDIT LOG HELPER (Feature 3) ---
def log_audit(action: str, target: str, before_val=None, after_val=None, detail: str = ""):
    try:
        db.audit_logs.insert_one({
            "datetime": get_now_str("%Y-%m-%d %H:%M:%S"),
            "actor": st.session_state.get("username", "system"),
            "role": st.session_state.get("role", "-"),
            "action": action,
            "target": target,
            "before": before_val,
            "after": after_val,
            "detail": detail
        })
    except Exception:
        pass

def get_next_sequence(name):
    counter = db.counters.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
    return counter["seq"]

@st.cache_data(ttl=30, show_spinner=False)
def get_settings_val(key, default="1"):
    res = db.settings.find_one({"key": key})
    return res["value"] if res else default

def set_settings_val(key, val):
    db.settings.update_one({"key": key}, {"$set": {"value": str(val)}}, upsert=True)
    get_settings_val.clear()

def get_iot_config():
    cfg = {
        "mqtt_server": "dcb4e8c8b1594e88aef914771ce94103.s1.eu.hivemq.cloud",
        "mqtt_port": 8883,
        "mqtt_user": "32bit7k",
        "mqtt_pass": "",
        "topic_servo_cmd": "esp8266/servo",
        "topic_servo_status": "esp8266/servo/status",
        "topic_water": "Water alarm",
        "topic_check_clients": "CheckClients",
        "topic_fire": "Firealarm",
        "topic_fire_relay": "nodemcu/control/relay",
        "line_token": "",
        "line_group_id": "",
        "growatt_user": "32bit7k",
        "growatt_pass": "",
        "growatt_sn": "RKG7BL404R",
        "google_webapp_url": "",
    }
    sec = st.secrets.get("iot", {})
    for k in cfg:
        if k in sec:
            cfg[k] = sec[k]
        saved = get_settings_val(f"iot_{k}", None)
        if saved not in (None, "None", ""):
            cfg[k] = int(saved) if isinstance(cfg[k], int) and str(saved).isdigit() else saved
    return cfg

# =====================================================================
#  REAL-TIME MQTT & IOT BACKGROUND ENGINE (WITH WATCHDOG - Feature 6)
# =====================================================================
def send_line_push(message_text, token=None, group_id=None):
    if requests is None:
        return False, "requests library not installed"
    cfg = get_iot_config()
    tk = token or cfg["line_token"]
    gid = group_id or cfg["line_group_id"]
    if not tk or not gid:
        return False, "Missing LINE Token or Group ID"
    try:
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {tk}"
        }
        payload = {
            "to": gid,
            "messages": [{"type": "text", "text": message_text}]
        }
        r = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload, timeout=6)
        return (200 <= r.status_code < 300), f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

class CentralIoTManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.connected = False
        self.last_connect_err = ""
        self.client = None
        self.servo_status = "DOWN"
        self.servo_last_update = "--:--:--"
        self.water_status = {"A": "NORMAL", "B": "NORMAL", "C": "NORMAL", "D": "NORMAL", "UNDERGROUND": "NORMAL"}
        self.water_online = {"A": True, "B": True, "C": True, "D": True, "UNDERGROUND": True}
        self.water_last_msg = "พร้อมทำงาน (Ready)"
        self.fire_status = "CLEAR"
        self.fire_location = "- (ระบบปกติ)"
        self.fire_zones = {"A": "NORMAL", "B": "NORMAL", "C": "NORMAL", "D": "NORMAL", "CLUB": "NORMAL", "LIBRARY": "NORMAL", "ST": "NORMAL", "UNKNOWN": "NORMAL"}
        self.raw_mqtt_feed = []
        self.last_seen_mqtt = time.time()  # Feature 6 Watchdog

    def add_feed(self, topic, msg):
        now_s = get_now_str("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.last_seen_mqtt = time.time()
            self.raw_mqtt_feed.insert(0, {"datetime": now_s, "topic": topic, "message": msg})
            if len(self.raw_mqtt_feed) > 150:
                self.raw_mqtt_feed.pop()

    def handle_message(self, topic, payload_str):
        msg = payload_str.strip()
        msg_up = msg.upper()
        t_low = topic.lower()
        self.add_feed(topic, msg)

        if topic in ["esp8266/servo", "esp8266/servo/status"]:
            if msg_up in ["UP", "DOWN"]:
                with self.lock:
                    self.servo_status = msg_up
                    self.servo_last_update = get_now_str("%H:%M:%S")
            return

        if t_low == "water alarm" or t_low.startswith("water alarm/status/"):
            with self.lock:
                self.water_last_msg = msg
            if t_low.startswith("water alarm/status/"):
                sub = topic.split("/")[-1].upper()
                key = "UNDERGROUND" if "UNDERGROUND" in sub else sub.replace("TRANSFERPUMP", "").strip()
                if key in self.water_status and msg_up in ["ALARM", "NORMAL"]:
                    with self.lock:
                        self.water_status[key] = msg_up
                        self.water_online[key] = True
                return
            return

        if "fire" in t_low:
            if any(w in msg_up for w in ["RESET", "CLEAR", "NORMAL"]):
                with self.lock:
                    self.fire_status = "CLEAR"
                    self.fire_location = "- (ระบบปกติ)"
                    for zk in self.fire_zones:
                        self.fire_zones[zk] = "NORMAL"
            else:
                with self.lock:
                    self.fire_status = "ALERT"
                    self.fire_location = msg

    def connect(self):
        if mqtt is None:
            self.last_connect_err = "ยังไม่ได้ติดตั้ง paho-mqtt"
            return False
        cfg = get_iot_config()
        if not cfg["mqtt_server"]:
            self.last_connect_err = "ยังไม่ได้กำหนด MQTT Server"
            return False
        try:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass

            cid = f"KaveAdminPortal_{secrets.token_hex(4)}"
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
            except AttributeError:
                client = mqtt.Client(client_id=cid)

            if cfg["mqtt_user"] and cfg["mqtt_pass"]:
                client.username_pw_set(cfg["mqtt_user"], cfg["mqtt_pass"])
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

            def on_connect(c, userdata, flags, rc):
                if rc == 0:
                    self.connected = True
                    self.last_connect_err = ""
                    c.subscribe([
                        (cfg["topic_servo_cmd"], 0), (cfg["topic_servo_status"], 0),
                        (cfg["topic_water"], 0), ("Water alarm/status/#", 0),
                        (cfg["topic_check_clients"], 0), (cfg["topic_fire"], 0),
                        ("firealarm", 0), ("FireAlarm", 0), ("fire_alarm", 0),
                        (cfg["topic_fire_relay"], 0),
                    ])
                else:
                    self.connected = False
                    self.last_connect_err = f"MQTT rc={rc}"

            def on_disconnect(c, userdata, rc):
                self.connected = False

            def on_message(c, userdata, msg):
                try:
                    payload = msg.payload.decode("utf-8", errors="ignore")
                    self.handle_message(msg.topic, payload)
                except Exception:
                    pass

            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_message = on_message

            client.connect_async(cfg["mqtt_server"], int(cfg["mqtt_port"]), keepalive=30)
            client.loop_start()
            self.client = client
            return True
        except Exception as e:
            self.connected = False
            self.last_connect_err = str(e)
            return False

    def publish(self, topic, payload, retain=False):
        if not self.client or not self.connected:
            self.connect()
            time.sleep(0.5)
        if self.client:
            try:
                self.client.publish(topic, str(payload), retain=retain)
                self.handle_message(topic, str(payload))
                return True
            except Exception as e:
                self.last_connect_err = str(e)
                return False
        return False

@st.cache_resource
def get_iot_manager():
    mgr = CentralIoTManager()
    mgr.connect()
    return mgr

iot_mgr = get_iot_manager()

# =====================================================================
#  GROWATT CLOUD & GOOGLE SHEETS
# =====================================================================
def growatt_md5(password_str):
    m = hashlib.md5(password_str.encode("utf-8")).hexdigest()
    chars = list(m)
    for i in range(0, len(chars), 2):
        if chars[i] == '0':
            chars[i] = 'c'
    return "".join(chars)

def _find_key_ci(node, target_key):
    t_low = target_key.lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() == t_low and v is not None and not isinstance(v, (dict, list)):
                return v
        for v in node.values():
            res = _find_key_ci(v, target_key)
            if res is not None:
                return res
    elif isinstance(node, list):
        for item in node:
            res = _find_key_ci(item, target_key)
            if res is not None:
                return res
    return None

def _find_obj_by_sn(node, sn):
    sn_low = str(sn).strip().lower()
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("sn", "devicesn", "storagesn", "serialnum") and isinstance(v, str) and v.strip().lower() == sn_low:
                return node
        for v in node.values():
            res = _find_obj_by_sn(v, sn)
            if res is not None:
                return res
    elif isinstance(node, list):
        for item in node:
            res = _find_obj_by_sn(item, sn)
            if res is not None:
                return res
    return None

def _spf_scope(j, sn):
    dev = _find_obj_by_sn(j, sn)
    if dev is not None and (_find_key_ci(dev, "vBat") is not None or _find_key_ci(dev, "soc") is not None):
        return dev
    return j

def _get_f(node, keys):
    for k in keys:
        v = _find_key_ci(node, k)
        if v is not None:
            try:
                return float(str(v).strip())
            except Exception:
                pass
    return None

def fetch_growatt_realtime(sync_sheets=False):
    if requests is None:
        return {"ok": False, "error": "requests library not installed"}
    cfg = get_iot_config()
    if not cfg["growatt_pass"]:
        return {"ok": False, "error": "ยังไม่ได้ตั้งค่ารหัสผ่าน Growatt"}
    hosts = ["server.growatt.com", "server-api.growatt.com", "openapi.growatt.com"]
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    pwd_md5 = growatt_md5(cfg["growatt_pass"])
    sn = cfg["growatt_sn"]

    sess = requests.Session()
    sess.headers.update({"User-Agent": ua, "X-Requested-With": "XMLHttpRequest"})

    logged_in_host = None
    plant_id = ""
    last_err = ""

    for h in hosts:
        try:
            url = f"https://{h}/newTwoLoginAPI.do"
            resp = sess.post(url, data={"userName": cfg["growatt_user"], "password": pwd_md5}, timeout=10)
            if resp.status_code == 200:
                j = resp.json()
                if j.get("back", {}).get("success"):
                    logged_in_host = h
                    data_arr = j.get("back", {}).get("data", [])
                    if data_arr and isinstance(data_arr, list):
                        plant_id = str(data_arr[0].get("plantId", ""))
                    break
        except Exception as e:
            last_err = str(e)

    if not logged_in_host:
        return {"ok": False, "error": last_err or "Cannot login to Growatt servers"}

    endpoints = [
        ("GET", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageParams_sacolar&storageId={sn}", None),
        ("GET", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageInfo_sacolar&storageId={sn}", None),
    ]

    for method, ep_url, body in endpoints:
        try:
            r = sess.get(ep_url, timeout=10)
            if r.status_code != 200:
                continue
            j = _spf_scope(r.json(), sn)
            vBat = _get_f(j, ["vBat", "vBattery", "vbatSys", "vAkku"])
            soc = _get_f(j, ["capacity", "soc", "batterySoc"])
            if vBat is None and soc is None:
                continue

            pvV = _get_f(j, ["vPv1", "vPv", "pvVoltage"]) or 0.0
            pvP = _get_f(j, ["ppv1", "pPv1", "ppv", "pvPower"]) or 0.0
            load = _get_f(j, ["outPutPower", "pLoad", "pLocalLoad", "loadPower"]) or 0.0
            loadPct = _get_f(j, ["loadPercent"]) or 0.0
            gridP = _get_f(j, ["pAcInPut"]) or 0.0
            gridV = _get_f(j, ["vGrid"]) or 0.0
            invTemp = _get_f(j, ["invTemperature"]) or 0.0
            pch = _get_f(j, ["pCharge"]) or 0.0
            pdis = _get_f(j, ["pDischarge"]) or 0.0

            vBat = vBat or 0.0
            soc = soc or 0.0
            if pdis > 0.5:
                batMode, batP = "DISCHARGING", pdis
            elif pch > 0.5:
                batMode, batP = "CHARGING", pch
            else:
                batMode, batP = "IDLE", 0.0

            result = {
                "ok": True, "host": logged_in_host, "updated": get_now_str("%Y-%m-%d %H:%M:%S"),
                "vBat": round(vBat, 1), "soc": round(soc, 0), "pvV": round(pvV, 1),
                "pvI": round((pvP / vBat) if (pvP > 0 and vBat > 10) else 0.0, 1),
                "pvP": round(pvP, 0), "load": round(load, 0), "loadPct": round(loadPct, 1),
                "gridP": round(gridP, 0), "gridV": round(gridV, 0), "invTemp": round(invTemp, 1),
                "batMode": batMode, "batP": round(batP, 0),
            }
            return result
        except Exception as e:
            last_err = str(e)

    return {"ok": False, "error": last_err or "No SPF5000ES data found"}

# =====================================================================
#  IMAGE & DB HELPERS
# =====================================================================
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
    return list(db.transactions.find({"status": "กำลังยืม"}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_pending_reqs():
    return list(db.requisition_requests.find({"status": "รออนุมัติ"}, {"_id": 0}).sort("id", -1))

@st.cache_data(ttl=15, show_spinner=False)
def get_inspection_count(category, today_str):
    return db.inspections.count_documents({"category": category, "inspection_date": {"$regex": f"^{today_str}"}})

@st.cache_data(ttl=30, show_spinner=False)
def get_tx_history(limit=500):
    return list(db.transactions.find({}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1).limit(limit))

@st.cache_data(ttl=600, max_entries=300, show_spinner=False)
def get_tx_image(tx_id):
    d = db.transactions.find_one({"id": tx_id}, {"_id": 0, "borrower_image": 1})
    return b64_to_bytes(d.get("borrower_image")) if d else None

@st.cache_data(ttl=30, show_spinner=False)
def get_inspections_list(limit=1000):
    return list(db.inspections.find({}, {"_id": 0, "photos": 0}).sort("id", -1).limit(limit))

def get_recent_reductions(inspections, days=7):
    rows = []
    cutoff = pd.Timestamp(get_now_str("%Y-%m-%d %H:%M:%S")) - pd.Timedelta(days=days)
    for rec in inspections:
        cat = rec.get("category")
        if cat not in ("อุปกรณ์ช่าง", "อุปกรณ์สระว่ายน้ำ"):
            continue
        when = pd.to_datetime(rec.get("inspection_date"), errors="coerce")
        if pd.isna(when) or when < cutoff:
            continue
        found = []
        if isinstance(rec.get("changes"), list):
            for c in rec["changes"]:
                try:
                    if int(c["new_qty"]) < int(c["old_qty"]):
                        found.append((c.get("name", "-"), int(c["old_qty"]), int(c["new_qty"]), c.get("reason", "")))
                except Exception:
                    continue
        for name, old_q, new_q, reason in found:
            rows.append({
                "วันที่ตรวจ": when.strftime("%d/%m/%Y %H:%M"), "อุปกรณ์": name, "หมวดหมู่": cat,
                "จำนวนเดิม": old_q, "จำนวนใหม่": new_q, "ลดลง": old_q - new_q,
                "สาเหตุ": reason or "ปรับจำนวน", "ผู้ตรวจ": rec.get("tech_name", "-"),
            })
    return rows

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
    u, p = None, None
    for line in text_content.splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        if "username" in line_s:
            m = re.search(r'["\']([^"\']+)["\']', line_s)
            if m: u = m.group(1)
        elif "password" in line_s:
            m = re.search(r'["\']([^"\']+)["\']', line_s)
            if m: p = m.group(1)
        if u and p:
            tech_list.append((u, p))
            u, p = None, None
    return tech_list

def esc(text):
    return _html.escape(str(text))

def switch_role(new_role):
    st.session_state.role = new_role
    st.session_state.original_role = ROLE_ADMIN
    tk = st.session_state.get("token")
    if tk:
        db.sessions.update_one({"token": tk}, {"$set": {"role": new_role}})
    st.rerun()

# =====================================================================
#  STYLING & CSS (Ocean Glassmorphism V5)
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
:root {
  color-scheme: dark;
  --bg-main: #08121E;
  --glass-surface: rgba(16, 30, 48, 0.65);
  --glass-border: rgba(148, 163, 184, 0.16);
  --ink: #F8FAFC;
  --muted: #94A3B8;
  --cyan: #38BDF8;
}
.stApp { background-color: var(--bg-main) !important; color: var(--ink); }
header[data-testid="stHeader"] { background: transparent !important; }
.app-hero {
  background: rgba(16, 30, 48, 0.75); backdrop-filter: blur(20px);
  border-radius: 16px; padding: 0.85rem 1.2rem; border: 1px solid var(--glass-border);
  display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.85rem;
}
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(195px, 1fr)); gap: 0.75rem; margin-bottom: 0.85rem; }
.glass-kpi {
  background: linear-gradient(145deg, rgba(22, 38, 60, 0.62) 0%, rgba(14, 25, 42, 0.76) 100%);
  backdrop-filter: blur(18px); border: 1px solid var(--glass-border); border-radius: 16px; padding: 0.95rem 1.05rem;
}
.glass-kpi .lbl { font-size: 0.74rem; color: #94A3B8; font-weight: 600; }
.glass-kpi .val { font-size: 1.55rem; font-weight: 800; color: #FFFFFF; }
.iot-card { background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: 14px; padding: 0.85rem 1rem; }
.pill { padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.73rem; font-weight: 700; display: inline-block; }
.pill-normal { background: rgba(16, 185, 129, 0.14); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.45); }
.pill-alarm { background: rgba(239, 68, 68, 0.20); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.55); }
</style>
""", unsafe_allow_html=True)

# =====================================================================
#  SESSION & LOGIN
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.session_state.token = None

LS_KEY = "inv_token"
local_store = LocalStorage() if LocalStorage is not None else None
saved_token = None
if local_store is not None:
    try: saved_token = local_store.getItem(LS_KEY)
    except Exception: pass

if not st.session_state.logged_in:
    cand_token = st.query_params.get("token") or saved_token
    if cand_token:
        sess = db.sessions.find_one({"token": cand_token})
        if sess and sess.get("role"):
            db.sessions.update_one({"token": cand_token}, {"$set": {"created": datetime.now(timezone.utc)}})
            st.session_state.logged_in = True
            st.session_state.role = sess["role"]
            st.session_state.username = sess["username"]
            st.session_state.original_role = sess.get("original_role")
            st.session_state.token = sess["token"]
            st.query_params["token"] = sess["token"]
        else:
            st.query_params.clear()

_flash = st.session_state.pop("_flash", None)
if _flash:
    st.toast(_flash[0], icon=_flash[1])

# =====================================================================
#  LOGIN SCREEN
# =====================================================================
if not st.session_state.logged_in or not st.session_state.role:
    _, col_login, _ = st.columns([1, 1.45, 1])
    with col_login:
        st.markdown("""
        <div class="app-hero" style="margin-top:2rem;">
          <div>
            <div style="font-size:1.18rem; font-weight:800;">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>
            <div style="font-size:0.78rem; color:#94A3B8;">เข้าสู่ระบบเพื่อตรวจเช็ค ยืม-คืน และบริหารจัดการระบบ</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("ชื่อผู้ใช้งาน (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)

        tech_df = get_tech_users_df()
        if submitted:
            role_val, user_val = "", ""
            try:
                admin_user = st.secrets["admin"]["username"]
                admin_pass = st.secrets["admin"]["password"]
            except Exception:
                admin_user, admin_pass = "admin", "admin"

            if username == admin_user and password == admin_pass:
                role_val, user_val = ROLE_ADMIN, admin_user
            else:
                matched_tech = tech_df[tech_df['username'] == username] if not tech_df.empty else pd.DataFrame()
                if not matched_tech.empty:
                    stored_pwd = matched_tech.iloc[0]['password']
                    is_valid, needs_upgrade = verify_password(password, stored_pwd)
                    if is_valid:
                        role_val, user_val = ROLE_TECH, username
                        if needs_upgrade:
                            db.tech_users.update_one({"username": username}, {"$set": {"password": hash_password(password)}})

            if role_val:
                token = secrets.token_urlsafe(24)
                db.sessions.insert_one({"token": token, "username": user_val, "role": role_val, "original_role": role_val if role_val == ROLE_ADMIN else None, "created": datetime.now(timezone.utc)})
                st.session_state.logged_in = True
                st.session_state.role = role_val
                st.session_state.username = user_val
                st.session_state.token = token
                st.query_params["token"] = token
                log_audit("LOGIN", user_val, detail=f"User logged in as {role_val}")
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# =====================================================================
#  DATA FETCHING & THRESHOLD MANAGEMENT (Feature 6 Custom Threshold)
# =====================================================================
low_stock_limit = int(get_settings_val('low_stock_threshold', '1'))
items_df = get_items_df()
item_name_map = dict(zip(items_df['id'], items_df['name'])) if not items_df.empty else {}

active_borrows = get_active_borrows()
borrowed_item_map = {}
borrower_details_map = {}
for t in active_borrows:
    it_id = t["item_id"]
    q_b = t.get("quantity", 1)
    borrowed_item_map[it_id] = borrowed_item_map.get(it_id, 0) + q_b
    borrower_details_map.setdefault(it_id, []).append(f"{t.get('borrower_name')} ({q_b} ชิ้น)")

is_tech_view = st.session_state.role in TECH_ROLES
abn_statuses = ['ชำรุด', 'อุปกรณ์หมด'] if is_tech_view else ['ชำรุด', 'สูญหาย', 'อุปกรณ์หมด']
abn_title = "อุปกรณ์ชำรุด/กำลังใช้งาน/หมด"

if not items_df.empty:
    abnormal_items = items_df[items_df['status'].isin(abn_statuses) | items_df['status'].str.contains('กำลังใช้งาน', na=False)]
    # Custom threshold per item (Feature 6)
    low_stock_items = items_df[
        (items_df['subcategory'] != 'เครื่องมือช่าง') & 
        (items_df['quantity'] <= items_df.apply(lambda r: r['min_stock'] if r['min_stock'] > 1 else low_stock_limit, axis=1)) &
        (items_df['alert_zero'] != 1)
    ]
else:
    abnormal_items = pd.DataFrame()
    low_stock_items = pd.DataFrame()

borrowed_cnt = len(active_borrows)
abn_cnt, low_cnt = len(abnormal_items), len(low_stock_items)
pending_reqs_all = get_pending_reqs()

# =====================================================================
#  SHARED BORROW / RETURN COMPONENT (Feature 4 Atomic & Feature 5 Excel)
# =====================================================================
def render_borrow_return_system():
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])

    with sub_borrow:
        available_items = items_df[items_df['quantity'] > 0] if not items_df.empty else pd.DataFrame()
        if not available_items.empty:
            with st.form("borrow_form_shared", clear_on_submit=True):
                item_dict = {f"{row['name']} (คงเหลือ: {row['quantity']} ชิ้น)": row['id'] for _, row in available_items.iterrows()}
                sel_item_label = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(item_dict.keys()))
                borrow_qty = st.number_input("จำนวนที่ต้องการยืม *", min_value=1, value=1)
                borrower_name = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                borrow_img_file = st.file_uploader("แนบรูปถ่ายผู้ยืม (ถ้ามี)", type=["jpg", "jpeg", "png"])
                
                if st.form_submit_button("ยืนยันการยืมอุปกรณ์", type="primary"):
                    selected_id = item_dict[sel_item_label]
                    if not borrower_name.strip():
                        st.error("❌ กรุณากรอกชื่อผู้ยืม")
                    else:
                        # Feature 4: Atomic update to prevent race conditions
                        upd_res = db.items.update_one(
                            {"id": selected_id, "quantity": {"$gte": borrow_qty}},
                            {"$inc": {"quantity": -borrow_qty}}
                        )
                        if upd_res.modified_count == 0:
                            st.error("❌ จำนวนคงเหลือในคลังไม่พอ หรือมีการเปลี่ยนแปลงข้อมูลพร้อมกัน")
                        else:
                            b_img_b64 = compress_image_to_base64(borrow_img_file)
                            tx_id = get_next_sequence("transactions_id")
                            db.transactions.insert_one({
                                "id": tx_id, "item_id": selected_id, "borrower_name": borrower_name,
                                "borrow_date": get_now_str("%Y-%m-%d %H:%M"), "return_date": None,
                                "status": "กำลังยืม", "borrower_image": b_img_b64, "quantity": borrow_qty,
                                "giver_name": st.session_state.username
                            })
                            log_audit("BORROW", item_name_map.get(selected_id, str(selected_id)), detail=f"Borrow {borrow_qty} by {borrower_name}")
                            refresh_items()
                            done("บันทึกการยืมเรียบร้อยแล้ว!")
        else:
            st.info("ไม่มีอุปกรณ์ให้ยืมในขณะนี้")

    with sub_return:
        active_txs = get_active_borrows()
        if active_txs:
            for t in active_txs:
                item_name = item_name_map.get(t["item_id"], "Unknown")
                with st.expander(f"📦 อุปกรณ์: {item_name} (จำนวน: {t.get('quantity', 1)}) | ผู้ยืม: {t.get('borrower_name')}"):
                    with st.form(key=f"return_form_{t['id']}"):
                        ret_img_file = st.file_uploader("รูปถ่ายตอนคืน (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"ret_img_{t['id']}")
                        if st.form_submit_button("✅ รับคืนอุปกรณ์รายการนี้", type="primary"):
                            r_img_b64 = compress_image_to_base64(ret_img_file)
                            db.transactions.update_one(
                                {"id": t['id']},
                                {"$set": {"return_date": get_now_str("%Y-%m-%d %H:%M"), "status": "คืนแล้ว", "receiver_name": st.session_state.username, "return_image": r_img_b64}}
                            )
                            tx_qty = int(t.get('quantity', 1))
                            db.items.update_one({"id": t['item_id']}, {"$inc": {"quantity": tx_qty}, "$set": {"status": "ปกติ"}})
                            log_audit("RETURN", item_name, detail=f"Returned {tx_qty} items from {t.get('borrower_name')}")
                            refresh_items()
                            done("รับคืนอุปกรณ์เรียบร้อยแล้ว!")
        else:
            st.info("ไม่มีรายการอุปกรณ์ที่กำลังถูกยืม")

    with sub_history:
        st.markdown("#### ประวัติการยืม-คืนทั้งหมด (แสดง 300 รายการล่าสุด)")
        all_txs = get_tx_history()
        
        # กำหนดโครงสร้างข้อมูลและปิดวงเล็บให้สมบูรณ์
        tx_data = [{
            "รหัส": t["id"],
            "ชื่ออุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
            "จำนวน": t.get("quantity", 1),
            "ผู้ยืม": t.get("borrower_name"),
            "ผู้ให้ยืม": t.get("giver_name"),
            "ผู้รับคืน": t.get("receiver_name"),
            "วันที่ยืม": t.get("borrow_date"),
            "วันที่คืน": t.get("return_date"),
            "สถานะ": t.get("status"),
        } for t in all_txs]  # ตรวจสอบว่ามีวงเล็บเหลี่ยมปิดท้ายตรงนี้ครบถ้วน
        
        tx_history = pd.DataFrame(tx_data)
        st.dataframe(tx_history, use_container_width=True, hide_index=True)