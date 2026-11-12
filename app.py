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
    import extra_streamlit_components as stx
except ImportError:
    stx = None

# =====================================================================
#  KAVE TOWN SHIFT - CENTRAL ENTERPRISE COMMAND & INVENTORY SYSTEM
#  - Admin: ควบคุมครบทุกส่วน (Inventory, ESP8266 Drawer Servo, Water Pump,
#           Fire Alarm + Relay Reset, Growatt Solar + Google Sheets)
#  - Tech: เฉพาะระบบตรวจเช็คอุปกรณ์ช่าง/สระว่ายน้ำ เบิกของ และยืม-คืน (ไม่มี MQTT/Drawer/Water/Fire)
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

# --- IoT defaults: public topics only. All connection data comes from Streamlit Secrets. ---
DEFAULT_IOT_CONFIG = {
    "mqtt_server": "", "mqtt_port": 8883, "mqtt_user": "", "mqtt_pass": "",
    "topic_servo_cmd": "esp8266/servo", "topic_servo_status": "esp8266/servo/status",
    "topic_water": "Water alarm", "topic_check_clients": "CheckClients",
    "topic_fire": "Firealarm", "topic_fire_relay": "nodemcu/control/relay",
    "line_token": "", "line_group_id": "", "growatt_user": "",
    "growatt_pass": "", "growatt_sn": "", "google_webapp_url": "",
}
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
    ("ขวดน้ำยาpH", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 3, "ปกติ", "-", None),
    ("สายดูดตะกอน สั้น+ยาว", "อุปกรณ์สระว่ายน้ำ", "เคมีภัณฑ์", 1, "ปกติ", "-", None),
]

def build_default_docs():
    docs = []
    for idx, i in enumerate(DEFAULT_INITIAL_ITEMS, start=1):
        docs.append({
            "id": idx, "name": i[0], "category": i[1], "subcategory": i[2],
            "quantity": i[3], "orig_quantity": i[3], "status": i[4], "alert_zero": 0, "note": i[5], "image": i[6]
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
        st.error("❌ ไม่พบ `st.secrets['mongo']['uri']` กรุณาตั้งค่าใน `.streamlit/secrets.toml`")
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
    # Keep sessions until explicit logout. Remove the former 30-day TTL index if present.
    session_indexes = database.sessions.index_information()
    for index_name, index_info in session_indexes.items():
        if index_info.get("expireAfterSeconds") is not None:
            database.sessions.drop_index(index_name)
    database.sessions.create_index("created")
    database.user_profiles.create_index("username", unique=True)
    database.iot_logs.create_index([("system", 1), ("datetime", -1)])
    database.audit_logs.create_index([("datetime", -1)])
    database.audit_logs.create_index([("actor", 1), ("datetime", -1)])

    if database.items.count_documents({}, limit=1) == 0:
        database.items.insert_many(build_default_docs())
        database.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
    else:
        database.items.update_many({"orig_quantity": {"$exists": False}}, [{"$set": {"orig_quantity": "$quantity"}}])

    database.settings.update_one({"key": "low_stock_threshold"}, {"$setOnInsert": {"value": "1"}}, upsert=True)
    database.settings.update_one({"key": "global_daily_quota"}, {"$setOnInsert": {"value": "3"}}, upsert=True)
    return database

db = init_mongo()
def log_audit(action, target, before=None, after=None, detail=""):
    """Record security-relevant changes without storing credentials or images."""
    try:
        db.audit_logs.insert_one({
            "datetime": get_now_str(),
            "actor": st.session_state.get("username", "system"),
            "role": st.session_state.get("role", "-"),
            "action": str(action),
            "target": str(target),
            "before": before,
            "after": after,
            "detail": str(detail)[:500],
        })
    except Exception:
        # Audit failures should be visible in server logs without breaking the user action.
        import logging
        logging.exception("Unable to write audit log")

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
    """Read sensitive IoT configuration from Streamlit Secrets only."""
    cfg = DEFAULT_IOT_CONFIG.copy()
    required = {
        "mqtt_server": "mqtt_server", "mqtt_user": "mqtt_user", "mqtt_pass": "mqtt_pass",
        "line_token": "line_token", "line_group_id": "line_group_id",
        "growatt_user": "growatt_user", "growatt_pass": "growatt_pass",
        "growatt_sn": "growatt_sn", "google_webapp_url": "google_webapp_url",
    }
    try:
        secret_cfg = st.secrets.get("iot", {})
    except Exception:
        secret_cfg = {}
    for key in required:
        value = secret_cfg.get(key) if hasattr(secret_cfg, "get") else None
        if value not in (None, ""):
            cfg[key] = str(value)
    port = secret_cfg.get("mqtt_port", cfg["mqtt_port"]) if hasattr(secret_cfg, "get") else cfg["mqtt_port"]
    try:
        cfg["mqtt_port"] = int(port)
    except (TypeError, ValueError):
        cfg["mqtt_port"] = 8883
    # Public topic names may be changed in settings; never load credentials from MongoDB.
    for key in ("topic_servo_cmd", "topic_servo_status", "topic_water", "topic_check_clients", "topic_fire", "topic_fire_relay"):
        saved = get_settings_val(f"iot_{key}", None)
        if saved not in (None, "None", ""):
            cfg[key] = saved
    return cfg
# =====================================================================
#  REAL-TIME MQTT & IOT BACKGROUND ENGINE (ADMIN ONLY)
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
        self.servo_logs = []
        self.water_status = {
            "A": "NORMAL", "B": "NORMAL", "C": "NORMAL", "D": "NORMAL", "UNDERGROUND": "NORMAL"
        }
        self.water_online = {
            "A": True, "B": True, "C": True, "D": True, "UNDERGROUND": True
        }
        self.water_last_msg = "พร้อมทำงาน (Ready)"
        self.fire_status = "CLEAR"
        self.fire_location = "- (ระบบปกติ)"
        self.fire_zones = {
            "A": "NORMAL", "B": "NORMAL", "C": "NORMAL", "D": "NORMAL",
            "CLUB": "NORMAL", "LIBRARY": "NORMAL", "ST": "NORMAL", "UNKNOWN": "NORMAL"
        }
        self.raw_mqtt_feed = []

    def add_feed(self, topic, msg):
        now_s = get_now_str("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.raw_mqtt_feed.insert(0, {"datetime": now_s, "topic": topic, "message": msg})
            if len(self.raw_mqtt_feed) > 150:
                self.raw_mqtt_feed.pop()

    def log_to_db(self, system_name, location, status, raw_msg=""):
        try:
            db.iot_logs.insert_one({
                "datetime": get_now_str("%Y-%m-%d %H:%M:%S"),
                "system": system_name,
                "location": location,
                "status": status,
                "raw": raw_msg
            })
        except Exception:
            pass

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
                if topic == "esp8266/servo/status":
                    self.log_to_db("SERVO", "Drawer Servo D4", msg_up, msg)
            return

        if t_low == "water alarm" or t_low.startswith("water alarm/status/"):
            with self.lock:
                self.water_last_msg = msg
            if t_low.startswith("water alarm/status/"):
                sub = topic.split("/")[-1].upper()
                key = "UNDERGROUND" if "UNDERGROUND" in sub else sub.replace("TRANSFERPUMP", "").strip()
                if key in self.water_status and msg_up in ["ALARM", "NORMAL"]:
                    with self.lock:
                        prev = self.water_status[key]
                        self.water_status[key] = msg_up
                        self.water_online[key] = True
                    if prev != msg_up:
                        self.log_to_db("WATER", key, msg_up, msg)
                return

            if msg_up == "CHECKCLIENTS" or "CHECK ALARM" in msg_up:
                return

            pumps_map = [
                ("TRANSFERPUMPA", "A"), ("TRANSFERPUMPB", "B"),
                ("TRANSFERPUMPC", "C"), ("TRANSFERPUMPD", "D"),
                ("UNDERGROUND PUMP", "UNDERGROUND")
            ]
            for prefix, k in pumps_map:
                if prefix in msg_up:
                    with self.lock:
                        if "OFFLINE" in msg_up:
                            self.water_online[k] = False
                        elif "ONLINE" in msg_up:
                            self.water_online[k] = True
                        else:
                            self.water_online[k] = True
                            new_st = "NORMAL" if "NORMAL" in msg_up else "ALARM"
                            prev = self.water_status.get(k, "NORMAL")
                            self.water_status[k] = new_st
                            if prev != new_st:
                                self.log_to_db("WATER", k, new_st, msg)
                    break
            return

        if t_low in ["firealarm", "fire_alarm"] or "firealarm" in t_low:
            if any(w in msg_up for w in ["RESET", "CLEAR", "NORMAL"]) or "สถานะปกติ" in msg:
                with self.lock:
                    self.fire_status = "CLEAR"
                    self.fire_location = "- (ระบบปกติ)"
                    for zk in self.fire_zones:
                        self.fire_zones[zk] = "NORMAL"
                self.log_to_db("FIRE", msg, "CLEAR", msg)
            else:
                with self.lock:
                    self.fire_status = "ALERT"
                    self.fire_location = msg
                    matched = False
                    if any(x in msg_up for x in ["อาคาร A", "BUILDING A", "BLDGA"]):
                        self.fire_zones["A"] = "ALERT"; matched = True
                    if any(x in msg_up for x in ["อาคาร B", "BUILDING B", "BLDGB"]):
                        self.fire_zones["B"] = "ALERT"; matched = True
                    if any(x in msg_up for x in ["อาคาร C", "BUILDING C", "BLDGC"]):
                        self.fire_zones["C"] = "ALERT"; matched = True
                    if any(x in msg_up for x in ["อาคาร D", "BUILDING D", "BLDGD"]):
                        self.fire_zones["D"] = "ALERT"; matched = True
                    if "สโมสร" in msg or "CLUB" in msg_up or "PAVILION" in msg_up:
                        self.fire_zones["CLUB"] = "ALERT"; matched = True
                    if "ห้องสมุด" in msg or "LIBRARY" in msg_up:
                        self.fire_zones["LIBRARY"] = "ALERT"; matched = True
                    if "ST" in msg_up or "บันไดหนีไฟ" in msg:
                        self.fire_zones["ST"] = "ALERT"; matched = True
                    if not matched:
                        self.fire_zones["UNKNOWN"] = "ALERT"
                self.log_to_db("FIRE", msg, "ALERT", msg)

    def connect(self):
        if mqtt is None:
            self.last_connect_err = "ยังไม่ได้ติดตั้ง paho-mqtt"
            return False
        cfg = get_iot_config()
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

            client.username_pw_set(cfg["mqtt_user"], cfg["mqtt_pass"])
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

            def on_connect(c, userdata, flags, rc):
                if rc == 0:
                    self.connected = True
                    self.last_connect_err = ""
                    c.subscribe([
                        (cfg["topic_servo_cmd"], 0),
                        (cfg["topic_servo_status"], 0),
                        (cfg["topic_water"], 0),
                        ("Water alarm/status/#", 0),
                        (cfg["topic_check_clients"], 0),
                        (cfg["topic_fire"], 0),
                        ("firealarm", 0),
                        ("FireAlarm", 0),
                        ("fire_alarm", 0),
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
#  GROWATT SPF5000ES CLOUD FETCHER & GOOGLE SHEETS SYNC (ADMIN ONLY)
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
    """หา object ที่มี sn/deviceSn/storageSn/serialNum ตรงกับอินเวอร์เตอร์ของเรา (เหมือน findObjBySn ในโค้ด CYD)"""
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
    """เลือกขอบเขต JSON ที่จะอ่านค่า: object ของอินเวอร์เตอร์ตาม SN (ถ้ามีข้อมูลแบตเตอรี่) ไม่เช่นนั้นใช้ทั้งก้อน
    ป้องกันการหยิบค่า Load/Grid จากอุปกรณ์หรือ node อื่นที่อยู่ในคำตอบเดียวกัน"""
    dev = _find_obj_by_sn(j, sn)
    if dev is not None and (_get_f(dev, ["vBat", "vBattery", "vbatSys", "vAkku"]) is not None
                            or _get_f(dev, ["capacity", "soc", "batterySoc"]) is not None):
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
            resp = sess.post(
                url,
                data={"userName": cfg["growatt_user"], "password": pwd_md5},
                headers={"Origin": f"https://{h}", "Referer": f"https://{h}/login"},
                timeout=12
            )
            if resp.status_code == 200:
                j = resp.json()
                if j.get("back", {}).get("success"):
                    logged_in_host = h
                    data_arr = j.get("back", {}).get("data", [])
                    if data_arr and isinstance(data_arr, list):
                        plant_id = str(data_arr[0].get("plantId", ""))
                    break
                else:
                    last_err = f"Login failed on {h}: {j.get('back', {}).get('msg', 'Unknown')}"
            else:
                last_err = f"HTTP {resp.status_code} on {h}"
        except Exception as e:
            last_err = str(e)

    if not logged_in_host:
        return {"ok": False, "error": last_err or "Cannot login to Growatt servers"}

    endpoints = [
        ("GET", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageParams_sacolar&storageId={sn}", None),
        ("GET", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageInfo_sacolar&storageId={sn}", None),
        ("POST", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageParams_sacolar", {"storageId": sn}),
        ("POST", f"https://{logged_in_host}/newStorageAPI.do?op=getStorageInfo_sacolar", {"storageId": sn}),
        ("GET", f"https://{logged_in_host}/newTwoPlantAPI.do?op=getAllDeviceList&plantId={plant_id}&language=1&currPage=1", None),
    ]

    for method, ep_url, body in endpoints:
        try:
            r = sess.post(ep_url, data=body, timeout=12) if method == "POST" else sess.get(ep_url, timeout=12)
            if r.status_code != 200:
                continue
            j = _spf_scope(r.json(), sn)
            vBat = _get_f(j, ["vBat", "vBattery", "vbatSys", "vAkku"])
            soc = _get_f(j, ["capacity", "soc", "batterySoc"])
            if soc is not None and not (0 <= soc <= 100):
                soc = None  # SOC นอกช่วง 0-100 ไม่ใช่ค่าที่ถูกต้อง (เหมือนโค้ด CYD)
            if vBat is None and soc is None:
                continue

            pvV = _get_f(j, ["vPv1", "vPv", "pvVoltage"]) or 0.0
            pvP = _get_f(j, ["ppv1", "pPv1", "ppv", "pvPower", "pCharge1"]) or 0.0
            load = _get_f(j, ["outPutPower", "pLoad", "pLocalLoad", "loadPower", "activePower"]) or 0.0
            loadPct = _get_f(j, ["loadPercent"]) or 0.0
            gridP = _get_f(j, ["pAcInPut"]) or 0.0
            gridV = _get_f(j, ["vGrid"]) or 0.0
            invTemp = _get_f(j, ["invTemperature"]) or 0.0
            pch = _get_f(j, ["pCharge"]) or 0.0
            pdis = _get_f(j, ["pDischarge"]) or 0.0
            iChg = _get_f(j, ["iChargePV1", "iCharge1", "icharge1"])

            vBat = vBat or 0.0
            soc = soc or 0.0
            if iChg and iChg > 0:
                pvI = iChg
            elif pvP > 0 and vBat > 10:
                pvI = pvP / vBat
            elif pvP > 0 and pvV > 1:
                pvI = pvP / pvV
            else:
                pvI = 0.0

            if pdis > 0.5:
                batMode, batP = "DISCHARGING", pdis
            elif pch > 0.5:
                batMode, batP = "CHARGING", pch
            else:
                batMode, batP = "IDLE", 0.0

            result = {
                "ok": True,
                "host": logged_in_host,
                "updated": get_now_str("%Y-%m-%d %H:%M:%S"),
                "vBat": round(vBat, 1),
                "soc": round(soc, 0),
                "pvV": round(pvV, 1),
                "pvI": round(pvI, 1),
                "pvP": round(pvP, 0),
                "load": round(load, 0),
                "loadPct": round(loadPct, 1),
                "gridP": round(gridP, 0),
                "gridV": round(gridV, 0),
                "invTemp": round(invTemp, 1),
                "batMode": batMode,
                "batP": round(batP, 0),
            }

            db.iot_logs.insert_one({
                "datetime": result["updated"],
                "system": "SOLAR",
                "location": sn,
                "status": batMode,
                "data": result
            })

            if sync_sheets and cfg.get("google_webapp_url"):
                try:
                    requests.post(
                        cfg["google_webapp_url"],
                        json={
                            "vBat": result["vBat"],
                            "soc": result["soc"],
                            "pvP": result["pvP"],
                            "pvI": result["pvI"],
                            "load": result["load"]
                        },
                        timeout=10
                    )
                    result["sheets_synced"] = True
                except Exception as ex:
                    result["sheets_synced"] = False
                    result["sheets_err"] = str(ex)

            return result
        except Exception as e:
            last_err = str(e)

    return {"ok": False, "error": last_err or "No SPF5000ES data found"}

# =====================================================================
#  IMAGE & DATABASE HELPER FUNCTIONS
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
        df['alert_zero'] = pd.to_numeric(df.get('alert_zero', 0), errors='coerce').fillna(0).astype(int)
        df['note'] = df['note'].fillna("") if 'note' in df.columns else ""
    return df

def get_display_name(username):
    if not username:
        return ""
    profile = db.user_profiles.find_one({"username": username}, {"_id": 0, "display_name": 1})
    return (profile or {}).get("display_name") or username

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
def get_tx_history(limit=300):
    return list(db.transactions.find({}, {"_id": 0, "borrower_image": 0, "return_image": 0}).sort("id", -1).limit(limit))

@st.cache_data(ttl=600, max_entries=300, show_spinner=False)
def get_tx_image(tx_id):
    d = db.transactions.find_one({"id": tx_id}, {"_id": 0, "borrower_image": 1})
    return b64_to_bytes(d.get("borrower_image")) if d else None

@st.cache_data(ttl=30, show_spinner=False)
def get_inspections_list(limit=1000):
    return list(db.inspections.find({}, {"_id": 0, "photos": 0}).sort("id", -1).limit(limit))

def get_recent_reductions(inspections, days=7):
    """คืนรายการอุปกรณ์ที่ถูกปรับลดจำนวนจากการตรวจเช็ค/แก้ไขในช่วง N วันล่าสุด (ช่าง + สระว่ายน้ำ) เรียงใหม่สุดก่อน"""
    rows = []
    cutoff = pd.Timestamp(get_now_str("%Y-%m-%d %H:%M:%S")) - pd.Timedelta(days=days)
    for rec in inspections:  # inspections เรียงใหม่สุดก่อนอยู่แล้ว
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
                except (KeyError, TypeError, ValueError):
                    continue
        else:
            # ข้อมูลเก่าที่ยังไม่มีฟิลด์ changes: ดึงจากข้อความ "ชื่อ: ปรับจาก X เหลือ Y" (เฉพาะสระว่ายน้ำ)
            txt = str(rec.get("details", "")).split("|")[-1].replace("การเปลี่ยนแปลง:", "")
            for part in txt.split(", "):
                m = re.match(r"^\s*(.*?):\s*ปรับจาก (\d+) เหลือ (\d+)\s*$", part)
                if m and int(m.group(3)) < int(m.group(2)):
                    found.append((m.group(1).strip(), int(m.group(2)), int(m.group(3)), "ปรับจำนวน"))
        for name, old_q, new_q, reason in found:
            rows.append({
                "วันที่ตรวจ": when.strftime("%d/%m/%Y %H:%M"), "อุปกรณ์": name, "หมวดหมู่": cat,
                "จำนวนเดิม": old_q, "จำนวนใหม่": new_q, "ลดลง": old_q - new_q,
                "สาเหตุ": reason or "ปรับจำนวน", "ผู้ตรวจ": get_display_name(rec.get("tech_name", "-")),
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
    u, p = None, None
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

# =====================================================================
#  ALARM ANALYTICS DASHBOARD (Water Alarm / Fire Alarm) - กราฟ Chart.js
# =====================================================================
ALARM_BUCKET_COLORS = ["#ef4444", "#f59e0b", "#3b82f6", "#8b5cf6", "#10b981"]
WATER_ZONES = [("A", "Transferpump A"), ("B", "Transferpump B"), ("C", "Transferpump C"),
               ("D", "Transferpump D"), ("UG", "Pool Ug Pump")]
WATER_ZONE_NAME = dict(WATER_ZONES)
FIRE_ZONE_NAME = {
    "A": "อาคาร A", "B": "อาคาร B", "C": "อาคาร C", "D": "อาคาร D",
    "CLUB": "สโมสร / Pavilion", "LIBRARY": "ห้องสมุด", "ST": "บันไดหนีไฟ (ST Zone)", "UNKNOWN": "ไม่สามารถระบุโซนได้",
}
FIRE_BUCKETS = [("A", "อาคาร A"), ("B", "อาคาร B"), ("C", "อาคาร C"), ("D", "อาคาร D"), ("OTHER", "สโมสร/บันได/อื่นๆ")]
TH_MONTH_OPTS = ["ALL", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
TH_MONTH_NAME = {"ALL": "ทุกเดือน (All Months)", "01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม", "04": "เมษายน",
                 "05": "พฤษภาคม", "06": "มิถุนายน", "07": "กรกฎาคม", "08": "สิงหาคม", "09": "กันยายน",
                 "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม"}

def norm_water_loc(raw_loc):
    """แปลงชื่อจุดตรวจน้ำจากหลายรูปแบบ (A / PUMP A / TransferpumpA / UNDERGROUND / PAVILION) ให้เป็น A,B,C,D,UG"""
    u = str(raw_loc).upper().strip()
    if any(k in u for k in ("UNDERGROUND", "PAVILION", "POOL")):
        return "UG"
    u = re.sub(r"TRANSFERPUMP|PUMP", "", u).strip()
    return u if u in ("A", "B", "C", "D") else (u or "-")

def classify_fire_zone(text):
    """จัดข้อความตำแหน่ง Fire Alarm เข้าโซน A,B,C,D,CLUB,LIBRARY,ST,UNKNOWN"""
    t = str(text)
    u = t.upper()
    for k in ("A", "B", "C", "D"):
        if f"อาคาร {k}" in t or f"BUILDING {k}" in u or f"BLDG{k}" in u:
            return k
    if "สโมสร" in t or "CLUB" in u or "PAVILION" in u:
        return "CLUB"
    if "ห้องสมุด" in t or "LIBRARY" in u:
        return "LIBRARY"
    if "ST" in u or "บันไดหนีไฟ" in t:
        return "ST"
    return "UNKNOWN"


# =====================================================================
#  SOLAR ANALYTICS (ข้อมูลจาก Google Sheets: Solar_Data_Log) - กราฟสไตล์ Neon Glass
# =====================================================================
SOLAR_SHEET_ID_DEFAULT = "1FQHhjrzsnK3a1_StCgb0dbOA_lywbhlDv7TgNHYusF8"
SOLAR_SHEET_GID_DEFAULT = "0"

@st.cache_data(ttl=120, show_spinner=False)
def load_solar_sheet(sheet_id, gid):
    """ดึงชีตเป็น CSV (ชีตต้องแชร์แบบ Anyone with the link = Viewer) คืนค่า (DataFrame|None, ข้อความผิดพลาด)"""
    if requests is None:
        return None, "ยังไม่ได้ติดตั้งไลบรารี requests"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None, f"Google ตอบกลับ HTTP {r.status_code} (ตรวจสอบว่าแชร์ชีตเป็น Anyone with the link)"
        if "text/html" in r.headers.get("Content-Type", ""):
            return None, "ชีตไม่ได้เปิดสาธารณะ (ต้องตั้งค่าแชร์เป็น Anyone with the link: Viewer)"
        return pd.read_csv(io.StringIO(r.content.decode("utf-8-sig"))), ""
    except Exception as e:
        return None, str(e)

def prep_solar_df(df, date_order="auto"):
    """จัดคอลัมน์ Timestamp, Vbat, SOC, PV_Power, PV_Current, Load_Power ให้เป็นตัวเลข/เวลา; date_order: auto | dmy | mdy"""
    d = df.copy()
    d.columns = [str(c).strip().lower() for c in d.columns]
    need = {"timestamp": "ts", "vbat": "vbat", "soc": "soc", "pv_power": "pv", "pv_current": "pvi", "load_power": "load"}
    missing = [k for k in need if k not in d.columns]
    if missing:
        return None, "ไม่พบคอลัมน์: " + ", ".join(missing)
    d = d[list(need.keys())].rename(columns=need)
    for c in ("vbat", "soc", "pv", "pvi", "load"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    ts = d["ts"].astype(str).str.strip()
    dayfirst = True  # ค่าเริ่มต้นแบบไทย วัน/เดือน/ปี
    if date_order == "mdy":
        dayfirst = False
    elif date_order == "auto":
        parts = ts.str.extract(r"^(\d{1,2})/(\d{1,2})/")
        a = pd.to_numeric(parts[0], errors="coerce")
        b = pd.to_numeric(parts[1], errors="coerce")
        if (a > 12).any():
            dayfirst = True
        elif (b > 12).any():
            dayfirst = False
    d["dt"] = pd.to_datetime(ts, dayfirst=dayfirst, errors="coerce")
    d = d.dropna(subset=["dt", "pv", "load"]).sort_values("dt").reset_index(drop=True)
    if d.empty:
        return None, "อ่านวัน-เวลาหรือค่าพลังงานจากชีตไม่ได้"
    return d, ""

def solar_age_seconds(updated_str):
    """อายุของข้อมูลโซลาร์ (วินาที) จากข้อความเวลา YYYY-MM-DD HH:MM:SS; คืน None ถ้าอ่านไม่ได้"""
    try:
        return (pd.Timestamp(get_now_str("%Y-%m-%d %H:%M:%S")) - pd.Timestamp(str(updated_str))).total_seconds()
    except Exception:
        return None

def fmt_age_th(sec):
    sec = max(int(sec), 0)
    if sec < 3600:
        return f"{sec // 60} นาที"
    if sec < 86400:
        return f"{sec // 3600} ชั่วโมง"
    return f"{sec // 86400} วัน"

def get_solar_sheet_df():
    """โหลดข้อมูลชีตโซลาร์ตามค่าที่ตั้งไว้ในกล่อง 'แหล่งข้อมูล' (หรือไฟล์ CSV ที่อัปโหลด) คืนค่า (DataFrame|None, ข้อความผิดพลาด)"""
    sid = (st.session_state.get("solar_sheet_id") or SOLAR_SHEET_ID_DEFAULT).strip()
    gid = (st.session_state.get("solar_sheet_gid") or SOLAR_SHEET_GID_DEFAULT).strip() or "0"
    order = st.session_state.get("solar_date_order", "auto")
    up = st.session_state.get("solar_csv_upload")
    if up is not None:
        try:
            up.seek(0)
            raw_df, err = pd.read_csv(up), ""
        except Exception as e:
            raw_df, err = None, str(e)
    else:
        raw_df, err = load_solar_sheet(sid, gid)
    if raw_df is None:
        return None, err
    return prep_solar_df(raw_df, order)

def _solar_charts_html(spec):
    """กราฟ Neon Glass: เกจครึ่งวงกลม 3 ตัว + Power Flow + แบตเตอรี่ + พลังงานรายชั่วโมง + สมดุลพลังงาน + PV vs Current"""
    payload = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    tpl = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'IBM Plex Sans Thai','Segoe UI',system-ui,sans-serif;}
html,body{overflow:hidden;}
body{background:transparent;color:#f1f5f9;padding:2px;}
.row{display:grid;gap:14px;margin-bottom:14px;}
.r3{grid-template-columns:repeat(3,1fr);}.r2{grid-template-columns:repeat(2,1fr);}.r1{grid-template-columns:1fr;}
@media (max-width:760px){.r3,.r2{grid-template-columns:1fr;}}
.card{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(255,255,255,.09),rgba(14,24,42,.62));border:1px solid rgba(255,255,255,.16);
  border-radius:16px;padding:14px 16px;box-shadow:0 10px 30px rgba(0,10,30,.38),inset 0 1px 0 rgba(255,255,255,.2);animation:up .7s cubic-bezier(.2,.8,.2,1) backwards;}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:var(--ac,#22d3ee);opacity:.8;box-shadow:0 0 14px var(--ac,#22d3ee);}
@keyframes up{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.ttl{font-size:.74rem;color:#cbd5e1;font-weight:600;margin-bottom:6px;letter-spacing:.2px;}
.box{position:relative;width:100%;height:250px;}
.g{height:150px;}
.gv{position:absolute;left:0;right:0;bottom:6px;text-align:center;}
.gv b{font-size:1.55rem;font-weight:800;color:var(--ac);text-shadow:0 0 16px var(--ac);}
.gv span{display:block;font-size:.72rem;color:#94a3b8;margin-top:1px;}
#err{display:none;color:#fbbf24;font-size:.85rem;padding:10px;}
@media (prefers-reduced-motion:reduce){*{animation:none!important;}}
</style></head><body>
<div id="err">⚠️ โหลด Chart.js ไม่สำเร็จ (ต้องเชื่อมต่ออินเทอร์เน็ตเพื่อแสดงกราฟ)</div>
<div class="row r3">
  <div class="card" style="--ac:#34d399;animation-delay:.05s"><div class="ttl" id="gt0"></div><div class="box g"><canvas id="g0"></canvas><div class="gv"><b id="gn0"></b><span id="gs0"></span></div></div></div>
  <div class="card" style="--ac:#fbbf24;animation-delay:.12s"><div class="ttl" id="gt1"></div><div class="box g"><canvas id="g1"></canvas><div class="gv"><b id="gn1"></b><span id="gs1"></span></div></div></div>
  <div class="card" style="--ac:#22d3ee;animation-delay:.19s"><div class="ttl" id="gt2"></div><div class="box g"><canvas id="g2"></canvas><div class="gv"><b id="gn2"></b><span id="gs2"></span></div></div></div>
</div>
<div class="row r1"><div class="card" style="--ac:#fbbf24;animation-delay:.26s"><div class="ttl">POWER FLOW · กำลังไฟจากแผงโซลาร์ เทียบกับโหลดใช้งาน (W)</div><div class="box"><canvas id="c1"></canvas></div></div></div>
<div class="row r2">
  <div class="card" style="--ac:#a78bfa;animation-delay:.33s"><div class="ttl">BATTERY · แรงดันแบตเตอรี่ (V) และ SOC (%)</div><div class="box"><canvas id="c2"></canvas></div></div>
  <div class="card" style="--ac:#22d3ee;animation-delay:.40s"><div class="ttl" id="t3"></div><div class="box"><canvas id="c3"></canvas></div></div>
</div>
<div class="row r2">
  <div class="card" style="--ac:#34d399;animation-delay:.47s"><div class="ttl">ENERGY BALANCE · สมดุลพลังงานของช่วงที่เลือก (kWh)</div><div class="box"><canvas id="c4"></canvas></div></div>
  <div class="card" style="--ac:#f472b6;animation-delay:.54s"><div class="ttl">PV EFFICIENCY · กำลังแผง (W) เทียบกับกระแสชาร์จ (A)</div><div class="box"><canvas id="c5"></canvas></div></div>
</div>
<script>
const S=__PAYLOAD__;
if(typeof Chart==='undefined'){document.getElementById('err').style.display='block';}
else{
Chart.defaults.color='#94a3b8';Chart.defaults.animation={duration:1300,easing:'easeOutQuart'};
const grid={color:'rgba(148,163,184,.13)'};
const tip={backgroundColor:'rgba(8,18,34,.92)',borderColor:'rgba(255,255,255,.2)',borderWidth:1,titleColor:'#f1f5f9',bodyColor:'#cbd5e1',padding:10,cornerRadius:10};
const leg={labels:{color:'#94a3b8',usePointStyle:true,pointStyle:'rectRounded',boxWidth:8,font:{size:11}}};
function grad(ctx,c,a0,a1){const g=ctx.createLinearGradient(0,0,0,250);g.addColorStop(0,c.replace('1)',a0+')'));g.addColorStop(1,c.replace('1)',a1+')'));return g;}
// เกจครึ่งวงกลม
S.gauges.forEach((g,i)=>{
  document.getElementById('gt'+i).textContent=g.title;document.getElementById('gs'+i).textContent=g.sub;
  const out=document.getElementById('gn'+i),t0=performance.now();
  const f=n=>{const p=Math.min(1,(n-t0)/1300),e=1-Math.pow(1-p,3);out.textContent=(g.val*e).toFixed(g.dec)+g.unit;if(p<1)requestAnimationFrame(f);};requestAnimationFrame(f);
  new Chart(document.getElementById('g'+i),{type:'doughnut',data:{datasets:[{data:[Math.min(g.val,g.max),Math.max(g.max-g.val,0)],backgroundColor:[g.color,'rgba(148,163,184,.14)'],borderWidth:0,borderRadius:8}]},
    options:{responsive:true,maintainAspectRatio:false,rotation:-90,circumference:180,cutout:'74%',plugins:{legend:{display:false},tooltip:{enabled:false}}}});
});
const xs={ticks:{color:'#94a3b8',maxRotation:0,autoSkip:true,maxTicksLimit:10},grid:grid};
const ctx1=document.getElementById('c1').getContext('2d');
new Chart(ctx1,{type:'line',data:{labels:S.labels,datasets:[
  {label:'PV Power (W)',data:S.pv,borderColor:'rgba(251,191,36,1)',backgroundColor:grad(ctx1,'rgba(251,191,36,1)','.55','.02'),fill:true,tension:.38,pointRadius:0,pointHoverRadius:5,borderWidth:2.5},
  {label:'Load (W)',data:S.load,borderColor:'rgba(34,211,238,1)',backgroundColor:grad(ctx1,'rgba(34,211,238,1)','.30','.02'),fill:true,tension:.38,pointRadius:0,pointHoverRadius:5,borderWidth:2.5}]},
  options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:leg,tooltip:tip},scales:{x:xs,y:{beginAtZero:true,ticks:{color:'#94a3b8'},grid:grid}}}});
new Chart(document.getElementById('c2'),{type:'line',data:{labels:S.labels,datasets:[
  {label:'Vbat (V)',data:S.vbat,borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,.15)',fill:true,tension:.35,pointRadius:0,pointHoverRadius:5,borderWidth:2.5,yAxisID:'y'},
  {label:'SOC (%)',data:S.soc,borderColor:'#34d399',stepped:true,pointRadius:0,borderWidth:2.5,yAxisID:'y1'}]},
  options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:leg,tooltip:tip},
  scales:{x:xs,y:{ticks:{color:'#c4b5fd'},grid:grid,suggestedMin:S.vmin,suggestedMax:S.vmax},y1:{position:'right',min:0,max:100,ticks:{color:'#6ee7b7'},grid:{drawOnChartArea:false}}}}});
document.getElementById('t3').textContent=S.hourTitle;
new Chart(document.getElementById('c3'),{type:'bar',data:{labels:S.hours,datasets:[
  {label:'PV (kWh)',data:S.hourPv,backgroundColor:'rgba(251,191,36,.85)',borderRadius:6},
  {label:'Load (kWh)',data:S.hourLoad,backgroundColor:'rgba(34,211,238,.85)',borderRadius:6}]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:leg,tooltip:tip},scales:{x:{ticks:{color:'#94a3b8'},grid:{display:false}},y:{beginAtZero:true,ticks:{color:'#94a3b8'},grid:grid}}}});
new Chart(document.getElementById('c4'),{type:'doughnut',data:{labels:S.balLabels,datasets:[{data:S.balData,backgroundColor:['#34d399','#fbbf24','#f87171'],borderColor:'rgba(10,22,40,.9)',borderWidth:3,hoverOffset:8}]},
  options:{responsive:true,maintainAspectRatio:false,cutout:'62%',plugins:{legend:{position:'bottom',labels:leg.labels},tooltip:tip}}});
new Chart(document.getElementById('c5'),{type:'scatter',data:{datasets:[{label:'PV Power vs Current',data:S.scatter,backgroundColor:'rgba(244,114,182,.7)',borderColor:'rgba(244,114,182,1)',pointRadius:4,pointHoverRadius:7}]},
  options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>c.raw.y+' W @ '+c.raw.x+' A'}}},
  scales:{x:{title:{display:true,text:'PV Current (A)',color:'#94a3b8'},ticks:{color:'#94a3b8'},grid:grid},y:{title:{display:true,text:'PV Power (W)',color:'#94a3b8'},ticks:{color:'#94a3b8'},grid:grid}}}});
}
function __fit(){try{const h=Math.ceil(document.body.getBoundingClientRect().height)+8;
  if(window.frameElement){window.frameElement.style.height=h+'px';window.frameElement.setAttribute('height',h);}}catch(e){}}
window.addEventListener('load',__fit);window.addEventListener('resize',__fit);setTimeout(__fit,250);setTimeout(__fit,1400);
</script></body></html>
"""
    return tpl.replace("__PAYLOAD__", payload)

def render_solar_dashboard(d_all):
    """แดชบอร์ดโซลาร์จากชีต: ตัวกรองวัน + KPI + กราฟ Neon Glass + ตารางข้อมูล"""
    import numpy as np
    d_all = d_all.copy()
    d_all["date"] = d_all["dt"].dt.strftime("%Y-%m-%d")
    date_opts = ["ALL"] + sorted(d_all["date"].unique().tolist(), reverse=True)
    c1, c2 = st.columns([1.2, 3])
    sel_date = c1.selectbox("เลือกวันที่ (Date)", date_opts, key="solar_dash_date",
                            format_func=lambda v: "ทุกวันที่มีข้อมูล (All)" if v == "ALL" else v)
    d = d_all if sel_date == "ALL" else d_all[d_all["date"] == sel_date]
    d = d.reset_index(drop=True)
    if d.empty:
        st.info("ไม่มีข้อมูลในวันที่เลือก")
        return
    c2.caption(f"📊 ข้อมูล {len(d):,} จุด · ตั้งแต่ {d['dt'].iloc[0].strftime('%d/%m/%Y %H:%M')} ถึง {d['dt'].iloc[-1].strftime('%d/%m/%Y %H:%M')}")

    # ---- คำนวณพลังงาน (kWh) ด้วย trapezoid; ข้ามช่วงที่ข้อมูลขาดนานเกิน 15 นาที ----
    dt_h = d["dt"].diff().dt.total_seconds().div(3600)
    ok = dt_h.between(0, 0.25)
    pv_avg = (d["pv"] + d["pv"].shift()) / 2
    ld_avg = (d["load"] + d["load"].shift()) / 2
    e_pv = (pv_avg * dt_h).where(ok, 0).fillna(0) / 1000
    e_ld = (ld_avg * dt_h).where(ok, 0).fillna(0) / 1000
    e_direct = (np.minimum(pv_avg, ld_avg) * dt_h).where(ok, 0).fillna(0) / 1000
    e_surplus = (np.maximum(pv_avg - ld_avg, 0) * dt_h).where(ok, 0).fillna(0) / 1000
    e_deficit = (np.maximum(ld_avg - pv_avg, 0) * dt_h).where(ok, 0).fillna(0) / 1000
    tot_pv, tot_ld = float(e_pv.sum()), float(e_ld.sum())
    coverage = (float(e_direct.sum()) / tot_ld * 100) if tot_ld > 0 else 0.0

    i_pk = int(d["pv"].idxmax())
    i_ld = int(d["load"].idxmax())
    last = d.iloc[-1]

    # ---- KPI cards (ตัวเลขนับขึ้นด้วย .cnt เมื่อเป็นจำนวนเต็ม) ----
    def kpi(lbl, icon, val_html, sub, color="#FFFFFF"):
        return (f'<div class="glass-kpi"><div class="top"><span class="lbl">{lbl}</span><span class="ic-badge">{icon}</span></div>'
                f'<div class="val" style="color:{color} !important;">{val_html}</div><div class="sub">{sub}</div></div>')
    cards = "".join([
        kpi("PV PEAK (กำลังแผงสูงสุด)", "☀️", f'<span class="cnt" style="--n:{int(d.loc[i_pk, "pv"])}"></span> W', f'เวลา {d.loc[i_pk, "dt"].strftime("%H:%M")} · กระแส {d.loc[i_pk, "pvi"]:.1f} A', "#FBBF24"),
        kpi("PV ENERGY (พลังงานจากแผง)", "⚡", f'{tot_pv:.2f} kWh', f'เฉลี่ย {d["pv"].mean():.0f} W · สะสมจากข้อมูลที่บันทึก', "#FBBF24"),
        kpi("LOAD ENERGY (พลังงานที่ใช้)", "🏠", f'{tot_ld:.2f} kWh', f'เฉลี่ย {d["load"].mean():.0f} W · พุ่งสูงสุด {int(d.loc[i_ld, "load"])} W @ {d.loc[i_ld, "dt"].strftime("%H:%M")}', "#22D3EE"),
        kpi("SOLAR COVERAGE (แผงรองรับโหลด)", "🌞", f'<span class="cnt" style="--n:{int(round(coverage))}"></span>%', "สัดส่วนโหลดที่แผงจ่ายได้โดยตรง", "#34D399"),
        kpi("BATTERY NOW", "🔋", f'<span class="cnt" style="--n:{int(last["soc"])}"></span>% <span style="font-size:1rem;color:#94A3B8;">({last["vbat"]:.2f} V)</span>', f'แรงดัน {d["vbat"].min():.2f} – {d["vbat"].max():.2f} V', "#A78BFA"),
    ])
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(215px,1fr));">{cards}</div>', unsafe_allow_html=True)

    # ---- เตรียมข้อมูลกราฟ (ลดจุดถ้าเกิน 600 จุดเพื่อให้เบา) ----
    step = max(1, int(np.ceil(len(d) / 600)))
    g = d.iloc[::step]
    multi = d["date"].nunique() > 1
    labels = g["dt"].dt.strftime("%d/%m %H:%M" if multi else "%H:%M").tolist()
    hr = d["dt"].shift().dt.hour  # พลังงานของช่วงเวลา นับเข้าชั่วโมงที่ช่วงนั้นเริ่ม
    hdf = pd.DataFrame({"h": hr, "pv": e_pv, "ld": e_ld}).dropna(subset=["h"])
    hsum = hdf.groupby("h")[["pv", "ld"]].sum()
    hours_idx = list(range(int(hsum.index.min()), int(hsum.index.max()) + 1)) if not hsum.empty else []
    hsum = hsum.reindex(hours_idx, fill_value=0)
    spec = {
        "labels": labels,
        "pv": [round(float(v), 1) for v in g["pv"]], "load": [round(float(v), 1) for v in g["load"]],
        "vbat": [round(float(v), 2) for v in g["vbat"]], "soc": [round(float(v), 0) for v in g["soc"]],
        "vmin": round(float(d["vbat"].min()) - 0.3, 1), "vmax": round(float(d["vbat"].max()) + 0.3, 1),
        "hours": [f"{h:02d}:00" for h in hours_idx],
        "hourPv": [round(float(v), 3) for v in hsum["pv"]], "hourLoad": [round(float(v), 3) for v in hsum["ld"]],
        "hourTitle": "HOURLY ENERGY · พลังงานรายชั่วโมง PV เทียบกับโหลด (kWh)" + (" · รวมทุกวัน" if multi else ""),
        "balLabels": ["แผงจ่ายโหลดโดยตรง", "ส่วนเกิน (ชาร์จแบต)", "ส่วนขาด (ใช้แบต/กริด)"],
        "balData": [round(float(e_direct.sum()), 3), round(float(e_surplus.sum()), 3), round(float(e_deficit.sum()), 3)],
        "scatter": [{"x": round(float(a), 1), "y": round(float(b), 0)} for a, b in zip(g["pvi"], g["pv"])],
        "gauges": [
            {"title": "BATTERY SOC", "val": float(last["soc"]), "max": 100, "unit": "%", "dec": 0, "color": "#34d399", "sub": f'Vbat {last["vbat"]:.2f} V'},
            {"title": "PV POWER NOW", "val": float(last["pv"]), "max": max(float(d["pv"].max()) * 1.15, 1), "unit": " W", "dec": 0, "color": "#fbbf24", "sub": f'เทียบกับค่าสูงสุดของช่วงนี้ ({int(d["pv"].max())} W)'},
            {"title": "AC LOAD NOW", "val": float(last["load"]), "max": 5000, "unit": " W", "dec": 0, "color": "#22d3ee", "sub": "เทียบกับพิกัดอินเวอร์เตอร์ 5,000 W"},
        ],
    }
    chart_html = _solar_charts_html(spec)
    if hasattr(st, "iframe"):
        st.iframe(chart_html, height=1170)
    else:
        components.html(chart_html, height=1170, scrolling=False)

    # ---- ตารางข้อมูล ----
    st.markdown("##### 🗂️ ข้อมูลดิบจากชีต Solar_Data_Log")
    t1, t2 = st.columns([3, 1.2])
    q = t1.text_input("🔍 ค้นหา", key="solar_dash_search", placeholder="พิมพ์วันที่ เวลา หรือค่าที่ต้องการ...", label_visibility="collapsed")
    csv_bytes = d_all[["dt", "vbat", "soc", "pv", "pvi", "load"]].rename(columns={
        "dt": "Timestamp", "vbat": "Vbat", "soc": "SOC", "pv": "PV_Power", "pvi": "PV_Current", "load": "Load_Power"
    }).to_csv(index=False).encode("utf-8-sig")
    t2.download_button("📥 โหลด Solar CSV", data=csv_bytes, file_name="solar_log.csv", mime="text/csv", key="solar_dash_dl", use_container_width=True)
    tv = d.sort_values("dt", ascending=False).copy()
    tv["วัน-เวลา"] = tv["dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if q.strip():
        ql = q.strip().lower()
        tv = tv[tv.astype(str).apply(lambda r: ql in " ".join(r.values).lower(), axis=1)]
    st.dataframe(tv[["วัน-เวลา", "vbat", "soc", "pv", "pvi", "load"]].head(100).rename(columns={
        "vbat": "Vbat (V)", "soc": "SOC (%)", "pv": "PV Power (W)", "pvi": "PV Current (A)", "load": "Load (W)"}),
        hide_index=True, use_container_width=True)
    st.caption(f"แสดง {min(len(tv), 100)} จาก {len(tv):,} รายการล่าสุดตามตัวกรอง")

def show_html_frame(html_str, height):
    """แสดง HTML แบบ self-contained ใน iframe (รองรับ Streamlit ทั้งรุ่นเก่าและใหม่)"""
    if hasattr(st, "iframe"):
        st.iframe(html_str, height=height)
    else:
        components.html(html_str, height=height, scrolling=False)

def _vault_html(state, prev, pending):
    """ตู้เซฟลิ้นชักอัจฉริยะ (CSS+JS): UP = ปลดล็อก/เปิด (0°), DOWN = ล็อก/ปิด (180°)
    เล่นลำดับ: รับคำสั่ง -> เซอร์โวหมุน -> ปลดสลัก -> ประตูเปิด (หรือย้อนกลับ) ทุกครั้งที่สถานะเปลี่ยน"""
    tpl = """
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'IBM Plex Sans Thai','Segoe UI',system-ui,sans-serif;}
body{background:transparent;color:#e2e8f0;padding:2px;}
.wrap{border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:12px;background:linear-gradient(145deg,rgba(255,255,255,.08),rgba(10,26,44,.55));box-shadow:0 10px 30px rgba(0,10,30,.4),inset 0 1px 0 rgba(255,255,255,.18);}
.stage{position:relative;height:290px;border-radius:12px;display:flex;align-items:center;justify-content:center;perspective:1100px;overflow:hidden;
  background:radial-gradient(60% 70% at 50% 40%,rgba(56,189,248,.16),transparent 70%),#0a1624;}
.floor{position:absolute;bottom:0;left:0;right:0;height:36px;background:linear-gradient(180deg,transparent,rgba(56,189,248,.10));}
.safe{position:relative;width:230px;height:236px;border-radius:14px;padding:14px;background:linear-gradient(145deg,#52627a,#1e293b);
  box-shadow:0 18px 34px rgba(0,0,0,.55),inset 0 2px 0 rgba(255,255,255,.2),inset 0 -3px 8px rgba(0,0,0,.4);}
.cav{position:absolute;inset:14px;border-radius:8px;background:#08101c;overflow:hidden;box-shadow:inset 0 0 18px rgba(0,0,0,.8);}
.cav::after{content:"";position:absolute;inset:0;background:radial-gradient(80% 70% at 50% 35%,rgba(125,211,252,.55),rgba(56,189,248,.12) 60%,transparent);opacity:0;transition:opacity .8s;}
.safe.light .cav::after{opacity:1;animation:flick 3s ease-in-out infinite;}
@keyframes flick{0%,100%{filter:brightness(1)}50%{filter:brightness(1.25)}}
.shelf{position:absolute;left:0;right:0;height:3px;background:#334155;}
.s1{top:46%}.s2{top:84%}
.item{position:absolute;font-size:30px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.6));transform:translateY(8px);opacity:.25;transition:all .7s .2s;}
.safe.light .item{opacity:1;transform:none;}
.i1{left:12%;top:14%}.i2{left:44%;top:14%}.i3{left:72%;top:14%}.i4{left:20%;top:55%}.i5{left:58%;top:55%}
.mote{position:absolute;width:3px;height:3px;border-radius:50%;background:#bae6fd;opacity:0;}
.safe.light .mote{animation:float 4s linear infinite;}
.m1{left:25%;top:80%}.m2{left:50%;top:90%;animation-delay:1.2s!important}.m3{left:75%;top:85%;animation-delay:2.2s!important}
@keyframes float{0%{transform:translateY(0);opacity:0}20%{opacity:.9}100%{transform:translateY(-120px);opacity:0}}
.door{position:absolute;inset:14px;border-radius:8px;transform-origin:left center;transition:transform 1.25s cubic-bezier(.65,0,.25,1);
  background:linear-gradient(145deg,#7587a1,#3b4a62);box-shadow:inset 0 2px 0 rgba(255,255,255,.28),inset 0 -3px 10px rgba(0,0,0,.35),4px 0 12px rgba(0,0,0,.35);}
.safe.open .door{transform:rotateY(-112deg);}
.plate{position:absolute;left:50%;top:10px;transform:translateX(-50%);font-size:10px;letter-spacing:2px;color:#cbd5e1;background:rgba(15,23,42,.55);padding:2px 8px;border-radius:4px;}
.dial{position:absolute;left:50%;top:50%;width:84px;height:84px;margin:-38px 0 0 -42px;border-radius:50%;
  background:conic-gradient(from 0deg,#94a3b8,#e2e8f0,#64748b,#cbd5e1,#94a3b8,#e2e8f0,#64748b,#cbd5e1,#94a3b8);
  box-shadow:0 4px 10px rgba(0,0,0,.5),inset 0 0 0 5px #475569,inset 0 0 0 7px rgba(255,255,255,.25);transition:transform 1.3s cubic-bezier(.3,.1,.2,1);}
.dial::before{content:"";position:absolute;inset:26px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#e2e8f0,#475569);box-shadow:0 2px 4px rgba(0,0,0,.5);}
.dial i{position:absolute;left:50%;top:50%;width:6px;height:46px;margin:-23px 0 0 -3px;background:#1e293b;border-radius:3px;}
.dial i:nth-child(2){transform:rotate(60deg)}.dial i:nth-child(3){transform:rotate(120deg)}
.safe.locked .dial{animation:breathe 3s ease-in-out infinite;}
@keyframes breathe{0%,100%{box-shadow:0 4px 10px rgba(0,0,0,.5),inset 0 0 0 5px #475569,0 0 0 0 rgba(248,113,113,0)}50%{box-shadow:0 4px 10px rgba(0,0,0,.5),inset 0 0 0 5px #475569,0 0 14px 3px rgba(248,113,113,.35)}}
.led{position:absolute;right:12px;top:12px;width:13px;height:13px;border-radius:50%;background:#ef4444;box-shadow:0 0 10px #ef4444;transition:background .3s,box-shadow .3s;}
.safe.unlocked .led{background:#34d399;box-shadow:0 0 12px #34d399;}
.safe.working .led{background:#fbbf24;box-shadow:0 0 12px #fbbf24;animation:blink .35s steps(2) infinite;}
@keyframes blink{50%{opacity:.25}}
.bolt{position:absolute;right:-10px;width:20px;height:16px;border-radius:3px;background:linear-gradient(180deg,#e2e8f0,#94a3b8);box-shadow:0 2px 4px rgba(0,0,0,.5);transition:right .55s cubic-bezier(.5,0,.3,1);}
.b1{top:22%}.b2{top:48%}.b3{top:74%}
.safe.unlocked .bolt{right:3px;}
.handle{position:absolute;left:10px;top:50%;width:8px;height:56px;margin-top:-28px;border-radius:4px;background:linear-gradient(90deg,#cbd5e1,#64748b);box-shadow:0 2px 4px rgba(0,0,0,.5);}
.row{display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;align-items:stretch;}
.panel{flex:1;min-width:190px;border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:10px 12px;background:rgba(255,255,255,.05);}
.ttl{font-size:11px;color:#94a3b8;margin-bottom:6px;letter-spacing:.5px;}
.status{display:inline-flex;align-items:center;gap:8px;font-weight:600;font-size:15px;padding:3px 12px;border-radius:999px;border:1px solid;}
.st-lock{color:#fca5a5;border-color:rgba(248,113,113,.5);background:rgba(239,68,68,.14);}
.st-open{color:#6ee7b7;border-color:rgba(52,211,153,.5);background:rgba(16,185,129,.14);}
.st-work{color:#fde68a;border-color:rgba(251,191,36,.5);background:rgba(245,158,11,.14);}
.note{font-size:12px;color:#94a3b8;margin-top:6px;min-height:16px;}
.gauge{position:relative;width:170px;height:124px;margin:0 auto;}
.gauge svg{width:100%;height:96px;overflow:visible;}
.needle{transform-origin:85px 85px;transition:transform 1.4s cubic-bezier(.4,.1,.2,1);}
.ang{position:absolute;left:0;right:0;bottom:0;text-align:center;font-size:19px;font-weight:600;color:#f1f5f9;}
.steps{list-style:none;display:grid;gap:5px;font-size:12.5px;color:#94a3b8;}
.steps li{display:flex;align-items:center;gap:8px;transition:color .3s;}
.steps li::before{content:"";width:9px;height:9px;border-radius:50%;background:#334155;transition:all .3s;flex:none;}
.steps li.on{color:#fde68a;}.steps li.on::before{background:#fbbf24;box-shadow:0 0 8px #fbbf24;}
.steps li.done{color:#a7f3d0;}.steps li.done::before{background:#34d399;}
button{margin-top:8px;font:inherit;font-size:12.5px;color:#e2e8f0;cursor:pointer;padding:6px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.26);background:linear-gradient(180deg,rgba(255,255,255,.16),rgba(10,30,52,.4));}
button:hover{border-color:rgba(186,230,253,.7);}
.laser{position:absolute;left:8%;right:8%;top:6%;height:2px;border-radius:2px;background:linear-gradient(90deg,transparent,#38bdf8,transparent);box-shadow:0 0 14px #38bdf8;opacity:0;pointer-events:none;z-index:5;}
.stage.scan .laser{opacity:1;animation:scan 1.1s ease-in-out infinite alternate;}
@keyframes scan{from{top:6%}to{top:92%}}
.stamp{position:absolute;top:12px;left:50%;transform:translateX(-50%);padding:4px 16px;border:2px solid;border-radius:8px;font-weight:700;letter-spacing:3px;font-size:14px;opacity:0;pointer-events:none;z-index:6;}
.stamp.ok{color:#6ee7b7;border-color:#34d399;background:rgba(16,185,129,.16);}
.stamp.lk{color:#fca5a5;border-color:#f87171;background:rgba(239,68,68,.16);}
.stamp.show{animation:stampIn 1.7s ease forwards;}
@keyframes stampIn{0%{opacity:0;transform:translateX(-50%) scale(1.9)}14%{opacity:1;transform:translateX(-50%) scale(1)}78%{opacity:1}100%{opacity:0;transform:translateX(-50%) scale(1)}}
.safe.shake{animation:shake .38s;}
@keyframes shake{0%,100%{transform:none}20%{transform:translateX(-5px)}40%{transform:translateX(5px)}60%{transform:translateX(-3px)}80%{transform:translateX(3px)}}
.chips{display:grid;gap:5px;font-size:12px;}
.chip{display:flex;align-items:center;gap:7px;color:#cbd5e1;animation:chipIn .5s ease backwards;}
.chip b{font-weight:600;padding:1px 8px;border-radius:999px;font-size:11px;border:1px solid;}
.chip b.u{color:#6ee7b7;border-color:rgba(52,211,153,.5);}.chip b.d{color:#fca5a5;border-color:rgba(248,113,113,.5);}
.chip span{color:#94a3b8;}
@keyframes chipIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition-duration:.01s!important;}}
</style></head><body><div class="wrap">
<div class="stage" id="stage"><div class="floor"></div><div class="laser"></div><div class="stamp" id="stamp"></div>
  <div class="safe locked" id="safe">
    <div class="cav"><div class="shelf s1"></div><div class="shelf s2"></div>
      <div class="item i1">🔧</div><div class="item i2">🔨</div><div class="item i3">🪛</div><div class="item i4">📦</div><div class="item i5">🔦</div>
      <div class="mote m1"></div><div class="mote m2"></div><div class="mote m3"></div></div>
    <div class="door"><div class="plate">SMART DRAWER</div><div class="led"></div>
      <div class="dial" id="dial"><i></i><i></i><i></i></div><div class="handle"></div>
      <div class="bolt b1"></div><div class="bolt b2"></div><div class="bolt b3"></div></div>
  </div>
</div>
<div class="row">
  <div class="panel"><div class="ttl">สถานะตู้</div><span class="status st-lock" id="st">LOCK · ล็อกอยู่</span><div class="note" id="note"></div>
    <button id="demo">▶ ทดสอบอนิเมชัน (ไม่ส่งคำสั่งจริง)</button> <button id="snd">🔇 เสียง: ปิด</button></div>
  <div class="panel"><div class="ttl">มุมเซอร์โว (SERVO ANGLE)</div>
    <div class="gauge"><svg viewBox="0 0 170 96"><path d="M10 85 A75 75 0 0 1 160 85" fill="none" stroke="#1e293b" stroke-width="12" stroke-linecap="round"/>
      <path d="M10 85 A75 75 0 0 1 85 10" fill="none" stroke="#34d399" stroke-width="12" stroke-linecap="round" opacity=".85"/>
      <path d="M85 10 A75 75 0 0 1 160 85" fill="none" stroke="#f87171" stroke-width="12" stroke-linecap="round" opacity=".85"/>
      <g class="needle" id="needle"><line x1="85" y1="85" x2="24" y2="85" stroke="#f1f5f9" stroke-width="3" stroke-linecap="round"/><circle cx="85" cy="85" r="6" fill="#f1f5f9"/></g></svg>
      <div class="ang" id="ang">180°</div></div></div>
  <div class="panel"><div class="ttl">ลำดับการทำงาน</div>
    <ul class="steps" id="steps"><li>1 รับคำสั่ง MQTT</li><li>2 เซอร์โวหมุน</li><li>3 ปลดสลัก/ใส่สลัก</li><li>4 ประตูเปิด/ปิด</li></ul></div>
</div></div>
<script>
const STATE="__STATE__",PREV="__PREV__",PENDING=__PENDING__;
const safe=document.getElementById('safe'),st=document.getElementById('st'),note=document.getElementById('note'),
  needle=document.getElementById('needle'),ang=document.getElementById('ang'),dial=document.getElementById('dial'),
  steps=[...document.querySelectorAll('#steps li')];
let cur=PREV,busy=false,angle=PREV==='UP'?0:180,dialDeg=0;
const stage=document.getElementById('stage'),stampEl=document.getElementById('stamp'),sndBtn=document.getElementById('snd');
let sndOn=false,ac=null;
function beep(f,d,type,vol){if(!sndOn)return;try{ac=ac||new (window.AudioContext||window.webkitAudioContext)();const o=ac.createOscillator(),g=ac.createGain();
  o.type=type||'sine';o.frequency.value=f;g.gain.value=vol||.05;o.connect(g);g.connect(ac.destination);o.start();g.gain.exponentialRampToValueAtTime(.0001,ac.currentTime+d);o.stop(ac.currentTime+d);}catch(e){}}
function whirr(){for(let i=0;i<8;i++)setTimeout(()=>beep(280+i*45,.12,'sawtooth',.02),i*130);}
function clunk(){beep(90,.28,'square',.08);}
function stamp(ok){stampEl.className='stamp '+(ok?'ok':'lk');stampEl.textContent=ok?'ACCESS GRANTED':'LOCKED';void stampEl.offsetWidth;stampEl.classList.add('show');}
function shake(){safe.classList.remove('shake');void safe.offsetWidth;safe.classList.add('shake');}
sndBtn.addEventListener('click',()=>{sndOn=!sndOn;sndBtn.textContent=sndOn?'🔊 เสียง: เปิด':'🔇 เสียง: ปิด';beep(660,.12,'sine',.05);});
function setStatus(kind,txt){st.className='status '+kind;st.textContent=txt;}
function setStep(n){steps.forEach((li,i)=>{li.className=i<n?'done':(i===n?'on':'');});}
function tween(to,ms){const from=angle,t0=performance.now();angle=to;needle.style.transform='rotate('+to+'deg)';
  const f=now=>{const p=Math.min(1,(now-t0)/ms),e=1-Math.pow(1-p,3);ang.textContent=Math.round(from+(to-from)*e)+'°';if(p<1)requestAnimationFrame(f);};requestAnimationFrame(f);}
function spin(d){dialDeg+=d;dial.style.transform='rotate('+dialDeg+'deg)';}
function statics(s){
  const up=s==='UP';safe.classList.toggle('open',up);safe.classList.toggle('unlocked',up);safe.classList.toggle('light',up);safe.classList.toggle('locked',!up);
  needle.style.transform='rotate('+(up?0:180)+'deg)';ang.textContent=(up?0:180)+'°';
  setStatus(up?'st-open':'st-lock',up?'OPEN · เปิดอยู่':'LOCK · ล็อกอยู่');steps.forEach(li=>li.className=PENDING?'':'done');
}
function run(target,cb){
  if(busy)return;busy=true;const opening=target==='UP';
  safe.classList.add('working');stage.classList.add('scan');beep(880,.1,'sine',.05);setStatus('st-work',opening?'กำลังเปิด…':'กำลังล็อก…');note.textContent='';setStep(0);
  const T=(ms,f)=>setTimeout(f,ms);
  if(opening){
    T(500,()=>{setStep(1);tween(0,1400);spin(720);whirr();});
    T(1500,()=>{setStep(2);safe.classList.add('unlocked');clunk();});
    T(2100,()=>{setStep(3);safe.classList.add('open');safe.classList.remove('locked');beep(180,.5,'triangle',.05);});
    T(2900,()=>{safe.classList.add('light');});
    T(3500,()=>{safe.classList.remove('working');stage.classList.remove('scan');setStatus('st-open','OPEN · เปิดอยู่');setStep(4);stamp(true);beep(660,.12,'sine',.06);setTimeout(()=>beep(990,.2,'sine',.06),140);cur='UP';busy=false;cb&&cb();});
  }else{
    T(400,()=>{setStep(3);safe.classList.remove('light');});
    T(700,()=>{safe.classList.remove('open');});
    T(2100,()=>{setStep(2);safe.classList.remove('unlocked');safe.classList.add('locked');clunk();shake();});
    T(2600,()=>{setStep(1);tween(180,1400);spin(-720);whirr();});
    T(4100,()=>{safe.classList.remove('working');stage.classList.remove('scan');setStatus('st-lock','LOCK · ล็อกอยู่');setStep(4);stamp(false);beep(220,.3,'square',.06);cur='DOWN';busy=false;cb&&cb();});
  }
}
function waitNote(){if(PENDING){note.textContent='ส่งคำสั่งแล้ว รอ ESP8266 ยืนยันสถานะ…';}}
statics(PREV);
if(STATE!==PREV){setTimeout(()=>run(STATE,waitNote),500);}else{waitNote();}
document.getElementById('demo').addEventListener('click',()=>{if(!busy){run(cur==='UP'?'DOWN':'UP',()=>{note.textContent='(โหมดทดสอบ: ยังไม่ได้สั่งบอร์ดจริง)';});}});
</script></body></html>
"""
    return (tpl.replace("__STATE__", "UP" if state == "UP" else "DOWN")
               .replace("__PREV__", "UP" if prev == "UP" else "DOWN")
               .replace("__PENDING__", "true" if pending else "false"))


def _alarm_charts_html(spec):
    """สร้าง HTML กราฟ 4 ช่อง (Bar / Doughnut / Line / Hourly Bar) ด้วย Chart.js ตามแบบแดชบอร์ดตัวอย่าง"""
    payload = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    tpl = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  *{margin:0;padding:0;box-sizing:border-box;font-family:'IBM Plex Sans Thai','Segoe UI',system-ui,sans-serif;}
  html,body{overflow:hidden;}
  body{background:transparent;color:#f1f5f9;padding:2px;}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;}
  @media (max-width:700px){.grid{grid-template-columns:1fr;}}
  .card{background:linear-gradient(145deg,rgba(255,255,255,0.08),rgba(21,28,44,0.62));border:1px solid rgba(255,255,255,0.16);
        border-radius:14px;padding:14px 16px;box-shadow:0 8px 26px rgba(0,10,30,0.35),inset 0 1px 0 rgba(255,255,255,0.18);}
  .ttl{font-size:0.74rem;color:#cbd5e1;font-weight:600;margin-bottom:6px;}
  .box{position:relative;height:250px;width:100%;}
  #err{display:none;color:#fbbf24;font-size:0.85rem;padding:10px;}
</style></head><body>
<div id="err">⚠️ โหลด Chart.js ไม่สำเร็จ (ต้องเชื่อมต่ออินเทอร์เน็ตเพื่อแสดงกราฟ)</div>
<div class="grid">
  <div class="card"><div class="ttl" id="t1"></div><div class="box"><canvas id="c1"></canvas></div></div>
  <div class="card"><div class="ttl" id="t2"></div><div class="box"><canvas id="c2"></canvas></div></div>
  <div class="card"><div class="ttl" id="t3"></div><div class="box"><canvas id="c3"></canvas></div></div>
  <div class="card"><div class="ttl" id="t4"></div><div class="box"><canvas id="c4"></canvas></div></div>
</div>
<script>
const S = __PAYLOAD__;
['t1','t2','t3','t4'].forEach((id,i)=>{document.getElementById(id).textContent=S.titles[i];});
if (typeof Chart === 'undefined') { document.getElementById('err').style.display='block'; }
else {
  Chart.defaults.color = '#94a3b8';
  const grid = {color:'rgba(148,163,184,0.16)'};
  const opts = (noScale) => ({
    responsive:true, maintainAspectRatio:false,
    plugins:{legend:{labels:{color:'#94a3b8',font:{size:11}}}},
    scales: noScale ? {} : {
      x:{ticks:{color:'#94a3b8',maxRotation:0,autoSkip:true},grid:grid},
      y:{beginAtZero:true,ticks:{color:'#94a3b8',precision:0},grid:grid}
    }
  });
  new Chart(document.getElementById('c1'),{type:'bar',
    data:{labels:S.labels,datasets:[{label:S.l1,data:S.counts,backgroundColor:S.colors,borderRadius:6}]},options:opts(false)});
  new Chart(document.getElementById('c2'),{type:'doughnut',
    data:{labels:S.labels,datasets:[{data:S.counts,backgroundColor:S.colors,borderWidth:2,borderColor:'#151c2c'}]},options:opts(true)});
  new Chart(document.getElementById('c3'),{type:'line',
    data:{labels:S.dates,datasets:[{label:S.l3,data:S.dateCounts,borderColor:S.trendColor,backgroundColor:S.trendFill,fill:true,tension:0.3}]},options:opts(false)});
  new Chart(document.getElementById('c4'),{type:'bar',
    data:{labels:S.hours,datasets:[{label:S.l4,data:S.hourCounts,backgroundColor:S.hourColor,borderRadius:4}]},options:opts(false)});
}
function __fit(){try{const h=Math.ceil(document.body.getBoundingClientRect().height)+8;
  if(window.frameElement){window.frameElement.style.height=h+'px';window.frameElement.setAttribute('height',h);}}catch(e){}}
window.addEventListener('load',__fit);window.addEventListener('resize',__fit);setTimeout(__fit,250);setTimeout(__fit,1400);
</script></body></html>
"""
    return tpl.replace("__PAYLOAD__", payload)

def render_alarm_dashboard(kind, df):
    """แดชบอร์ดสถิติ Water Alarm (kind='water') / Fire Alarm (kind='fire'): ตัวกรอง + KPI 3 ใบ + กราฟ 4 ช่อง + ตารางประวัติ"""
    is_fire = kind == "fire"
    p = f"{kind}_dash"
    if df is None or df.empty:
        st.info("ยังไม่มีประวัติสัญญาณแจ้งเตือนอัคคีภัยในฐานข้อมูล" if is_fire else "ยังไม่มีข้อมูลประวัติระดับน้ำในฐานข้อมูล")
        return

    d = df.copy()
    for col in ("datetime", "location", "status"):
        if col not in d.columns:
            d[col] = ""
    d["dt"] = pd.to_datetime(d["datetime"], errors="coerce")
    d = d.dropna(subset=["dt"]).copy()
    if d.empty:
        st.warning("พบข้อมูลแต่รูปแบบวัน-เวลาอ่านไม่ได้ (ต้องเป็น YYYY-MM-DD HH:MM:SS)")
        return
    d["year"] = d["dt"].dt.strftime("%Y")
    d["month"] = d["dt"].dt.strftime("%m")
    d["date"] = d["dt"].dt.strftime("%Y-%m-%d")
    d["hour"] = d["dt"].dt.hour
    d["status"] = d["status"].astype(str).str.upper().str.strip()
    d["loc_text"] = d["location"].astype(str).str.replace(r"\s*\n\s*", " ", regex=True).str.strip()
    d["zone"] = d["loc_text"].map(classify_fire_zone) if is_fire else d["location"].map(norm_water_loc)
    inc_word = "ALERT" if is_fire else "ALARM"

    # ---------- แถบตัวกรอง ----------
    year_opts = ["ALL"] + sorted(d["year"].unique().tolist(), reverse=True)
    zone_opts = ["ALL"] + (list(FIRE_ZONE_NAME.keys()) if is_fire else [z for z, _ in WATER_ZONES])
    zone_name = FIRE_ZONE_NAME if is_fire else WATER_ZONE_NAME
    status_opts = ["ALL", "ALERT", "CLEAR"] if is_fire else ["ALL", "ALARM", "NORMAL"]

    def _reset_filters():
        for k in ("year", "month", "zone", "status"):
            st.session_state[f"{p}_{k}"] = "ALL"
        st.session_state[f"{p}_search"] = ""

    c1, c2, c3, c4, c5 = st.columns([1, 1.1, 1.3, 1, 0.9])
    sel_year = c1.selectbox("กรองตามปี (Year)", year_opts, key=f"{p}_year",
                            format_func=lambda v: "ทุกปี (All Years)" if v == "ALL" else v)
    sel_month = c2.selectbox("กรองตามเดือน (Month)", TH_MONTH_OPTS, key=f"{p}_month",
                             format_func=lambda v: TH_MONTH_NAME[v])
    sel_zone = c3.selectbox("อาคาร/โซน (Zone)" if is_fire else "ตำแหน่ง (Location)", zone_opts, key=f"{p}_zone",
                            format_func=lambda v: ("ทุกสถานที่ (All Areas)" if is_fire else "ทั้งหมด (All Pumps)") if v == "ALL" else zone_name.get(v, v))
    sel_status = c4.selectbox("สถานะ (Status)", status_opts, key=f"{p}_status",
                              format_func=lambda v: "ทุกสถานะ (All Status)" if v == "ALL" else v)
    c5.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
    c5.button("🔄 ล้างการกรอง", key=f"{p}_reset", on_click=_reset_filters, use_container_width=True)

    f = d
    if sel_year != "ALL":
        f = f[f["year"] == sel_year]
    if sel_month != "ALL":
        f = f[f["month"] == sel_month]
    if sel_zone != "ALL":
        f = f[f["zone"] == sel_zone]
    if sel_status != "ALL":
        f = f[f["status"].str.contains(sel_status, na=False)]
    inc = f[f["status"].str.contains(inc_word, na=False)]

    # ---------- สรุปตัวเลข ----------
    if is_fire:
        bucket_keys = [k for k, _ in FIRE_BUCKETS]
        bucket_names = [n for _, n in FIRE_BUCKETS]
        bucket_series = inc["zone"].where(inc["zone"].isin(["A", "B", "C", "D"]), "OTHER")
    else:
        bucket_keys = [k for k, _ in WATER_ZONES]
        bucket_names = [n for _, n in WATER_ZONES]
        bucket_series = inc["zone"]
    counts = [int((bucket_series == k).sum()) for k in bucket_keys]

    if sum(counts) > 0:
        top_i = max(range(len(counts)), key=lambda i: counts[i])
        top_txt = f"{bucket_names[top_i]} ({counts[top_i]} ครั้ง)"
    else:
        top_txt = "-"
    if not inc.empty:
        hc = inc["hour"].value_counts()
        ph, pn = int(hc.idxmax()), int(hc.max())
        peak_txt = f"{ph:02d}:00 - {ph:02d}:59 น. ({pn} ครั้ง)"
    else:
        peak_txt = "-"

    if is_fire:
        kpis = [
            ("จำนวนการเตือนภัย (FIRE INCIDENT COUNT)", str(len(inc)), "#ff334b", "จำนวนครั้งที่ตรวจพบอัคคีภัยตามตัวกรอง"),
            ("อาคาร/โซนเสี่ยงสูงสุด (MOST TRIGGERED ZONE)", top_txt, "#f59e0b", "พื้นที่ที่ส่งสัญญาณอลามบ่อยที่สุด"),
            ("ช่วงเวลาเกิดเหตุสูงสุด (PEAK ALARM HOUR)", peak_txt, "#8b5cf6", "ชั่วโมงในรอบวันที่เกิดเหตุบ่อยที่สุด"),
        ]
    else:
        kpis = [
            ("จำนวนการแจ้งเตือน (FILTERED WATER ALARMS)", str(len(inc)), "#00f2fe", "จำนวนครั้งที่เกิด Alarm ในช่วงที่เลือก"),
            ("จุดเสี่ยงแจ้งเตือนสูงสุด (MOST FREQUENT)", top_txt, "#f59e0b", "ตำแหน่งที่มีอัตราการเกิด Alarm สูงสุด"),
            ("ช่วงเวลาเสี่ยงสูง (PEAK ALARM HOUR)", peak_txt, "#8b5cf6", "ชั่วโมงในรอบวันที่เกิด Alarm ถี่ที่สุด"),
        ]
    cards = "".join(
        f'<div class="glass-kpi"><div class="top"><span class="lbl">{esc(lbl)}</span></div>'
        f'<div class="val" style="color:{col} !important;">{esc(val)}</div><div class="sub">{esc(sub)}</div></div>'
        for lbl, val, col, sub in kpis
    )
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(250px,1fr));">{cards}</div>', unsafe_allow_html=True)

    # ---------- กราฟ 4 ช่อง ----------
    day_counts = inc["date"].value_counts().sort_index()
    hour_counts = [int((inc["hour"] == h).sum()) for h in range(24)]
    if is_fire:
        titles = ["1. สถิติการเกิดเหตุแยกตามอาคาร (FIRE INCIDENTS BY BUILDING)",
                  "2. สัดส่วน % การแจ้งเตือนแต่ละอาคาร (BUILDING ALARM DISTRIBUTION)",
                  "3. แนวโน้มการแจ้งเตือนตามวัน (FIRE INCIDENTS TIMELINE)",
                  "4. ช่วงเวลาการเกิด FIRE ALARM ในรอบวัน (PEAK HOUR ANALYSIS)"]
        labels3 = ("จำนวนเหตุการณ์เตือนภัย", "จำนวนเหตุการณ์ต่อวัน", "ความถี่ Fire Alarm แต่ละชั่วโมง")
        trend_c, trend_f, hour_c = "#ff416c", "rgba(255, 65, 108, 0.12)", "#ff4b2b"
    else:
        titles = ["1. จำนวนครั้งการแจ้งเตือนแยกตามจุด (WATER ALARM COUNT)",
                  "2. สัดส่วนเปอร์เซ็นต์การเกิด ALARM (WATER ALARM DISTRIBUTION %)",
                  "3. แนวโน้มการแจ้งเตือนตามช่วงเวลา (TIMELINE TREND)",
                  "4. ช่วงเวลาการเกิด ALARM ในรอบวัน (PEAK HOUR 00:00 - 23:00)"]
        labels3 = ("จำนวนครั้งที่แจ้งเตือน", "จำนวน Alarm ต่อวัน", "ความถี่การเกิด Alarm ในแต่ละชั่วโมง")
        trend_c, trend_f, hour_c = "#00f2fe", "rgba(0, 242, 254, 0.12)", "#8b5cf6"
    spec = {
        "titles": titles, "labels": bucket_names, "counts": counts, "colors": ALARM_BUCKET_COLORS,
        "l1": labels3[0], "l3": labels3[1], "l4": labels3[2],
        "dates": day_counts.index.tolist(), "dateCounts": [int(v) for v in day_counts.values],
        "hours": [f"{h:02d}:00" for h in range(24)], "hourCounts": hour_counts,
        "trendColor": trend_c, "trendFill": trend_f, "hourColor": hour_c,
    }
    chart_html = _alarm_charts_html(spec)  # ข้อมูลในกราฟเป็นตัวเลข/ชื่อมาตรฐานเท่านั้น ไม่ใส่ข้อความดิบจาก MQTT
    if hasattr(st, "iframe"):
        st.iframe(chart_html, height=650)  # Streamlit รุ่นใหม่ (components.html ถูกเลิกใช้)
    else:
        components.html(chart_html, height=650, scrolling=False)

    # ---------- ตารางประวัติ ----------
    st.markdown(f"##### {'ประวัติบันทึกสัญญาณแจ้งเตือนอัคคีภัย (Fire Alarm Log History)' if is_fire else 'ประวัติการบันทึกระดับน้ำ (Water Level Incident History)'}")
    t1, t2 = st.columns([3, 1.2])
    q = t1.text_input("🔍 ค้นหาในตาราง", key=f"{p}_search", placeholder="พิมพ์วันที่ ตำแหน่ง หรือสถานะ...", label_visibility="collapsed")
    full_csv = df[[c for c in ("datetime", "location", "status") if c in df.columns]].rename(
        columns={"datetime": "DateTime", "location": "Location", "status": "Status"}
    ).to_csv(index=False).encode("utf-8-sig")
    t2.download_button("📥 โหลด Fire CSV" if is_fire else "📥 โหลด CSV ทั้งหมด", data=full_csv,
                       file_name="fire_log.csv" if is_fire else "water_log.csv", mime="text/csv",
                       key=f"{p}_dl", use_container_width=True)

    t = f.sort_values("dt", ascending=False)
    if is_fire:
        disp = t["loc_text"]  # Fire: แสดงข้อความตำแหน่งเต็ม (อาคาร/ชั้น/โซน)
    else:
        disp = t["zone"].map(lambda z: zone_name.get(z, ""))  # Water: แสดงชื่อปั๊มมาตรฐาน
        disp = disp.where(disp != "", t["loc_text"])
    t = t.assign(disp=disp)
    if q.strip():
        ql = q.strip().lower()
        mask = (t["datetime"].astype(str).str.lower().str.contains(ql, regex=False) |
                t["disp"].str.lower().str.contains(ql, regex=False) |
                t["status"].str.lower().str.contains(ql, regex=False))
        t = t[mask]
    shown = t.head(50)
    if shown.empty:
        st.info("ไม่พบประวัติการแจ้งเตือนตามเงื่อนไข")
    else:
        view = pd.DataFrame({
            "วัน-เวลา (Date Time)": shown["datetime"].astype(str).values,
            "อาคาร / ชั้น / โซน (Location Details)" if is_fire else "ตำแหน่ง (Location)": shown["disp"].values,
            "สถานะ (Status)": [("🔴 " if inc_word in s_ else "🟢 ") + s_ for s_ in shown["status"]],
        })
        st.dataframe(view, hide_index=True, use_container_width=True)
        st.caption(f"แสดง {len(shown)} จาก {len(t)} รายการล่าสุดตามตัวกรอง (สูงสุด 50 รายการ)")


def keyed_container(key, **kwargs):
    try:
        return st.container(key=key, **kwargs)
    except TypeError:
        return st.container(**kwargs)

def switch_role(new_role):
    st.session_state.role = new_role
    st.session_state.original_role = ROLE_ADMIN
    tk = st.session_state.get("token")
    if tk:
        db.sessions.update_one({"token": tk}, {"$set": {"role": new_role}})
    st.rerun()

# =====================================================================
#  ADMIN DASHBOARD V2 - COOL OCEAN GLASSMORPHISM UI (NO ORANGE SELECTED BG)
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
  color-scheme: dark;
  --bg-main: #08121E;
  --bg-mesh:
    radial-gradient(at 15% 10%, rgba(14, 165, 233, 0.20) 0px, transparent 52%),
    radial-gradient(at 85% 15%, rgba(56, 189, 248, 0.14) 0px, transparent 48%),
    radial-gradient(at 50% 90%, rgba(20, 184, 166, 0.10) 0px, transparent 55%),
    linear-gradient(160deg, #07101C 0%, #0C1B2E 55%, #081320 100%);
  --glass-surface: rgba(16, 30, 48, 0.65);
  --glass-surface-strong: rgba(13, 24, 40, 0.84);
  --glass-border: rgba(148, 163, 184, 0.16);
  --glass-border-active: rgba(56, 189, 248, 0.55);
  --ink: #F8FAFC;
  --muted: #94A3B8;
  --cyan: #38BDF8;
  --sky: #0EA5E9;
  --teal: #14B8A6;
  --ok: #10B981;
  --warn: #F59E0B;
  --bad: #EF4444;
}

.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp input, .stApp textarea, .stApp button, .stApp [data-baseweb="tab"], .stApp [data-baseweb="select"] {
  font-family: 'IBM Plex Sans Thai', 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
  color: var(--ink) !important;
}

.stApp {
  background-color: var(--bg-main) !important;
  background-image: var(--bg-mesh) !important;
  background-attachment: fixed !important;
  color: var(--ink);
}

header[data-testid="stHeader"] { background: transparent !important; height: 1.4rem !important; }
footer { visibility: hidden !important; display: none !important; }
#MainMenu { visibility: hidden !important; display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }

.block-container {
  padding-top: 0.65rem !important;
  padding-bottom: 3rem !important;
  max-width: 1380px !important;
}

/* --- SIDEBAR: ADMIN DASHBOARD V2 FROSTED SLATE-BLUE --- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(10, 21, 36, 0.92) 0%, rgba(7, 15, 27, 0.96) 100%) !important;
  border-right: 1px solid var(--glass-border) !important;
  backdrop-filter: blur(22px) !important;
}

.brand-box {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 0.9rem; margin-bottom: 0.75rem;
  border-radius: 14px;
  background: rgba(14, 165, 233, 0.10);
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.brand-logo {
  width: 2.35rem; height: 2.35rem; border-radius: 10px;
  background: linear-gradient(135deg, #0EA5E9, #2563EB);
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 1.15rem; color: #fff;
  box-shadow: 0 4px 14px rgba(14, 165, 233, 0.35);
}
.brand-title { font-weight: 800; font-size: 0.95rem; letter-spacing: 0.3px; color: #F8FAFC; line-height: 1.15; }
.brand-sub { font-size: 0.72rem; color: #94A3B8; }

.user-card {
  display: flex; align-items: center; gap: .75rem; padding: .7rem .85rem;
  border: 1px solid var(--glass-border); border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  margin-bottom: 0.75rem;
}
.avatar {
  width: 2.3rem; height: 2.3rem; border-radius: 50%;
  background: rgba(56, 189, 248, 0.18);
  border: 1px solid rgba(56, 189, 248, 0.45);
  color: #38BDF8 !important; display: flex; align-items: center; justify-content: center;
  font-weight: 800; flex: none;
}
.u-name { font-weight: 700; font-size: 0.9rem; color: #F8FAFC; }
.u-role { font-size: 0.74rem; color: var(--muted); }

/* Sidebar Radio Navigation - Clean Translucent Pill (No Orange!) */
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
  padding: 0.52rem 0.75rem !important;
  border-radius: 10px !important;
  margin-bottom: 0.22rem !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  transition: all 0.16s ease !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
  background: rgba(255, 255, 255, 0.04) !important;
  border-color: rgba(148, 163, 184, 0.14) !important;
}
section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
  background: rgba(56, 189, 248, 0.13) !important;
  border: 1px solid rgba(56, 189, 248, 0.42) !important;
  box-shadow: inset 3px 0 0 #38BDF8 !important;
}

/* --- TOP BAR / HERO CARD --- */
.app-hero {
  background: var(--glass-surface);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 0.85rem 1.2rem;
  border: 1px solid var(--glass-border);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.25);
  display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; flex-wrap: wrap;
  margin-bottom: 0.85rem;
}
.app-hero .t { font-size: 1.18rem; font-weight: 800; color: #FFFFFF; letter-spacing: 0.2px; }
.app-hero .s { font-size: 0.78rem; color: #94A3B8; margin-top: 0.12rem; }
.badge-row { display: flex; gap: 0.45rem; align-items: center; flex-wrap: wrap; }
.status-pill-top {
  padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.73rem; font-weight: 600;
  display: inline-flex; align-items: center; gap: 0.35rem;
  border: 1px solid var(--glass-border); background: rgba(15, 23, 42, 0.6);
}
.status-pill-top.ok { color: #34D399 !important; border-color: rgba(16, 185, 129, 0.38); background: rgba(16, 185, 129, 0.10); }
.status-pill-top.warn { color: #FBBF24 !important; border-color: rgba(245, 158, 11, 0.38); background: rgba(245, 158, 11, 0.10); }
.status-pill-top.bad { color: #F87171 !important; border-color: rgba(239, 68, 68, 0.45); background: rgba(239, 68, 68, 0.14); }
.status-pill-top.info { color: #38BDF8 !important; border-color: rgba(56, 189, 248, 0.38); background: rgba(56, 189, 248, 0.10); }

/* --- GLASSY KPI CARDS (Admin Dashboard V2 Style) --- */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.glass-kpi {
  background: linear-gradient(145deg, rgba(22, 38, 60, 0.62) 0%, rgba(14, 25, 42, 0.76) 100%);
  backdrop-filter: blur(18px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 0.95rem 1.05rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: transform 0.18s ease, border-color 0.18s ease;
}
.glass-kpi:hover {
  transform: translateY(-2px);
  border-color: rgba(56, 189, 248, 0.38);
}
.glass-kpi .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
.glass-kpi .lbl { font-size: 0.74rem; color: #94A3B8; font-weight: 600; }
.glass-kpi .ic-badge {
  width: 1.85rem; height: 1.85rem; border-radius: 9px;
  background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.24);
  display: flex; align-items: center; justify-content: center; font-size: 0.9rem;
}
.glass-kpi .val { font-size: 1.55rem; font-weight: 800; color: #FFFFFF; line-height: 1.15; }
.glass-kpi .sub { font-size: 0.73rem; color: #94A3B8; margin-top: 0.28rem; }

/* --- IOT STATUS CARDS --- */
.iot-card {
  background: var(--glass-surface);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  padding: 0.85rem 1rem;
  box-shadow: 0 4px 18px rgba(0,0,0,0.2);
}
.iot-card .hd { font-size: 0.71rem; color: var(--muted); text-transform: uppercase; font-weight: 700; margin-bottom: 0.4rem; }
.iot-card .bd { display: flex; justify-content: space-between; align-items: center; }
.iot-card .nm { font-size: 0.94rem; font-weight: 700; color: #F8FAFC; }
.pill {
  padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.73rem; font-weight: 700;
  display: inline-block;
}
.pill-normal { background: rgba(16, 185, 129, 0.14); color: #34D399 !important; border: 1px solid rgba(16, 185, 129, 0.45); }
.pill-alarm {
  background: rgba(239, 68, 68, 0.20); color: #FCA5A5 !important; border: 1px solid rgba(239, 68, 68, 0.55);
  animation: pulse-red 1.5s infinite;
}
.pill-off { background: rgba(148, 163, 184, 0.12); color: #94A3B8 !important; border: 1px solid rgba(148, 163, 184, 0.3); }

@keyframes pulse-red {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.45); }
  50% { box-shadow: 0 0 0 7px rgba(239, 68, 68, 0); }
}

/* --- TABS (NO ORANGE BACKGROUND! Clean Frosted Glass Pill + Cyan Indicator) --- */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
  background: rgba(11, 22, 36, 0.68);
  padding: 0.32rem;
  border-radius: 12px;
  border: 1px solid var(--glass-border);
  overflow-x: auto;
  flex-wrap: nowrap;
}
.stTabs [data-baseweb="tab"] {
  height: auto;
  padding: 0.45rem 0.95rem;
  border-radius: 9px;
  font-weight: 500;
  color: #94A3B8 !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  white-space: nowrap;
  transition: all 0.16s ease;
}
.stTabs [data-baseweb="tab"]:hover {
  color: #E2E8F0 !important;
  background: rgba(255, 255, 255, 0.04) !important;
}
.stTabs [aria-selected="true"] {
  background: transparent !important;
  color: #FFFFFF !important;
  border: 1px solid transparent !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
.stTabs [data-baseweb="tab-highlight"] {
  background-color: transparent !important;
  display: none !important;
}

/* --- EXPANDERS, FORMS, TABLES & BUTTONS --- */
[data-testid="stExpander"] {
  border: 1px solid var(--glass-border) !important;
  border-radius: 12px !important;
  background: var(--glass-surface) !important;
  backdrop-filter: blur(14px) !important;
  margin-bottom: 0.42rem !important;
}
[data-testid="stForm"] {
  border: 1px solid var(--glass-border) !important;
  border-radius: 14px !important;
  background: var(--glass-surface) !important;
  backdrop-filter: blur(16px) !important;
  padding: 0.9rem !important;
}
[data-testid="stDataFrame"], .stTable {
  border: 1px solid var(--glass-border) !important;
  border-radius: 12px !important;
  overflow-x: auto !important;
}

.stApp button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  border: 1px solid var(--glass-border) !important;
  background: rgba(20, 35, 56, 0.72) !important;
  transition: all 0.16s ease !important;
}
.stApp button:hover {
  border-color: rgba(56, 189, 248, 0.45) !important;
  background: rgba(28, 48, 76, 0.85) !important;
}
.stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%) !important;
  border: 1px solid rgba(125, 211, 252, 0.35) !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.32) !important;
}
.stApp button[kind="primary"]:hover, .stApp button[data-testid="stBaseButton-primary"]:hover,
.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.req-banner {
  display: flex; align-items: center; gap: .9rem; padding: 0.7rem 1rem; margin-bottom: 0.75rem;
  border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.45);
  background: linear-gradient(90deg, rgba(14, 116, 144, 0.35), rgba(15, 23, 42, 0.75));
}

/* =================================================================
   OCEAN GLASSMORPHISM LAYER - ชั้นเสริมความเป็นกระจกใสสีมหาสมุทร
   ================================================================= */
:root {
  --ocean-glass: linear-gradient(145deg, rgba(56, 189, 248, 0.10) 0%, rgba(14, 38, 64, 0.55) 45%, rgba(8, 24, 42, 0.62) 100%);
  --ocean-edge: rgba(186, 230, 253, 0.22);
  --ocean-glow: 0 10px 34px rgba(2, 20, 40, 0.45), 0 0 0 1px rgba(125, 211, 252, 0.05);
  --ocean-shine: inset 0 1px 0 rgba(255, 255, 255, 0.14), inset 0 -1px 0 rgba(125, 211, 252, 0.05);
}

/* พื้นหลังน้ำทะเลลึก + ลูกแสงลอยช้าๆ เหมือนแสงใต้น้ำ */
.stApp::before {
  content: ""; position: fixed; inset: -10%; z-index: 0; pointer-events: none;
  background:
    radial-gradient(38% 32% at 12% 18%, rgba(34, 211, 238, 0.20), transparent 70%),
    radial-gradient(34% 30% at 88% 12%, rgba(56, 189, 248, 0.18), transparent 70%),
    radial-gradient(40% 34% at 70% 88%, rgba(20, 184, 166, 0.16), transparent 70%),
    radial-gradient(30% 26% at 22% 82%, rgba(59, 130, 246, 0.14), transparent 70%);
  filter: blur(18px);
  animation: oceanDrift 28s ease-in-out infinite alternate;
}
@keyframes oceanDrift {
  0%   { transform: translate3d(0, 0, 0) scale(1); }
  100% { transform: translate3d(-2.5%, 2%, 0) scale(1.06); }
}
.block-container, section[data-testid="stSidebar"], header[data-testid="stHeader"] { position: relative; z-index: 1; }

/* การ์ดกระจกใส: เบลอแรง + เส้นขอบสว่างด้านบน + เงาลึก */
.app-hero, .glass-kpi, .iot-card, .user-card, .brand-box,
[data-testid="stExpander"], [data-testid="stForm"], .req-banner {
  background: var(--ocean-glass) !important;
  backdrop-filter: blur(24px) saturate(165%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(165%) !important;
  border: 1px solid var(--ocean-edge) !important;
  box-shadow: var(--ocean-glow), var(--ocean-shine) !important;
}
.app-hero, .glass-kpi { border-radius: 20px !important; position: relative; overflow: hidden; }
/* เงาสะท้อนผิวกระจกเฉียงมุมบนซ้าย */
.app-hero::after, .glass-kpi::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.10) 0%, rgba(255, 255, 255, 0) 38%);
}
.glass-kpi:hover {
  transform: translateY(-3px);
  border-color: rgba(125, 211, 252, 0.50) !important;
  box-shadow: 0 14px 38px rgba(2, 20, 40, 0.5), 0 0 22px rgba(56, 189, 248, 0.16), var(--ocean-shine) !important;
}
.glass-kpi .ic-badge {
  background: linear-gradient(145deg, rgba(125, 211, 252, 0.22), rgba(14, 165, 233, 0.08)) !important;
  border: 1px solid rgba(186, 230, 253, 0.30) !important;
  backdrop-filter: blur(8px);
}

/* Sidebar กระจกฝ้า */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(12, 32, 54, 0.62) 0%, rgba(6, 16, 30, 0.78) 100%) !important;
  backdrop-filter: blur(28px) saturate(150%) !important;
  border-right: 1px solid var(--ocean-edge) !important;
}

/* แท็บ: แถบกระจกใส */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(10, 26, 44, 0.45) !important;
  backdrop-filter: blur(20px) saturate(150%) !important;
  border: 1px solid var(--ocean-edge) !important;
  border-radius: 14px !important;
  box-shadow: var(--ocean-shine) !important;
}

/* ปุ่มกระจก + ปุ่มหลักไล่สีน้ำทะเลมีประกาย */
.stApp button {
  background: linear-gradient(180deg, rgba(125, 211, 252, 0.12), rgba(14, 38, 64, 0.55)) !important;
  border: 1px solid var(--ocean-edge) !important;
  backdrop-filter: blur(12px) !important;
  box-shadow: var(--ocean-shine) !important;
}
.stApp button:hover {
  border-color: rgba(125, 211, 252, 0.55) !important;
  box-shadow: 0 0 18px rgba(56, 189, 248, 0.20), var(--ocean-shine) !important;
}
.stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.85) 0%, rgba(14, 165, 233, 0.90) 50%, rgba(37, 99, 235, 0.88) 100%) !important;
  border: 1px solid rgba(186, 230, 253, 0.45) !important;
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
}

/* ช่องกรอกข้อมูล / Dropdown / ตาราง: กระจกใส */
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="textarea"], .stApp textarea {
  background: rgba(8, 22, 40, 0.50) !important;
  border-color: rgba(148, 163, 184, 0.22) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(10px) !important;
}
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="select"] > div:focus-within, .stApp textarea:focus {
  border-color: rgba(125, 211, 252, 0.65) !important;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.14) !important;
}
[data-testid="stDataFrame"], .stTable {
  border: 1px solid var(--ocean-edge) !important;
  border-radius: 14px !important;
  background: rgba(8, 22, 40, 0.35) !important;
  box-shadow: var(--ocean-shine) !important;
}
[data-testid="stAlert"] {
  border-radius: 14px !important;
  backdrop-filter: blur(16px) saturate(150%) !important;
  border: 1px solid var(--ocean-edge) !important;
}

/* =================================================================
   GLASS PLUS - กระจกใสมากขึ้น: โปร่งแสงกว่าเดิม เห็นฉากหลังทะลุ มีประกายผิว
   ================================================================= */
:root {
  --g-fill: linear-gradient(135deg, rgba(255, 255, 255, 0.13) 0%, rgba(125, 211, 252, 0.06) 38%, rgba(10, 30, 52, 0.26) 100%);
  --g-edge: rgba(255, 255, 255, 0.24);
  --g-shadow: 0 14px 44px rgba(0, 12, 32, 0.52), inset 0 1px 0 rgba(255, 255, 255, 0.38), inset 1px 0 0 rgba(255, 255, 255, 0.10), inset 0 -1px 0 rgba(125, 211, 252, 0.10), inset 0 0 28px rgba(125, 211, 252, 0.05);
}

/* ฉากหลังใต้น้ำสว่างขึ้น ให้กระจกมีอะไรให้เบลอ */
.stApp::before {
  background:
    radial-gradient(34% 30% at 10% 14%, rgba(34, 211, 238, 0.34), transparent 70%),
    radial-gradient(30% 28% at 90% 10%, rgba(56, 189, 248, 0.30), transparent 70%),
    radial-gradient(38% 32% at 72% 90%, rgba(20, 184, 166, 0.28), transparent 70%),
    radial-gradient(28% 26% at 18% 84%, rgba(59, 130, 246, 0.26), transparent 70%),
    radial-gradient(22% 20% at 50% 48%, rgba(103, 232, 249, 0.14), transparent 70%) !important;
  filter: blur(14px) !important;
}
/* ฟองอากาศโปร่งแสงลอยขึ้นช้าๆ */
.stApp::after {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(circle at 8% 88%, rgba(255,255,255,0.20) 0 1.5px, rgba(186,230,253,0.07) 2px 26px, transparent 27px),
    radial-gradient(circle at 24% 62%, rgba(255,255,255,0.16) 0 1px, rgba(186,230,253,0.06) 1.5px 16px, transparent 17px),
    radial-gradient(circle at 78% 74%, rgba(255,255,255,0.18) 0 1.5px, rgba(186,230,253,0.07) 2px 34px, transparent 35px),
    radial-gradient(circle at 92% 38%, rgba(255,255,255,0.14) 0 1px, rgba(186,230,253,0.05) 1.5px 14px, transparent 15px),
    radial-gradient(circle at 55% 20%, rgba(255,255,255,0.14) 0 1px, rgba(186,230,253,0.05) 1.5px 20px, transparent 21px);
  animation: bubbleRise 40s linear infinite alternate;
}
@keyframes bubbleRise {
  0%   { transform: translateY(3%); }
  100% { transform: translateY(-4%); }
}

/* การ์ด/กล่องทั้งหมด: กระจกโปร่ง เบลอลึก ขอบสว่างเป็นประกาย */
.app-hero, .glass-kpi, .iot-card, .user-card, .brand-box,
[data-testid="stExpander"], [data-testid="stForm"], .req-banner {
  background: var(--g-fill) !important;
  backdrop-filter: blur(30px) saturate(190%) brightness(1.06) !important;
  -webkit-backdrop-filter: blur(30px) saturate(190%) brightness(1.06) !important;
  border: 1px solid var(--g-edge) !important;
  border-top-color: rgba(255, 255, 255, 0.40) !important;
  border-left-color: rgba(255, 255, 255, 0.30) !important;
  box-shadow: var(--g-shadow) !important;
}
.app-hero::after, .glass-kpi::after {
  background:
    linear-gradient(115deg, rgba(255, 255, 255, 0.22) 0%, rgba(255, 255, 255, 0.05) 26%, rgba(255, 255, 255, 0) 46%),
    radial-gradient(120% 60% at 0% 0%, rgba(255, 255, 255, 0.10), transparent 60%) !important;
}
.glass-kpi:hover {
  border-color: rgba(186, 230, 253, 0.65) !important;
  box-shadow: 0 18px 48px rgba(0, 12, 32, 0.55), 0 0 28px rgba(103, 232, 249, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.45) !important;
}
.glass-kpi .ic-badge {
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.26), rgba(56, 189, 248, 0.10)) !important;
  border: 1px solid rgba(255, 255, 255, 0.34) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.40) !important;
}

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(10, 30, 52, 0.46) 100%) !important;
  backdrop-filter: blur(34px) saturate(190%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.20) !important;
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.06) !important;
}

.stTabs [data-baseweb="tab-list"] {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.10), rgba(10, 30, 52, 0.30)) !important;
  backdrop-filter: blur(26px) saturate(180%) !important;
  border: 1px solid rgba(255, 255, 255, 0.22) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.30), 0 8px 26px rgba(0, 12, 32, 0.35) !important;
}

.stApp button {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(125, 211, 252, 0.06) 55%, rgba(10, 30, 52, 0.34)) !important;
  border: 1px solid rgba(255, 255, 255, 0.26) !important;
  backdrop-filter: blur(16px) saturate(170%) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.34), 0 4px 14px rgba(0, 12, 32, 0.30) !important;
}
.stApp button:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.26), rgba(125, 211, 252, 0.12) 55%, rgba(10, 30, 52, 0.30)) !important;
  border-color: rgba(186, 230, 253, 0.65) !important;
}
.stApp button[kind="primary"], .stApp button[data-testid="stBaseButton-primary"],
.stApp button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.34) 0%, rgba(56, 189, 248, 0.62) 40%, rgba(14, 116, 190, 0.74) 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.50) !important;
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.55) !important;
}

.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="textarea"], .stApp textarea {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(8, 22, 40, 0.32)) !important;
  border: 1px solid rgba(255, 255, 255, 0.20) !important;
  backdrop-filter: blur(14px) saturate(160%) !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.18) !important;
}
[data-testid="stDataFrame"], .stTable {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.20) !important;
  backdrop-filter: blur(20px) saturate(160%) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 8px 26px rgba(0, 12, 32, 0.30) !important;
}
[data-testid="stAlert"] {
  background-image: linear-gradient(135deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.02)) !important;
  backdrop-filter: blur(22px) saturate(180%) !important;
  border: 1px solid rgba(255, 255, 255, 0.22) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.26) !important;
}

/* =================================================================
   INPUT TEXT FIX - แก้ข้อความในช่องกรอก (รวมถึงรหัสผ่านหน้า Login) มองไม่เห็นบนเครื่องที่ใช้ธีมสว่าง
   ================================================================= */
.stApp { color-scheme: dark; }
.stApp input, .stApp textarea,
.stApp [data-baseweb="input"] input, .stApp [data-baseweb="base-input"] input,
.stApp [data-baseweb="textarea"] textarea {
  background: transparent !important;            /* ไม่ให้ธีมสว่างทับพื้นกระจกด้วยสีขาว */
  color: #F1F5F9 !important;
  -webkit-text-fill-color: #F1F5F9 !important;   /* บังคับสีตัวอักษร/จุดรหัสผ่านบน iOS/Safari */
  caret-color: #7DD3FC !important;
}
.stApp input::placeholder, .stApp textarea::placeholder {
  color: #94A3B8 !important;
  -webkit-text-fill-color: #94A3B8 !important;
  opacity: 1 !important;
}
/* เบราว์เซอร์เติมรหัสอัตโนมัติ (autofill) ปกติจะเปลี่ยนพื้นเป็นสีสว่าง */
.stApp input:-webkit-autofill, .stApp input:-webkit-autofill:hover, .stApp input:-webkit-autofill:focus {
  -webkit-text-fill-color: #F1F5F9 !important;
  caret-color: #7DD3FC !important;
  -webkit-box-shadow: 0 0 0 1000px rgba(12, 30, 52, 0.96) inset !important;
  transition: background-color 9999s ease-in-out 0s;
}
/* ไอคอนตา (แสดง/ซ่อนรหัส), ปุ่ม +/- ของ number input */
.stApp [data-baseweb="input"] button, .stApp [data-baseweb="base-input"] button {
  background: transparent !important; box-shadow: none !important; border: none !important;
}
.stApp [data-baseweb="input"] svg, .stApp [data-baseweb="base-input"] svg, .stApp [data-baseweb="select"] svg {
  fill: #CBD5E1 !important; color: #CBD5E1 !important;
}
/* Dropdown (selectbox) ทั้งค่าที่เลือกและรายการที่เด้งขึ้นมา */
.stApp [data-baseweb="select"] div, .stApp [data-baseweb="select"] span { color: #F1F5F9 !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul[role="listbox"] {
  background: rgba(12, 30, 52, 0.96) !important; color: #F1F5F9 !important;
}
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: #F1F5F9 !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: rgba(56, 189, 248, 0.18) !important; }
/* ป้ายชื่อช่องกรอก */
.stApp label, .stApp [data-testid="stWidgetLabel"] p { color: #E2E8F0 !important; }

/* =================================================================
   MOTION LAYER - อนิเมชั่นเบาๆ ทั้งแอป (CSS ล้วน ไม่รีเฟรชอัตโนมัติ)
   1 ไล่ขึ้นทีละใบ  2 ตัวเลขนับขึ้น  3 ยกตัว+แสงกวาด  4 จุดสถานะกะพริบ  5 เด้งเมื่อค่าเปลี่ยน  6 แสงใต้น้ำลอย
   * Streamlit วาด HTML ใหม่เมื่อข้อความเปลี่ยน อนิเมชั่นจึงเล่นซ้ำเองเมื่อค่าเปลี่ยน
   ================================================================= */
@property --num { syntax: "<integer>"; initial-value: 0; inherits: false; }
.cnt { --num: 0; animation: cntUp 1.1s cubic-bezier(.2,.8,.2,1) forwards; counter-reset: cn var(--num); }
.cnt::after { content: counter(cn); }
@keyframes cntUp { from { --num: 0; } to { --num: var(--n); } }

@keyframes riseIn { from { opacity: 0; transform: translateY(16px) scale(.97); } to { opacity: 1; transform: none; } }
.app-hero, .glass-kpi, .iot-card, .req-banner, [data-testid="stExpander"], [data-testid="stAlert"], [data-testid="stDataFrame"] {
  animation: riseIn .6s cubic-bezier(.2,.8,.2,1) backwards;
}
.kpi-grid > .glass-kpi:nth-child(1), [data-testid="stColumn"]:nth-child(1) .iot-card { animation-delay: .05s; }
.kpi-grid > .glass-kpi:nth-child(2), [data-testid="stColumn"]:nth-child(2) .iot-card { animation-delay: .14s; }
.kpi-grid > .glass-kpi:nth-child(3), [data-testid="stColumn"]:nth-child(3) .iot-card { animation-delay: .23s; }
.kpi-grid > .glass-kpi:nth-child(4), [data-testid="stColumn"]:nth-child(4) .iot-card { animation-delay: .32s; }
.kpi-grid > .glass-kpi:nth-child(5), [data-testid="stColumn"]:nth-child(5) .iot-card { animation-delay: .41s; }
.kpi-grid > .glass-kpi:nth-child(6) { animation-delay: .50s; }

/* ยกตัว + แสงเฉียงกวาดผ่านผิวกระจกเมื่อชี้เมาส์ */
.glass-kpi, .iot-card { position: relative; overflow: hidden; transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease; }
.glass-kpi:hover, .iot-card:hover { transform: translateY(-4px); }
.glass-kpi::before, .iot-card::before {
  content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%; pointer-events: none; z-index: 2;
  background: linear-gradient(105deg, transparent, rgba(255,255,255,.20), transparent); transform: skewX(-18deg);
}
.glass-kpi:hover::before, .iot-card:hover::before { animation: sheen .9s ease; }
@keyframes sheen { to { left: 130%; } }

/* ตัวเลขหลักเด้งเข้ามา (เล่นซ้ำเมื่อค่าเปลี่ยน) */
.glass-kpi .val { animation: valPop .7s cubic-bezier(.2,1.4,.4,1) backwards; animation-delay: .12s; display: block; }
@keyframes valPop { 0% { transform: scale(1.14); filter: brightness(1.5); } 100% { transform: none; filter: none; } }

/* จุดสถานะกะพริบ: ปกติ = เขียววงแหวนขยาย, ALARM = แดงเรืองกะพริบ */
.pill-normal::before, .status-pill-top.ok::before, .status-pill-top.info::before {
  content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: 1px;
  background: currentColor; animation: dotRing 1.8s ease-out infinite;
}
.status-pill-top.bad, .status-pill-top.warn { animation: pulse-red 1.5s infinite; }
@keyframes dotRing { 0% { box-shadow: 0 0 0 0 currentColor; } 70% { box-shadow: 0 0 0 7px transparent; } 100% { box-shadow: 0 0 0 0 transparent; } }

/* แท็บ: เนื้อหาเฟดเข้า */
.stTabs [role="tabpanel"] { animation: riseIn .45s ease backwards; }

/* คนที่ตั้งค่าลดการเคลื่อนไหว / เครื่องช้า: ปิดอนิเมชั่น และแสดงตัวเลขจริงทันที */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .cnt { --num: var(--n); }
}

/* =================================================================
   IOT CARD OVERFLOW FIX - ชื่อ/ป้ายสถานะไม่ล้นการ์ด: ตัดบรรทัดอัตโนมัติ ป้ายสถานะลงบรรทัดใหม่เมื่อที่ไม่พอ
   ================================================================= */
.iot-card { min-height: 6rem; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; }
.iot-card .hd { overflow-wrap: anywhere; }
.iot-card .bd { flex-wrap: wrap; gap: 0.35rem 0.6rem; align-items: center; justify-content: space-between; min-width: 0; }
.iot-card .nm { flex: 1 1 6rem; min-width: 0; line-height: 1.3; overflow-wrap: anywhere; word-break: break-word; }
.iot-card .pill { flex: none; white-space: nowrap; max-width: 100%; }

@media (max-width:768px){
  .block-container { padding-left: .4rem !important; padding-right: .4rem !important; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 0.45rem; }
  .glass-kpi .val { font-size: 1.25rem; }
}
</style>
""", unsafe_allow_html=True)

# =====================================================================
#  LOGIN STATE & SESSION RESTORATION
# =====================================================================
# --- Password hashing for technician accounts (stdlib PBKDF2-HMAC-SHA256) ---
PASSWORD_HASH_ROUNDS = 310000

def hash_user_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_HASH_ROUNDS).hex()
    return f"pbkdf2${PASSWORD_HASH_ROUNDS}${salt}${digest}"

def verify_user_password(password, stored):
    """Return (valid, is_legacy_plaintext). Upgrade legacy credentials after successful login."""
    stored = str(stored or "")
    if stored.startswith("pbkdf2$"):
        try:
            _, rounds, salt, expected = stored.split("$", 3)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(rounds)).hex()
            return secrets.compare_digest(actual, expected), False
        except (ValueError, TypeError):
            return False, False
    return secrets.compare_digest(password, stored), True
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""
    st.session_state.original_role = None
    st.session_state.token = None

if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0

LS_KEY = "inv_token"
local_store = LocalStorage() if LocalStorage is not None else None
cookie_manager = None
saved_cookie_token = None
if stx is not None:
    try:
        cookie_manager = stx.CookieManager(key="login_cookie_manager")
        saved_cookie_token = cookie_manager.get(cookie=LS_KEY)
    except Exception:
        cookie_manager = None
saved_token = None
if local_store is not None:
    try:
        saved_token = local_store.getItem(LS_KEY)
    except Exception:
        saved_token = None

if not st.session_state.logged_in:
    cand_token = st.query_params.get("token") or saved_cookie_token or saved_token
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
            if cookie_manager is not None and saved_cookie_token != sess["token"]:
                try:
                    cookie_manager.set(cookie=LS_KEY, val=sess["token"], expires_at=datetime.now() + timedelta(days=3650))
                except Exception:
                    pass
        else:
            st.query_params.clear()
            if saved_token and local_store is not None:
                try:
                    local_store.deleteItem(LS_KEY, key="ls_del_token")
                except Exception:
                    pass

_flash = st.session_state.pop("_flash", None)
if _flash:
    st.toast(_flash[0], icon=_flash[1])

if st.session_state.get("token") and saved_token != st.session_state.token and local_store is not None:
    try:
        local_store.setItem(LS_KEY, st.session_state.token, key="ls_set_token")
    except Exception:
        pass

# =====================================================================
#  LOGIN SCREEN (IF NOT LOGGED IN)
# =====================================================================
if not st.session_state.logged_in or not st.session_state.role or st.session_state.role == "None":
    _, col_login, _ = st.columns([1, 1.45, 1])
    with col_login:
        st.markdown("""
        <div class="app-hero" style="margin-top:2rem;">
          <div>
            <div class="t">🛠️ ระบบจัดการอุปกรณ์ช่าง & สระว่ายน้ำ</div>
            <div class="s">เข้าสู่ระบบเพื่อตรวจเช็ค ยืม-คืน และบริหารจัดการระบบ</div>
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
                    saved_password = matched_tech.iloc[0].get('password', '')
                    password_ok, needs_upgrade = verify_user_password(password, saved_password)
                    if password_ok:
                        role_val, user_val = ROLE_TECH, username
                        if needs_upgrade:
                            upgraded_hash = hash_user_password(password)
                            db.tech_users.update_one({"username": username}, {"$set": {"password": upgraded_hash}})
                            get_tech_users_df.clear()

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
                if cookie_manager is not None:
                    try:
                        cookie_manager.set(cookie=LS_KEY, val=token, expires_at=datetime.now() + timedelta(days=3650))
                    except Exception:
                        pass
                if local_store is not None:
                    try:
                        local_store.setItem(LS_KEY, token, key="ls_set_token")
                    except Exception:
                        pass
                st.success("เข้าสู่ระบบสำเร็จ!")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    st.stop()

# =====================================================================
#  SHARED DATA FETCH (INVENTORY + BORROWS + ALERTS)
# =====================================================================
low_stock_limit = int(get_settings_val('low_stock_threshold', '1'))
items_df = get_items_df()
item_name_map = dict(zip(items_df['id'], items_df['name'])) if not items_df.empty else {}

active_borrows = get_active_borrows()
borrowed_item_map = {}
borrower_details_map = {}
for t in active_borrows:
    it_id = t["item_id"]
    q_borrowed = t.get("quantity", 1)
    b_name = t.get("borrower_name", "ไม่ระบุ")
    borrowed_item_map[it_id] = borrowed_item_map.get(it_id, 0) + q_borrowed
    borrower_details_map.setdefault(it_id, []).append(f"{b_name} ({q_borrowed} ชิ้น)")

is_tech_view = st.session_state.role in TECH_ROLES
abn_statuses = ['ชำรุด', 'อุปกรณ์หมด'] if is_tech_view else ['ชำรุด', 'สูญหาย', 'อุปกรณ์หมด']
abn_label = "ชำรุด / กำลังใช้งาน / หมด"
abn_title = "อุปกรณ์ชำรุด/กำลังใช้งาน/หมด"

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

borrowed_cnt = len(active_borrows)
abn_cnt, low_cnt = len(abnormal_items), len(low_stock_items)
pending_reqs_all = get_pending_reqs()

# =====================================================================
#  SHARED BORROW / RETURN COMPONENT
# =====================================================================
def render_borrow_return_system():
    st.subheader("🔄 ระบบยืม-คืน เครื่องมือและอุปกรณ์")
    sub_borrow, sub_return, sub_history = st.tabs(["📝 ทำรายการยืม", "🔙 ทำรายการคืน", "📜 ประวัติยืม-คืน"])

    with sub_borrow:
        available_items = items_df[items_df['quantity'] > 0] if not items_df.empty else pd.DataFrame()
        if not available_items.empty:
            with st.form("borrow_form_shared", clear_on_submit=True):
                item_dict = {f"{row['name']} (คงเหลือ: {row['quantity']} ชิ้น)": row['id']
                             for _, row in available_items.iterrows()}
                sel_item_label = st.selectbox("เลือกเครื่องมือ/อุปกรณ์ที่ต้องการยืม *", list(item_dict.keys()))
                borrow_qty = st.number_input("จำนวนที่ต้องการยืม *", min_value=1,
                                             max_value=int(available_items['quantity'].max()), value=1)
                borrower_name = st.text_input("ชื่อผู้ยืม * (ระบุชื่อ-นามสกุล / แผนก)")
                borrow_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายผู้ยืมหรือหลักฐานการยืม (ถ้ามี)", type=["jpg", "jpeg", "png"])
                st.info(f"📌 ผู้ทำรายการ/ผู้ให้ยืม: **{get_display_name(st.session_state.username)}** (บันทึกอัตโนมัติ)")

                if st.form_submit_button("ยืนยันการยืมอุปกรณ์", type="primary"):
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
        active_txs = get_active_borrows()
        if active_txs:
            for t in active_txs:
                item_name = item_name_map.get(t["item_id"], "Unknown")
                giver_str = f" | ผู้ให้ยืม: {get_display_name(t.get('giver_name'))}" if t.get('giver_name') else ""
                with st.expander(f"📦 อุปกรณ์: {item_name} (จำนวนยืม: {t.get('quantity', 1)} ชิ้น) | ผู้ยืม: {t.get('borrower_name')}{giver_str}"):
                    col_r1, col_r2 = st.columns([1, 2])
                    with col_r1:
                        p_img = get_tx_image(t['id'])
                        if p_img:
                            st.image(p_img, caption=f"ผู้ยืม: {t.get('borrower_name')}", width=200)
                        else:
                            st.write("*(ไม่มีรูปถ่าย)*")
                    with col_r2:
                        st.write(f"**ชื่ออุปกรณ์:** {item_name}")
                        st.write(f"**จำนวนที่ยืม:** {t.get('quantity', 1)} ชิ้น")
                        st.write(f"**ผู้ยืม:** {t.get('borrower_name')}")
                        if t.get('giver_name'):
                            st.write(f"**ผู้ให้ยืม/บันทึก:** {get_display_name(t.get('giver_name'))}")
                        st.write(f"**วันที่ยืม:** {t.get('borrow_date')}")

                        with st.form(key=f"return_form_{t['id']}"):
                            st.info(f"📌 ผู้รับคืน: **{get_display_name(st.session_state.username)}** (บันทึกอัตโนมัติ)")
                            ret_img_file = st.file_uploader("ถ่ายภาพ/แนบรูปถ่ายตอนคืนอุปกรณ์ (ถ้ามี)", type=["jpg", "jpeg", "png"], key=f"ret_img_{t['id']}")
                            if st.form_submit_button("✅ รับคืนอุปกรณ์รายการนี้", type="primary"):
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
            "ผู้ให้ยืม": get_display_name(t.get("giver_name")),
            "ผู้รับคืน": get_display_name(t.get("receiver_name")),
            "วันที่ยืม": t.get("borrow_date"),
            "วันที่คืน": t.get("return_date"),
            "สถานะ": t.get("status"),
        } for t in all_txs])
        st.dataframe(tx_history, use_container_width=True, hide_index=True)

# =====================================================================
#  INSPECTION LISTS
# =====================================================================
def render_tool_inspection_list(tools_all_df):
    tech_search = st.text_input("🔍 ค้นหาอุปกรณ์ช่าง...", key="tech_search_box")
    tools_df = tools_all_df
    if tech_search.strip():
        tools_df = tools_df[tools_df['name'].str.contains(tech_search.strip(), case=False, na=False)]

    st.caption("💡 คลิกที่ชื่ออุปกรณ์เพื่อตรวจสอบสถานะ · อุปกรณ์ช่างทั่วไปสามารถปรับแก้จำนวนคงเหลือจริงได้ทันที")

    with keyed_container("tech_check_list", height=520):
        for _, row in tools_df.iterrows():
            rid = int(row['id'])
            current_status = str(row['status'])
            subcat = str(row.get('subcategory', ''))
            borrow_qty = borrowed_item_map.get(rid, 0)
            borrower_info = ", ".join(borrower_details_map.get(rid, []))

            if borrow_qty > 0:
                badge_color, status_text = "🔵", f"[ถูกยืมโดย {borrower_info}]"
            elif current_status == "ปกติ":
                badge_color, status_text = "🟢", "[ปกติ]"
            elif current_status.startswith("กำลังใช้งาน"):
                badge_color, status_text = "🟡", f"[{current_status}]"
            elif current_status == "อุปกรณ์หมด":
                badge_color, status_text = "🟠", "[อุปกรณ์หมด]"
            else:
                badge_color, status_text = "🔴", f"[{current_status}]"

            with st.expander(f"{badge_color} {row['name']} (คงเหลือ: {row['quantity']})  {status_text}"):
                if subcat == "อุปกรณ์ช่างทั่วไป":
                    st.number_input(
                        "ปรับจำนวนคงเหลือจริง *",
                        min_value=0,
                        value=int(row['quantity']),
                        step=1,
                        key=f"gen_q_{rid}"
                    )
                else:
                    base_st = current_status.split(" (")[0] if "(" in current_status else current_status
                    if borrow_qty > 0:
                        base_st = "ยืม"
                    status_options = ["ปกติ", "ชำรุด", "สูญหาย", "อุปกรณ์หมด", "กำลังใช้งาน"]
                    def_idx = status_options.index(base_st) if base_st in status_options else 0
                    selected_status = st.selectbox(
                        "สถานะการตรวจสอบ *",
                        status_options,
                        index=def_idx,
                        key=f"status_sel_{rid}"
                    )
                    if selected_status != "ปกติ":
                        if selected_status == "กำลังใช้งาน":
                            detail_def = current_status.split("(")[1].replace(")", "") if "กำลังใช้งาน (" in current_status else ""
                            st.text_input("ระบุรายละเอียดการใช้งาน *", value=detail_def, key=f"issue_detail_{rid}")
                            if int(row['orig_quantity']) > 1:
                                st.number_input("จำนวนชิ้นที่นำไปใช้งาน *", min_value=1, max_value=int(row['orig_quantity']), value=1, key=f"issue_qty_{rid}")
                        elif selected_status in ["ชำรุด", "สูญหาย"]:
                            if int(row['orig_quantity']) > 1:
                                st.number_input(f"จำนวนชิ้นที่{selected_status} *", min_value=1, max_value=int(row['orig_quantity']), value=1, key=f"issue_qty_{rid}")

                img_bytes = get_item_image(rid)
                if img_bytes:
                    with st.popover("📷 ดูรูปภาพอุปกรณ์"):
                        st.image(img_bytes, caption=row['name'], use_container_width=True)
                else:
                    st.caption("*(ไม่มีรูปภาพประกอบ)*")

def render_pool_list(pool_all_df):
    tech_pool_search = st.text_input("🔍 ค้นหาอุปกรณ์สระว่ายน้ำ...", key="tech_pool_search_box")
    pool_df = pool_all_df
    if tech_pool_search.strip():
        pool_df = pool_df[pool_df['name'].str.contains(tech_pool_search.strip(), case=False, na=False)]

    st.caption("💡 ตรวจสอบจำนวนคงเหลือปัจจุบันของเคมีภัณฑ์และอุปกรณ์สระว่ายน้ำ สามารถกดปรับแก้ตัวเลขและดูรูปภาพได้รวดเร็ว")

    with keyed_container("pool_check_list", height=520):
        for _, row in pool_df.iterrows():
            rid = int(row['id'])
            with st.expander(f"🏊 {row['name']} (ปัจจุบัน: {row['quantity']} ชิ้น)"):
                st.number_input(
                    "ปรับจำนวนคงเหลือจริง *",
                    min_value=0,
                    value=int(row['quantity']),
                    step=1,
                    key=f"pool_q_{rid}"
                )
                img_bytes = get_item_image(rid)
                if img_bytes:
                    with st.popover("📷 ดูรูปภาพอุปกรณ์"):
                        st.image(img_bytes, caption=row['name'], use_container_width=True)
                else:
                    st.caption("*(ไม่มีรูปภาพประกอบ)*")

def clear_inspection_widget_state():
    prefixes = ("issue_type_", "issue_detail_", "issue_qty_", "pool_q_", "status_sel_", "gen_q_")
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(prefixes):
            del st.session_state[k]

# =====================================================================
#  ROLE 1: ADMIN VIEW (FULL ACCESS TO ALL 7 MODULES)
# =====================================================================
if st.session_state.role == ROLE_ADMIN:
    ADMIN_NAV_ITEMS = [
        "📊 1. ภาพรวมระบบ (Overview)",
        "🛠️ 2. คลังอุปกรณ์ช่าง & สระว่ายน้ำ",
        "🗄️ 3. ควบคุมลิ้นชัก",
        "💧 4. Water Alarm System",
        "🚨 5. Fire Alarm System",
        "☀️ 6. ระบบโซล่าเซลล์",
        "⚙️ 7. ตั้งค่าระบบ & บัญชีผู้ใช้งาน"
    ]

    with st.sidebar:
        st.markdown("""
        <div class="brand-box">
          <div class="brand-logo">K</div>
          <div>
            <div class="brand-title">KAVE TOWN SHIFT</div>
            <div class="brand-sub">Admin Dashboard V2</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            f'<div class="user-card"><div class="avatar">{esc(st.session_state.username[:1].upper() if st.session_state.username else "A")}</div>'
            f'<div><div class="u-name">{esc(get_display_name(st.session_state.username))}</div>'
            f'<div class="u-role">{esc(st.session_state.role)}</div></div></div>',
            unsafe_allow_html=True
        )

        st.caption("OVERVIEW & MODULES")
        selected_admin_module = st.radio(
            "เมนูควบคุมหลัก",
            ADMIN_NAV_ITEMS,
            label_visibility="collapsed",
            key="admin_sidebar_nav"
        )

        st.markdown("---")
        st.caption("SYSTEM TELEMETRY")
        mqtt_badge = "🟢 Online" if iot_mgr.connected else "🔴 Offline"
        servo_badge = "🔓 OPEN" if iot_mgr.servo_status == "UP" else "🔒 LOCK"
        fire_badge = "🚨 ALERT" if iot_mgr.fire_status == "ALERT" else "🟢 NORMAL"
        water_any_alarm = any(v == "ALARM" for v in iot_mgr.water_status.values())
        water_badge = "🚨 ALARM" if water_any_alarm else "🟢 NORMAL"

        st.markdown(f"""
        <div style="font-size:0.77rem; line-height:1.85; background:rgba(15,23,42,0.55); padding:0.65rem 0.8rem; border-radius:12px; border:1px solid var(--glass-border);">
          <div><b>MQTT Broker:</b> {mqtt_badge}</div>
          <div><b>Servo Drawer:</b> {servo_badge}</div>
          <div><b>Water Pumps:</b> {water_badge}</div>
          <div><b>Fire Alarm:</b> {fire_badge}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 รีเฟรชการเชื่อมต่อ MQTT", use_container_width=True):
            iot_mgr.connect()
            st.toast("รีเฟรชการเชื่อมต่อ MQTT แล้ว", icon="📡")
            st.rerun()

        st.markdown("---")
        with st.expander("👤 สลับมุมมอง / ออกจากระบบ", expanded=False):
            if st.session_state.original_role == ROLE_ADMIN:
                if st.button("🔀 สลับเป็น 'ช่างประจำอาคารพิเศษ'", use_container_width=True):
                    switch_role(ROLE_TECH_SP)
            if st.button("🚪 ออกจากระบบ (Logout)", type="primary", use_container_width=True, key="sidebar_logout_btn"):
                if st.session_state.get("token"):
                    db.sessions.delete_one({"token": st.session_state.token})
                if cookie_manager is not None:
                    try:
                        cookie_manager.delete(cookie=LS_KEY)
                    except Exception:
                        pass
                if local_store is not None:
                    try:
                        local_store.deleteItem(LS_KEY, key="ls_del_token")
                    except Exception:
                        pass
                st.session_state.logged_in = False
                st.session_state.role = None
                st.session_state.username = ""
                st.session_state.original_role = None
                st.session_state.token = None
                st.query_params.clear()
                st.rerun()

    # Admin Top Hero Banner
    cfg_iot = get_iot_config()
    mqtt_cls = "ok" if iot_mgr.connected else "bad"
    mqtt_txt = "MQTT: ONLINE" if iot_mgr.connected else "MQTT: OFFLINE"
    fire_cls = "bad" if iot_mgr.fire_status == "ALERT" else "ok"
    fire_txt = f"FIRE: {iot_mgr.fire_status}"
    water_alarm_cnt = sum(1 for v in iot_mgr.water_status.values() if v == "ALARM")
    water_cls = "bad" if water_alarm_cnt > 0 else "ok"
    water_txt = f"WATER ALARM: {water_alarm_cnt}" if water_alarm_cnt else "WATER: NORMAL"
    servo_cls = "info" if iot_mgr.servo_status == "UP" else "ok"
    servo_txt = "DRAWER: OPEN" if iot_mgr.servo_status == "UP" else "DRAWER: LOCK"

    st.markdown(f"""
    <div class="app-hero">
      <div>
        <div class="t">🛠️ KAVE TOWN SHIFT · ADMIN COMMAND DASHBOARD</div>
        <div class="s">วันที่ {get_now_str("%d/%m/%Y %H:%M")} · ผู้ดูแลระบบ: <b>{esc(get_display_name(st.session_state.username))}</b></div>
      </div>
      <div class="badge-row">
        <span class="status-pill-top {mqtt_cls}">📡 {mqtt_txt}</span>
        <span class="status-pill-top {servo_cls}">🗄️ {servo_txt}</span>
        <span class="status-pill-top {water_cls}">💧 {water_txt}</span>
        <span class="status-pill-top {fire_cls}">🔥 {fire_txt}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if pending_reqs_all:
        st.markdown(
            f'<div class="req-banner"><div style="font-size:1.5rem;">📥</div><div>'
            f'<div style="font-weight:700; color:#E0F2FE;">มีคำขอเบิกของรออนุมัติ {len(pending_reqs_all)} รายการ</div>'
            f'<div style="font-size:0.78rem; color:#BAE6FD;">ไปที่เมนู "2. คลังอุปกรณ์ช่าง & สระว่ายน้ำ -> อนุมัติคำขอเพิ่มอุปกรณ์" เพื่อพิจารณา</div></div></div>',
            unsafe_allow_html=True
        )

    # -----------------------------------------------------------------
    # MODULE 1: EXECUTIVE OVERVIEW (Admin Dashboard V2 Glass Grid)
    # -----------------------------------------------------------------
    if selected_admin_module.startswith("📊 1."):
        st.subheader("📊 ภาพรวมศูนย์ควบคุม (Executive Overview)")

        sol = st.session_state.get("last_solar_data", {})
        soc_disp = f"{int(sol['soc'])}%" if sol.get("ok") else "--%"
        pv_disp = f"{int(sol['pvP'])} W" if sol.get("ok") else "-- W"

        st.markdown(f"""
        <div class="kpi-grid">
          <div class="glass-kpi">
            <div class="top"><span class="lbl">รายการอุปกรณ์ทั้งหมด</span><span class="ic-badge">🛠️</span></div>
            <div class="val"><span class="cnt" style="--n:{len(items_df)}"></span></div>
            <div class="sub">สภาพปกติพร้อมใช้งาน {len(items_df) - abn_cnt} รายการ</div>
          </div>
          <div class="glass-kpi">
            <div class="top"><span class="lbl">ชำรุด / กำลังใช้งาน / หมด</span><span class="ic-badge">⚠️</span></div>
            <div class="val" style="color:{'#F87171' if abn_cnt else '#34D399'} !important;"><span class="cnt" style="--n:{abn_cnt}"></span></div>
            <div class="sub">สต็อกเหลือน้อยกว่าเกณฑ์: {low_cnt} รายการ</div>
          </div>
          <div class="glass-kpi">
            <div class="top"><span class="lbl">กำลังถูกยืม / รออนุมัติเบิก</span><span class="ic-badge">📦</span></div>
            <div class="val"><span class="cnt" style="--n:{borrowed_cnt}"></span> / <span class="cnt" style="--n:{len(pending_reqs_all)}"></span></div>
            <div class="sub">ยืมอยู่ {borrowed_cnt} รายการ · รออนุมัติ {len(pending_reqs_all)} รายการ</div>
          </div>
          <div class="glass-kpi">
            <div class="top"><span class="lbl">ระบบปั๊มน้ำ (Water Alarm)</span><span class="ic-badge">💧</span></div>
            <div class="val" style="color:{'#F87171' if water_alarm_cnt else '#34D399'} !important;">{'ALARM ('+str(water_alarm_cnt)+')' if water_alarm_cnt else 'NORMAL'}</div>
            <div class="sub">ออนไลน์ {sum(1 for v in iot_mgr.water_online.values() if v)}/5 จุดตรวจวัด</div>
          </div>
          <div class="glass-kpi">
            <div class="top"><span class="lbl">ระบบอัคคีภัย & โซลาร์เซลล์</span><span class="ic-badge">☀️</span></div>
            <div class="val">{iot_mgr.fire_status} · {soc_disp}</div>
            <div class="sub">PV Input: {pv_disp}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### ⚡ แผงควบคุมด่วน (Quick Hardware & System Controls)")
        qa1, qa2, qa3, qa4, qa5 = st.columns(5)
        if qa1.button("🔓 เปิดลิ้นชัก (OPEN)", type="primary", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_servo_cmd"], "UP")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            st.toast("ส่งคำสั่ง UP ไปที่ esp8266/servo แล้ว", icon="🔓")
            st.rerun()
        if qa2.button("🔒 ล็อกลิ้นชัก (LOCK)", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_servo_cmd"], "DOWN")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            st.toast("ส่งคำสั่ง DOWN ไปที่ esp8266/servo แล้ว", icon="🔒")
            st.rerun()
        if qa3.button("📡 เช็กสถานะปั๊มน้ำ (CheckClients)", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_check_clients"], "CheckClients")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            iot_mgr.publish(cfg_iot["topic_water"], "CheckClients")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            st.toast("ส่งคำสั่ง CheckClients แล้ว", icon="💧")
            st.rerun()
        if qa4.button("⚡ สั่ง Reset Relay ไฟไหม้", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_fire_relay"], "reset")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            iot_mgr.handle_message(cfg_iot["topic_fire"], "RESET CLEAR")
            st.toast("ส่งคำสั่ง reset ไปที่ nodemcu/control/relay แล้ว", icon="🚨")
            st.rerun()
        if qa5.button("☀️ ดึงค่า Growatt Solar ล่าสุด", use_container_width=True):
            with st.spinner("กำลังดึงข้อมูลจาก Growatt Server..."):
                st.session_state.last_solar_data = fetch_growatt_realtime(sync_sheets=False)
            st.rerun()

        st.markdown("---")
        col_ov1, col_ov2 = st.columns([1.2, 1])
        with col_ov1:
            st.markdown("#### 💧 สถานะปั๊มน้ำและจุดตรวจจับน้ำท่วม (5 จุด)")
            p_cols = st.columns(5)
            p_labels = [("A", "อาคาร A"), ("B", "อาคาร B"), ("C", "อาคาร C"), ("D", "อาคาร D"), ("UNDERGROUND", "สระว่ายน้ำใต้ดิน")]
            for idx, (pk, pname) in enumerate(p_labels):
                st_val = iot_mgr.water_status.get(pk, "NORMAL")
                on_val = iot_mgr.water_online.get(pk, True)
                pill_c = "pill-off" if not on_val else ("pill-alarm" if st_val == "ALARM" else "pill-normal")
                pill_t = "OFFLINE" if not on_val else st_val
                p_cols[idx].markdown(
                    f'<div class="iot-card"><div class="hd">{pname}</div>'
                    f'<div class="bd"><span class="pill {pill_c}">{pill_t}</span></div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("#### 🔥 สถานะโซนแจ้งเตือนอัคคีภัย (Fire Alarm Zones)")
            f_cols = st.columns(4)
            f_labels = [("A", "อาคาร A"), ("B", "อาคาร B"), ("C", "อาคาร C"), ("D", "อาคาร D")]
            for idx, (fk, fname) in enumerate(f_labels):
                fst = iot_mgr.fire_zones.get(fk, "NORMAL")
                fc = "pill-alarm" if fst == "ALERT" else "pill-normal"
                f_cols[idx].markdown(
                    f'<div class="iot-card">'
                    f'<div class="bd"><span class="nm">{fname}</span>'
                    f'<span class="pill {fc}">{fst}</span></div></div>',
                    unsafe_allow_html=True
                )

        with col_ov2:
            st.markdown("#### 📋 สรุปรายการอุปกรณ์ที่ต้องดูแล")
            if abn_cnt:
                with st.expander(f"❌ {abn_title} ({abn_cnt} รายการ)", expanded=True):
                    st.dataframe(abnormal_items[['name', 'category', 'status', 'quantity']], hide_index=True, use_container_width=True)
            else:
                st.success("✅ อุปกรณ์ทุกชิ้นอยู่ในสภาพปกติ")

            if low_cnt:
                with st.expander(f"⚠️ อุปกรณ์ทั่วไปเหลือน้อยกว่าเกณฑ์ ({low_cnt} รายการ)", expanded=False):
                    st.dataframe(low_stock_items[['name', 'category', 'quantity']], hide_index=True, use_container_width=True)
            else:
                st.success("✅ อุปกรณ์ทั่วไปมีจำนวนเพียงพอทุกรายการ")

            # แจ้งเตือนรายการที่ถูกปรับลดจำนวนใน 7 วันล่าสุด (ไม่มีการปรับลดเลย = ไม่แสดง)
            admin_reduced_rows = get_recent_reductions(get_inspections_list(), days=7)
            if admin_reduced_rows:
                with st.expander(f"📉 มีการปรับลดจำนวนอุปกรณ์ใน 7 วันล่าสุด ({len(admin_reduced_rows)} รายการ)", expanded=False):
                    st.dataframe(pd.DataFrame(admin_reduced_rows), hide_index=True, use_container_width=True)

            if borrowed_cnt:
                with st.expander(f"📤 อุปกรณ์ที่กำลังถูกยืม ({borrowed_cnt} รายการ)", expanded=False):
                    st.dataframe(pd.DataFrame([{
                        "อุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
                        "จำนวน": t.get("quantity", 1),
                        "ผู้ยืม": t.get("borrower_name"),
                        "วันที่ยืม": t.get("borrow_date"),
                    } for t in active_borrows]), hide_index=True, use_container_width=True)

    # -----------------------------------------------------------------
    # MODULE 2: INVENTORY, INSPECTIONS, REQUISITIONS & BORROW/RETURN
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("🛠️ 2."):
        admin_inv_tabs = st.tabs([
            "📋 2.1 จัดการอุปกรณ์ทั้งหมด",
            "🧑‍🔧 2.2 ตรวจเช็ค/ปรับสต็อกโดยตรง",
            "📊 2.3 รายงานการตรวจเช็ค",
            "📥 2.4 อนุมัติคำขอเพิ่มอุปกรณ์",
            "🔄 2.5 ยืม-คืน เครื่องมือ-อุปกรณ์"
        ])

        with admin_inv_tabs[0]:
            tab_list, tab_add_edit, tab_excel_import = st.tabs(["🔍 ดูและแก้ไขด่วนในตาราง", "➕ เพิ่ม/แก้ไขอุปกรณ์", "📥 นำเข้า/รีเซ็ตข้อมูลตั้งต้น"])

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

                st.caption(f"แสดงรายการอุปกรณ์ทั้งหมด {len(filtered_df)} จาก {len(items_df)} รายการ (💡 คลิกเลือกแถวในตารางเพื่อเปิดหน้าต่างแก้ไขทันที)")

                cols_show = ['id', 'name', 'category', 'subcategory', 'quantity', 'status', 'alert_zero', 'note']
                show_df = filtered_df[cols_show].copy() if not filtered_df.empty else pd.DataFrame(columns=cols_show)
                if not show_df.empty:
                    show_df['alert_zero'] = show_df['alert_zero'].astype(bool)

                table_event = st.dataframe(
                    show_df, use_container_width=True, hide_index=True, height=360,
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
                        with st.expander(f"📌 แก้ไขข้อมูลอุปกรณ์: #{qe_row['id']} - {qe_row['name']}", expanded=True):
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
                                           "quantity": qe_quantity, "orig_quantity": qe_quantity, "status": qe_status,
                                           "alert_zero": 1 if qe_alert_zero else 0, "note": qe_note}
                                    if qe_file is not None:
                                        upd["image"] = compress_image_to_base64(qe_file)
                                    db.items.update_one({"id": qe_id}, {"$set": upd})
                                    log_audit("ITEM_UPDATE", qe_id, {"name": qe_row.get("name"), "quantity": qe_row.get("quantity"), "status": qe_row.get("status")}, {"name": qe_name, "quantity": qe_quantity, "status": qe_status})
                                    refresh_items(images=qe_file is not None)
                                    close_quick_edit()
                                    done("อัปเดตข้อมูลสำเร็จ!")
                                if col_qe2.form_submit_button("🗑️ ลบอุปกรณ์นี้", type="secondary"):
                                    db.items.delete_one({"id": qe_id})
                                    log_audit("ITEM_DELETE", qe_id, {"name": qe_row.get("name"), "quantity": qe_row.get("quantity"), "status": qe_row.get("status")})
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
                        alert_zero = st.checkbox("🔔 แจ้งเตือนเมื่อจำนวนเหลือ 0")
                        note = st.text_area("หมายเหตุ")
                        uploaded_file = st.file_uploader("อัปโหลดรูปภาพอุปกรณ์", type=["jpg", "jpeg", "png"])

                        if st.form_submit_button("บันทึกอุปกรณ์ใหม่", type="primary"):
                            if name.strip():
                                new_id = get_next_sequence("items_id")
                                db.items.insert_one({
                                    "id": new_id, "name": name, "category": category, "subcategory": subcategory,
                                    "quantity": quantity, "orig_quantity": quantity, "status": status,
                                    "alert_zero": 1 if alert_zero else 0, "note": note,
                                    "image": compress_image_to_base64(uploaded_file)
                                })
                                log_audit("ITEM_CREATE", new_id, after={"name": name, "category": category, "quantity": int(quantity), "status": status})
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
                                           "quantity": e_quantity, "orig_quantity": e_quantity, "status": e_status,
                                           "alert_zero": 1 if e_alert_zero else 0, "note": e_note}
                                    if e_file is not None:
                                        upd["image"] = compress_image_to_base64(e_file)
                                    db.items.update_one({"id": item_id_int}, {"$set": upd})
                                    log_audit("ITEM_UPDATE", item_id_int, {"name": current_item["name"], "quantity": int(current_item["quantity"]), "status": current_item["status"]}, {"name": e_name, "quantity": int(e_quantity), "status": e_status})
                                    refresh_items(images=e_file is not None)
                                    done("อัปเดตข้อมูลสำเร็จ!")
                                if col_e2.form_submit_button("ลบอุปกรณ์นี้", type="secondary"):
                                    db.items.delete_one({"id": item_id_int})
                                    log_audit("ITEM_DELETE", item_id_int, {"name": current_item["name"], "quantity": int(current_item["quantity"]), "status": current_item["status"]})
                                    refresh_items(images=True)
                                    done("ลบเรียบร้อยแล้ว!")

                with sub_bulk:
                    st.markdown("### 📁 อัปโหลดรูปภาพอุปกรณ์แบบกลุ่ม (ตามชื่อไฟล์รหัสอุปกรณ์ เช่น `1.jpg`, `2.png`)")
                    bulk_files = st.file_uploader("เลือกไฟล์รูปภาพทั้งหมด", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="bulk_img_files")
                    if bulk_files:
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
                st.warning("การคลิกปุ่มนี้จะล้างข้อมูลอุปกรณ์เดิมและโหลดรายการตั้งต้น 79 รายการใหม่ทั้งหมด")
                if st.button("🚀 รีเซ็ตและโหลดอุปกรณ์ทั้งหมดตามรายการตั้งต้น", type="primary"):
                    db.items.delete_many({})
                    db.items.insert_many(build_default_docs())
                    db.counters.update_one({"_id": "items_id"}, {"$set": {"seq": len(DEFAULT_INITIAL_ITEMS)}}, upsert=True)
                    refresh_items(images=True)
                    done("นำเข้าอุปกรณ์และลำดับใหม่สำเร็จ!")

        with admin_inv_tabs[1]:
            st.markdown("#### 🧑‍🔧 ตรวจเช็คสภาพและปรับแก้จำนวนอุปกรณ์โดยแอดมิน")
            adm_cat = st.radio("เลือกหมวดหมู่", ["🔧 หมวดอุปกรณ์ช่าง", "🏊 หมวดอุปกรณ์สระว่ายน้ำ"], horizontal=True, key="adm_insp_cat")
            if adm_cat == "🔧 หมวดอุปกรณ์ช่าง":
                tools_all_df = items_df[items_df['category'] == 'อุปกรณ์ช่าง'] if not items_df.empty else pd.DataFrame()
                if not tools_all_df.empty:
                    render_tool_inspection_list(tools_all_df)
                    if st.button("💾 บันทึกการตรวจเช็ค/ปรับจำนวนอุปกรณ์ช่าง", type="primary", use_container_width=True):
                        bulk_ops, summaries, adm_changes = [], [], []
                        for _, row in tools_all_df.iterrows():
                            rid = int(row['id'])
                            subcat = str(row.get('subcategory', ''))
                            orig_q = int(row['orig_quantity'])
                            item_name = row['name']
                            if subcat == "อุปกรณ์ช่างทั่วไป":
                                new_q = int(st.session_state.get(f"gen_q_{rid}", row['quantity']))
                                bulk_ops.append(pymongo.operations.UpdateOne(
                                    {"id": rid}, {"$set": {"quantity": new_q, "orig_quantity": new_q, "status": "ปกติ"}}
                                ))
                                if new_q != int(row['quantity']):
                                    summaries.append(f"{item_name}: ปรับสต็อกเหลือ {new_q} ชิ้น")
                                if new_q < int(row['quantity']):
                                    adm_changes.append({"item_id": rid, "name": item_name, "old_qty": int(row['quantity']), "new_qty": new_q, "reason": "ปรับสต็อก"})
                            else:
                                sel_st = st.session_state.get(f"status_sel_{rid}", "ปกติ")
                                detail = st.session_state.get(f"issue_detail_{rid}", "") or ""
                                qty_issue = int(st.session_state.get(f"issue_qty_{rid}", 1) or 1)
                                if sel_st != "ปกติ":
                                    final_st = f"กำลังใช้งาน ({detail})" if (sel_st == "กำลังใช้งาน" and detail.strip()) else sel_st
                                    new_q = 0 if sel_st == "อุปกรณ์หมด" else max(0, orig_q - qty_issue)
                                    bulk_ops.append(pymongo.operations.UpdateOne(
                                        {"id": rid}, {"$set": {"status": final_st, "quantity": new_q}}
                                    ))
                                    summaries.append(f"{item_name}: {final_st}")
                                    if new_q < int(row['quantity']):
                                        adm_changes.append({"item_id": rid, "name": item_name, "old_qty": int(row['quantity']), "new_qty": new_q, "reason": sel_st})
                                else:
                                    bulk_ops.append(pymongo.operations.UpdateOne(
                                        {"id": rid}, {"$set": {"status": "ปกติ", "quantity": orig_q}}
                                    ))
                        if bulk_ops:
                            db.items.bulk_write(bulk_ops, ordered=False)
                        db.inspections.insert_one({
                            "id": get_next_sequence("inspections_id"),
                            "tech_name": f"{st.session_state.username} (Admin)",
                            "category": "อุปกรณ์ช่าง",
                            "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"),
                            "session_num": 1,
                            "details": "Admin Direct Update | " + (", ".join(summaries) if summaries else "ปกติทุกรายการ"),
                            "changes": adm_changes,
                            "photos": ""
                        })
                        refresh_items()
                        get_inspections_list.clear()
                        clear_inspection_widget_state()
                        done("บันทึกการปรับแก้สถานะและจำนวนอุปกรณ์ช่างเรียบร้อยแล้ว!")
            else:
                pool_all_df = items_df[items_df['category'] == 'อุปกรณ์สระว่ายน้ำ'] if not items_df.empty else pd.DataFrame()
                if not pool_all_df.empty:
                    render_pool_list(pool_all_df)
                    if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                        bulk_pool_ops, pool_summaries, adm_pool_changes = [], [], []
                        row_map = pool_all_df.set_index('id')
                        for item_id in pool_all_df['id']:
                            rid = int(item_id)
                            q_val = int(st.session_state.get(f"pool_q_{rid}", row_map.loc[rid, 'quantity']))
                            old_q = int(row_map.loc[rid, 'quantity'])
                            if q_val != old_q:
                                bulk_pool_ops.append(pymongo.operations.UpdateOne({"id": rid}, {"$set": {"quantity": q_val, "orig_quantity": q_val}}))
                                pool_summaries.append(f"{row_map.loc[rid, 'name']}: ปรับจาก {old_q} เหลือ {q_val}")
                                if q_val < old_q:
                                    adm_pool_changes.append({"item_id": rid, "name": row_map.loc[rid, 'name'], "old_qty": old_q, "new_qty": q_val, "reason": "ปรับจำนวน"})
                        if bulk_pool_ops:
                            db.items.bulk_write(bulk_pool_ops, ordered=False)
                        db.inspections.insert_one({
                            "id": get_next_sequence("inspections_id"),
                            "tech_name": f"{st.session_state.username} (Admin)",
                            "category": "อุปกรณ์สระว่ายน้ำ",
                            "inspection_date": get_now_str("%Y-%m-%d %H:%M:%S"),
                            "session_num": 1,
                            "details": "Admin Pool Update | " + (", ".join(pool_summaries) if pool_summaries else "ไม่มีการเปลี่ยนจำนวน"),
                            "changes": adm_pool_changes,
                            "photos": ""
                        })
                        refresh_items()
                        get_inspections_list.clear()
                        clear_inspection_widget_state()
                        done("อัปเดตจำนวนอุปกรณ์สระว่ายน้ำเรียบร้อยแล้ว!")

        with admin_inv_tabs[2]:
            st.subheader("📊 รายงานการตรวจเช็คสภาพอุปกรณ์")
            report_type = st.radio("เลือกมุมมองรายงาน", ["รายวัน (Daily)", "รายสัปดาห์ (Weekly)", "รายเดือน (Monthly)", "รายปี (Yearly)", "ประวัติทั้งหมด"], horizontal=True)
            inspections_df = pd.DataFrame(get_inspections_list())

            if not inspections_df.empty:
                inspections_df['inspection_date'] = pd.to_datetime(inspections_df['inspection_date'])
                now_dt = get_now_th()
                if report_type == "รายวัน (Daily)":
                    target_date = st.date_input("เลือกวันที่", value=now_dt.date())
                    filtered_insp = inspections_df[inspections_df['inspection_date'].dt.date == target_date]
                elif report_type == "รายสัปดาห์ (Weekly)":
                    # เลือกวันใดก็ได้ในสัปดาห์ แล้วคำนวณช่วง จันทร์-อาทิตย์ ให้อัตโนมัติ
                    week_pick = st.date_input("เลือกวันใดก็ได้ในสัปดาห์ที่ต้องการ", value=now_dt.date(), key="rep_week_pick")
                    week_start = week_pick - timedelta(days=week_pick.weekday())
                    week_end = week_start + timedelta(days=6)
                    st.caption(f"📅 ช่วงสัปดาห์: {week_start.strftime('%d/%m/%Y')} (จันทร์) – {week_end.strftime('%d/%m/%Y')} (อาทิตย์)")
                    _insp_day = inspections_df['inspection_date'].dt.date
                    filtered_insp = inspections_df[(_insp_day >= week_start) & (_insp_day <= week_end)]
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

                display_insp = filtered_insp.copy()
                display_insp['tech_display_name'] = display_insp['tech_name'].map(lambda n: get_display_name(str(n)[:-8]) + ' (Admin)' if str(n).endswith(' (Admin)') else get_display_name(n))
                st.dataframe(
                    display_insp[['id', 'tech_display_name', 'category', 'inspection_date', 'session_num', 'details']],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("รหัส", width="small"),
                        "tech_display_name": "ผู้ตรวจ", "category": "หมวดหมู่",
                        "inspection_date": st.column_config.DatetimeColumn("วันที่ตรวจ", format="DD/MM/YYYY HH:mm"),
                        "session_num": st.column_config.NumberColumn("รอบ", width="small"),
                        "details": st.column_config.TextColumn("รายละเอียด", width="large"),
                    }
                )

                st.markdown("---")
                st.markdown("#### 📸 ดูรายละเอียดและรูปถ่ายหน้างานของการตรวจเช็ค")
                for _, row in display_insp.head(30).iterrows():
                    date_str_show = row['inspection_date'].strftime("%Y-%m-%d %H:%M:%S")
                    with st.expander(f"📌 {date_str_show} | ผู้ตรวจ: {row['tech_display_name']} | หมวด: {row['category']} (รอบที่ {row['session_num']})"):
                        st.write(f"📝 **รายละเอียดการตรวจ:** {row['details']}")
                        if st.checkbox("🖼️ โหลดรูปถ่าย", key=f"load_photos_{row['id']}"):
                            photo_imgs = get_inspection_photos(int(row['id']))
                            if photo_imgs:
                                cols_p = st.columns(min(len(photo_imgs), 4))
                                for idx, p_img in enumerate(photo_imgs):
                                    cols_p[idx % 4].image(p_img, caption=f"รูปที่ {idx + 1}", use_container_width=True)
                            else:
                                st.info("*(ไม่ได้อัปโหลดรูปถ่ายรวม)*")
            else:
                st.info("ยังไม่มีประวัติการตรวจเช็คในระบบ")

        with admin_inv_tabs[3]:
            st.subheader("📥 จัดการคำขอเพิ่มอุปกรณ์เข้าคลัง")
            sub_req_pending, sub_req_history = st.tabs(["📥 คำขอที่รออนุมัติ", "📜 ประวัติการอนุมัติคำขอ"])
            with sub_req_pending:
                current_qty_map = dict(zip(items_df['id'], items_df['quantity'])) if not items_df.empty else {}
                if pending_reqs_all:
                    for req in pending_reqs_all:
                        item_name = item_name_map.get(req["item_id"], "Unknown")
                        current_stock = current_qty_map.get(req["item_id"], 0)
                        with st.container():
                            st.write(f"🆔 **รหัสคำขอ:** #{req['id']} | 👤 **ผู้ขอเพิ่ม:** {get_display_name(req['tech_name'])} | 📅 **วันที่ขอ:** {req['request_date']}")
                            st.write(f"📦 **อุปกรณ์:** {item_name} | **จำนวนที่ขอเพิ่ม:** +{req['quantity']} ชิ้น (คงเหลือปัจจุบัน: {current_stock})")
                            st.write(f"📝 **หมายเหตุ/เหตุผล:** {req['note']}")
                            col_app1, col_app2 = st.columns(2)
                            if col_app1.button("✅ อนุมัติ (เพิ่มจำนวนเข้าคลัง)", key=f"approve_{req['id']}", type="primary"):
                                res = db.requisition_requests.update_one(
                                    {"id": req['id'], "status": "รออนุมัติ"},
                                    {"$set": {"status": "อนุมัติ", "approval_date": get_now_str()}})
                                if res.modified_count:
                                    log_audit("REQUISITION_APPROVE", req["id"], before={"status": "รออนุมัติ", "quantity": current_stock}, after={"status": "อนุมัติ", "quantity": current_stock + int(req["quantity"])})
                                    db.items.update_one({"id": req['item_id']}, {"$inc": {"quantity": int(req['quantity']), "orig_quantity": int(req['quantity'])}, "$set": {"status": "ปกติ"}})
                                refresh_items()
                                clear_req_cache()
                                done(f"อนุมัติคำขอ #{req['id']} เรียบร้อยแล้ว")
                            if col_app2.button("❌ ไม่อนุมัติ", key=f"reject_{req['id']}"):
                                db.requisition_requests.update_one({"id": req['id'], "status": "รออนุมัติ"}, {"$set": {"status": "ไม่อนุมัติ", "approval_date": get_now_str()}})
                                log_audit("REQUISITION_REJECT", req["id"], before={"status": "รออนุมัติ"}, after={"status": "ไม่อนุมัติ"})
                                clear_req_cache()
                                done(f"ปฏิเสธคำขอ #{req['id']} เรียบร้อยแล้ว", icon="⚠️")
                            st.markdown("---")
                else:
                    st.info("ไม่มีคำขอเพิ่มอุปกรณ์ที่รอการอนุมัติในขณะนี้")

            with sub_req_history:
                req_history_list = get_req_history()
                if req_history_list:
                    st.dataframe(pd.DataFrame([{
                        "รหัส": r["id"], "ผู้ขอ": get_display_name(r.get("tech_name")),
                        "ชื่ออุปกรณ์": item_name_map.get(r["item_id"], "Unknown"),
                        "จำนวนที่ขอ": r.get("quantity"), "หมายเหตุ": r.get("note"),
                        "วันที่ขอ": r.get("request_date"), "วันที่อนุมัติ": r.get("approval_date"),
                        "สถานะ": r.get("status")
                    } for r in req_history_list]), use_container_width=True, hide_index=True)
                else:
                    st.info("ยังไม่มีประวัติการอนุมัติคำขอ")

        with admin_inv_tabs[4]:
            render_borrow_return_system()

    # -----------------------------------------------------------------
    # MODULE 3: ESP8266 SMART DRAWER SERVO CONTROL
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("🗄️ 3."):
        st.subheader("🗄️ ระบบควบคุมลิ้นชักอัจฉริยะ (ESP8266 Servo Controller)")
        st.caption(f"เชื่อมโยงกับบอร์ด ESP8266 (Pin D4 / GPIO2) · Command Topic: `{cfg_iot['topic_servo_cmd']}` · Status Topic: `{cfg_iot['topic_servo_status']}`")

        # สถานะที่ใช้แสดงในตู้เซฟ: ถ้าเพิ่งสั่งงานและบอร์ดยังไม่ยืนยัน ให้เล่นอนิเมชั่นไปยังสถานะเป้าหมายก่อน
        servo_cmd = st.session_state.get("servo_cmd")
        if servo_cmd and (iot_mgr.servo_status == servo_cmd["target"] or time.time() - servo_cmd["ts"] > 45):
            st.session_state.pop("servo_cmd", None)
            servo_cmd = None
        eff_state = servo_cmd["target"] if servo_cmd else iot_mgr.servo_status
        prev_state = st.session_state.get("servo_view_prev", eff_state)

        s_col1, s_col2 = st.columns([1.5, 1])
        with s_col1:
            show_html_frame(_vault_html(eff_state, prev_state, bool(servo_cmd)), 580)

        with s_col2:
            is_up = iot_mgr.servo_status == "UP"
            st.markdown(f"""
            <div class="glass-kpi" style="padding:1.35rem;">
              <div class="top"><span class="lbl">CURRENT SERVO POSITION</span><span class="ic-badge">{'🔓' if is_up else '🔒'}</span></div>
              <div class="val" style="font-size:1.7rem; color:{'#38BDF8' if is_up else '#34D399'} !important;">
                {'OPEN (เปิด 0°)' if is_up else 'LOCK (ล็อก 180°)'}
              </div>
              <div class="sub">อัปเดตสถานะล่าสุด: {iot_mgr.servo_last_update}</div>
            </div>
            """, unsafe_allow_html=True)

            b_up, b_down = st.columns(2)
            if b_up.button("🔓 สั่งเปิดลิ้นชัก (OPEN)", type="primary", use_container_width=True):
                iot_mgr.publish(cfg_iot["topic_servo_cmd"], "UP")
                log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
                db.iot_logs.insert_one({
                    "datetime": get_now_str(), "system": "SERVO",
                    "location": "Admin Remote", "status": "UP",
                    "raw": f"Admin {st.session_state.username} sent UP"
                })
                st.session_state["servo_cmd"] = {"target": "UP", "ts": time.time()}
                done("ส่งคำสั่ง OPEN (หมุนเซอร์โวไปที่ 0°) เรียบร้อยแล้ว!")

            if b_down.button("🔒 สั่งล็อก/ปิดลิ้นชัก (LOCK)", use_container_width=True):
                iot_mgr.publish(cfg_iot["topic_servo_cmd"], "DOWN")
                log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
                db.iot_logs.insert_one({
                    "datetime": get_now_str(), "system": "SERVO",
                    "location": "Admin Remote", "status": "DOWN",
                    "raw": f"Admin {st.session_state.username} sent DOWN"
                })
                st.session_state["servo_cmd"] = {"target": "DOWN", "ts": time.time()}
                done("ส่งคำสั่ง LOCK (หมุนเซอร์โวไปที่ 180°) เรียบร้อยแล้ว!")

            st.caption("💡 กดสั่งงานแล้วตู้เซฟจะเล่นลำดับ เซอร์โวหมุน → ปลดสลัก → ประตูเปิด/ปิด ทันที และขึ้น 'รอบอร์ดยืนยัน' จนกว่า ESP8266 ตอบกลับ (รีเฟรชหน้าเพื่อดูสถานะจริง)")

        st.session_state["servo_view_prev"] = eff_state  # จำสถานะที่แสดงล่าสุด เพื่อเล่นอนิเมชั่นเฉพาะตอนสถานะเปลี่ยน

        st.markdown("#### 📜 ประวัติการสั่งงานและสถานะตอบกลับจาก ESP8266")
        servo_db_logs = list(db.iot_logs.find({"system": "SERVO"}, {"_id": 0}).sort("datetime", -1).limit(50))
        if servo_db_logs:
            st.dataframe(pd.DataFrame(servo_db_logs), use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีประวัติการสั่งเปิด-ปิดลิ้นชัก")

    # -----------------------------------------------------------------
    # MODULE 4: WATER LEVEL & PUMP ALARM
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("💧 4."):
        st.subheader("💧 ระบบตรวจจับระดับน้ำและปั๊มน้ำ (Water Level & Pump Alarm System)")
        st.caption(f"เชื่อมโยงกับ NodeMCU Server & จอ TFT · Topic: `{cfg_iot['topic_water']}` และ `Water alarm/status/#` พร้อมแจ้งเตือนเข้ากลุ่ม LINE OA")

        p_cols = st.columns(5)
        pump_meta = [
            ("A", "Transferpump A", "อาคาร A ห้องปั๊มน้ำ"),
            ("B", "Transferpump B", "อาคาร B ห้องปั๊มน้ำ"),
            ("C", "Transferpump C", "อาคาร C ห้องปั๊มน้ำ"),
            ("D", "Transferpump D", "อาคาร D ห้องปั๊มน้ำ"),
            ("UNDERGROUND", "Pool Ug Pump", "ห้องปั๊มสระว่ายน้ำใต้ดิน"),
        ]
        for idx, (pk, title, desc) in enumerate(pump_meta):
            st_val = iot_mgr.water_status.get(pk, "NORMAL")
            on_val = iot_mgr.water_online.get(pk, True)
            pill_c = "pill-off" if not on_val else ("pill-alarm" if st_val == "ALARM" else "pill-normal")
            pill_t = "OFFLINE" if not on_val else st_val
            p_cols[idx].markdown(
                f'<div class="iot-card"><div class="hd">{title}</div>'
                f'<div class="bd"><span class="nm">{desc}</span>'
                f'<span class="pill {pill_c}">{pill_t}</span></div></div>',
                unsafe_allow_html=True
            )

        w_act1, w_act2, w_act3 = st.columns([1.2, 1.2, 1.6])
        if w_act1.button("📡 ส่งคำสั่ง CheckClients (ตรวจสอบสถานะออนไลน์)", type="primary", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_check_clients"], "CheckClients")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            iot_mgr.publish(cfg_iot["topic_water"], "CheckClients")
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            done("ส่งคำสั่ง CheckClients ไปยัง MQTT แล้ว")

        with w_act2:
            sim_pump = st.selectbox("จำลอง/ส่งสถานะปั๊ม", [
                "TransferpumpA Normal", "TransferpumpA Alarm",
                "TransferpumpB Normal", "TransferpumpB Alarm",
                "TransferpumpC Normal", "TransferpumpC Alarm",
                "TransferpumpD Normal", "TransferpumpD Alarm",
                "Underground pump Normal", "Underground pump Alarm"
            ])
        if w_act3.button("🚀 ส่งสถานะเข้า MQTT & แจ้งเตือน LINE OA", use_container_width=True):
            iot_mgr.publish(cfg_iot["topic_water"], sim_pump)
            log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
            line_msg_map = {
                "TransferpumpA Alarm": "Flood Alert⚠️ : อาคารA ห้องปั้มน้ำผิดปกติ❌",
                "TransferpumpA Normal": "อาคารA ห้องปั้มน้ำสถานะ : ปกติ✅",
                "TransferpumpB Alarm": "Flood Alert⚠️ : อาคารB ห้องปั้มน้ำผิดปกติ❌",
                "TransferpumpB Normal": "อาคารB ห้องปั้มน้ำสถานะ : ปกติ✅",
                "TransferpumpC Alarm": "Flood Alert⚠️ : อาคารC ห้องปั้มน้ำผิดปกติ❌",
                "TransferpumpC Normal": "อาคารC ห้องปั้มน้ำสถานะ : ปกติ✅",
                "TransferpumpD Alarm": "Flood Alert⚠️ : อาคารD ห้องปั้มน้ำผิดปกติ❌",
                "TransferpumpD Normal": "อาคารD ห้องปั้มน้ำสถานะ : ปกติ✅",
                "Underground pump Alarm": "Flood Alert⚠️ : ห้องปั้มสระว่ายน้ำใต้ดินผิดปกติ❌",
                "Underground pump Normal": "ห้องปั้มสระว่ายน้ำใต้ดิน สถานะ : ปกติ✅",
            }
            ok_l, info_l = send_line_push(line_msg_map.get(sim_pump, sim_pump))
            done(f"ส่ง MQTT '{sim_pump}' แล้ว (LINE Push: {info_l})")

        st.markdown("---")
        st.markdown("#### 📊 สถิติและประวัติการแจ้งเตือนระดับน้ำ (Water Alarm Incident Analytics)")
        water_logs = list(db.iot_logs.find({"system": "WATER"}, {"_id": 0, "datetime": 1, "location": 1, "status": 1}).sort("datetime", -1).limit(5000))
        w_df = pd.DataFrame(water_logs)

        with st.expander("📂 นำเข้าไฟล์ `log.csv` จากการ์ด SD ของบอร์ด ESP32-TFT"):
            up_w_csv = st.file_uploader("เลือกไฟล์ log.csv (คอลัมน์ DateTime, Location, Status)", type=["csv"], key="up_water_csv")
            if up_w_csv is not None and st.button("📥 บันทึกข้อมูลจาก log.csv ลงฐานข้อมูล", key="btn_imp_w"):
                csv_df = pd.read_csv(up_w_csv)
                ins = []
                for _, r in csv_df.iterrows():
                    ins.append({
                        "datetime": str(r.get("DateTime", get_now_str())),
                        "system": "WATER",
                        "location": str(r.get("Location", "A")).strip().upper(),
                        "status": str(r.get("Status", "NORMAL")).strip().upper(),
                        "raw": "Imported from SD log.csv"
                    })
                if ins:
                    db.iot_logs.insert_many(ins)
                done(f"นำเข้าข้อมูลประวัติระดับน้ำ {len(ins)} รายการสำเร็จ!")

        render_alarm_dashboard("water", w_df)

    # -----------------------------------------------------------------
    # MODULE 5: FIRE ALARM & RELAY RESET
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("🚨 5."):
        st.subheader("🚨 ระบบแจ้งเตือนอัคคีภัยและรีเซ็ตรีเลย์ (Fire Alarm & Remote Relay Control)")
        st.caption(f"เชื่อมโยงกับบอร์ด ESP32 Fire Alarm (PCF8574 I2C 7 โมดูล `0x20-0x26`) · Alarm Topic: `{cfg_iot['topic_fire']}` · Relay Reset Topic: `{cfg_iot['topic_fire_relay']}`")

        f_top1, f_top2 = st.columns([2, 1])
        with f_top1:
            is_alert = iot_mgr.fire_status == "ALERT"
            st.markdown(f"""
            <div class="glass-kpi" style="padding:1.2rem;">
              <div class="top"><span class="lbl">MAIN FIRE ALARM STATUS</span><span class="ic-badge">🔥</span></div>
              <div class="val" style="color:{'#F87171' if is_alert else '#34D399'} !important;">
                {'🚨 FIRE ALERT! ตรวจพบสัญญาณเตือนภัย' if is_alert else '✅ NORMAL (CLEAR) สถานะปกติ'}
              </div>
              <div class="sub">ตำแหน่งล่าสุด: <b>{esc(iot_mgr.fire_location)}</b></div>
            </div>
            """, unsafe_allow_html=True)

        with f_top2:
            st.markdown("#### ⚡ ควบคุมรีเลย์ตู้ไฟ (Remote Reset)")
            if st.button("⚡ สั่ง RESET RELAY อาราม (MQTT 'reset')", type="primary", use_container_width=True):
                iot_mgr.publish(cfg_iot["topic_fire_relay"], "reset")
                log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
                iot_mgr.handle_message(cfg_iot["topic_fire"], "RESET CLEAR")
                done("ส่งคำสั่ง 'reset' ไปยังหัวข้อ nodemcu/control/relay เรียบร้อยแล้ว!")

            if st.button("🔔 ทดสอบส่งแจ้งเตือนสถานะปกติเข้า LINE OA", use_container_width=True):
                ok_l, info_l = send_line_push("✅ ALARM CLEAR! สถานะปกติ (ทดสอบจากระบบ Admin Portal)")
                done(f"ส่งข้อความเข้ากลุ่ม LINE แล้ว ({info_l})")

        z_cols = st.columns(4)
        z_items = [
            ("A", "อาคาร A (ชั้น 1-8 โซน 1-3)"),
            ("B", "อาคาร B (ชั้น 1-8 โซน 1-3)"),
            ("C", "อาคาร C (ชั้น 1-8 โซน 1-3)"),
            ("D", "อาคาร D (ชั้น 1-8 โซน 1-3)"),
            ("CLUB", "สโมสร / Pavilion"),
            ("LIBRARY", "ห้องสมุด (Library)"),
            ("ST", "บันไดหนีไฟ (A/B/C/D-ST1,2)"),
            ("UNKNOWN", "ไม่ระบุโซน (Unspecified)"),
        ]
        for idx, (zk, zlabel) in enumerate(z_items):
            zst = iot_mgr.fire_zones.get(zk, "NORMAL")
            zc = "pill-alarm" if zst == "ALERT" else "pill-normal"
            z_cols[idx % 4].markdown(
                f'<div class="iot-card" style="margin-bottom:0.6rem;"><div class="hd">{zk} ZONE</div>'
                f'<div class="bd"><span class="nm" style="font-size:0.88rem;">{zlabel}</span>'
                f'<span class="pill {zc}">{zst}</span></div></div>',
                unsafe_allow_html=True
            )

        with st.expander("🧪 จำลองการเกิดเหตุเพลิงไหม้รายโซน (สำหรับทดสอบระบบและแจ้งเตือน LINE OA)"):
            sim_c1, sim_c2, sim_c3 = st.columns([1.2, 1.2, 1])
            sim_bldg = sim_c1.selectbox("เลือกอาคาร / สถานที่", [
                "อาคาร A ชั้น 1 โซน 1", "อาคาร A ชั้น 4 โซน 2",
                "อาคาร B ชั้น 2 โซน 1", "อาคาร C ชั้น 5 โซน 3",
                "อาคาร D ชั้น 3 โซน 1", "สถานที่: สโมสร",
                "สถานที่: ห้องสมุด", "สถานที่: A-ST1", "ตรวจพบสัญญาณอาราม (ไม่ระบุโซน)"
            ])
            send_to_line_too = sim_c2.checkbox("ส่งแจ้งเตือนเข้ากลุ่ม LINE OA ด้วย", value=False)
            if sim_c3.button("🚨 ส่งสัญญาณทดสอบ Fire Alarm", type="primary", use_container_width=True):
                alert_msg = f"🚨 ALARM ALERT!\n- {sim_bldg}"
                iot_mgr.publish(cfg_iot["topic_fire"], alert_msg)
                log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
                if send_to_line_too:
                    send_line_push(alert_msg)
                done(f"จำลองสัญญาณเตือนภัย: {sim_bldg}")

        st.markdown("---")
        st.markdown("#### 📊 สถิติและประวัติสัญญาณแจ้งเตือนอัคคีภัย (Fire Alarm Incident Analytics)")
        fire_logs = list(db.iot_logs.find({"system": "FIRE"}, {"_id": 0, "datetime": 1, "location": 1, "status": 1}).sort("datetime", -1).limit(5000))
        f_df = pd.DataFrame(fire_logs)

        with st.expander("📂 นำเข้าไฟล์ `fire_log.csv` จากการ์ด SD"):
            up_f_csv = st.file_uploader("เลือกไฟล์ fire_log.csv (คอลัมน์ DateTime, Location, Status)", type=["csv"], key="up_fire_csv")
            if up_f_csv is not None and st.button("📥 บันทึกข้อมูลจาก fire_log.csv ลงฐานข้อมูล", key="btn_imp_f"):
                csv_df = pd.read_csv(up_f_csv)
                ins = []
                for _, r in csv_df.iterrows():
                    ins.append({
                        "datetime": str(r.get("DateTime", get_now_str())),
                        "system": "FIRE",
                        "location": str(r.get("Location", "-")).strip(),
                        "status": str(r.get("Status", "CLEAR")).strip().upper(),
                        "raw": "Imported from SD fire_log.csv"
                    })
                if ins:
                    db.iot_logs.insert_many(ins)
                done(f"นำเข้าข้อมูลประวัติอัคคีภัย {len(ins)} รายการสำเร็จ!")

        render_alarm_dashboard("fire", f_df)

    # -----------------------------------------------------------------
    # MODULE 6: GROWATT SPF5000ES SOLAR MONITOR
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("☀️ 6."):
        st.subheader("☀️ ระบบมอนิเตอร์โซลาร์เซลล์ (Growatt SPF5000ES & Google Sheets Sync)")
        st.caption(f"อินเวอร์เตอร์ Serial Number: `{cfg_iot['growatt_sn']}` · บัญชี Growatt: `{cfg_iot['growatt_user']}`")

        g_col1, g_col2, _ = st.columns([1.2, 1.4, 1.4])
        if g_col1.button("🔄 ดึงข้อมูลเรียลไทม์จาก Growatt Cloud", type="primary", use_container_width=True):
            with st.spinner("กำลังล็อกอินและดึงข้อมูลจากเซิร์ฟเวอร์ Growatt..."):
                st.session_state.last_solar_data = fetch_growatt_realtime(sync_sheets=False)
        if g_col2.button("📤 ดึงข้อมูล + บันทึกลง Google Sheets ทันที", use_container_width=True):
            with st.spinner("กำลังดึงข้อมูลและส่งไปยัง Google Apps Script Web App..."):
                st.session_state.last_solar_data = fetch_growatt_realtime(sync_sheets=True)

        solar_df, solar_err = get_solar_sheet_df()  # ข้อมูลจาก Google Sheets (ใช้ทั้งการ์ด PV และแดชบอร์ดด้านล่าง)

        # ถ้ายังไม่มีค่าเรียลไทม์ หรือค่าที่มีเก่ากว่า 5 นาที -> ดึงจาก Growatt ให้เอง (จำกัดไม่เกิน 1 ครั้งต่อ 5 นาที กันยิง Growatt ถี่)
        _s_cur = st.session_state.get("last_solar_data")
        _s_age = solar_age_seconds(_s_cur.get("updated")) if (_s_cur and _s_cur.get("ok")) else None
        if (_s_age is None or _s_age > 300) and (time.time() - st.session_state.get("solar_auto_ts", 0)) > 300:
            st.session_state["solar_auto_ts"] = time.time()
            with st.spinner("กำลังดึงค่าเรียลไทม์ล่าสุดจาก Growatt Cloud..."):
                _auto = fetch_growatt_realtime(sync_sheets=False)
            if _auto.get("ok"):
                st.session_state.last_solar_data = _auto
                st.session_state.pop("solar_auto_err", None)
            else:
                st.session_state["solar_auto_err"] = _auto.get("error")

        sol = st.session_state.get("last_solar_data")
        if not sol:
            last_sol_doc = db.iot_logs.find_one({"system": "SOLAR"}, {"_id": 0}, sort=[("datetime", -1)])
            if last_sol_doc and last_sol_doc.get("data"):
                sol = last_sol_doc["data"]

        if sol and sol.get("ok"):
            if sol.get("sheets_synced"):
                st.success(f"✅ อัปเดตข้อมูลล่าสุดเมื่อ {sol['updated']} (Server: {sol.get('host')}) และบันทึกลง Google Sheets เรียบร้อยแล้ว!")
            else:
                _age = solar_age_seconds(sol.get("updated"))
                if _age is not None and _age > 600:
                    st.warning(f"⏱️ ข้อมูลนี้เก่า ({fmt_age_th(_age)}ที่แล้ว · บันทึกเมื่อ {sol['updated']}) ค่าอาจไม่ตรงกับปัจจุบัน — กด 'ดึงข้อมูลเรียลไทม์จาก Growatt Cloud' เพื่อดึงค่าล่าสุด"
                               + (f" (ดึงอัตโนมัติไม่สำเร็จ: {st.session_state.get('solar_auto_err')})" if st.session_state.get("solar_auto_err") else ""))
                else:
                    st.info(f"📡 ข้อมูลล่าสุดเมื่อ: **{sol['updated']}** · อุณหภูมิอินเวอร์เตอร์: **{sol['invTemp']} °C**")

            # การ์ด SOLAR (PV INPUT): ใช้ค่าแถวล่าสุดจาก Google Sheets (Solar_Data_Log) ถ้ามี ไม่เช่นนั้นใช้ค่าจาก Growatt
            if solar_df is not None and not solar_df.empty:
                _sl = solar_df.iloc[-1]
                pv_card_val = f"{int(_sl['pv'])} W"
                pv_card_sub = f"กระแสชาร์จ: <b>{_sl['pvi']:.1f} A</b> · Google Sheets {_sl['dt'].strftime('%d/%m %H:%M')}"
            else:
                pv_card_val = f"{int(sol['pvP'])} W"
                pv_card_sub = f"แรงดันแผง: <b>{sol['pvV']} V</b> · กระแสชาร์จ: <b>{sol['pvI']} A</b>"
            st.markdown(f"""
            <div class="kpi-grid">
              <div class="glass-kpi">
                <div class="top"><span class="lbl">BATTERY (SOC & VOLTAGE)</span><span class="ic-badge">🔋</span></div>
                <div class="val">{int(sol['soc'])}% <span style="font-size:1rem; color:#94A3B8;">({sol['vBat']} V)</span></div>
                <div class="sub">กำลังไฟแบตเตอรี่: <b>{int(sol['batP'])} W</b> ({sol['batMode']})</div>
              </div>
              <div class="glass-kpi">
                <div class="top"><span class="lbl">SOLAR (PV INPUT)</span><span class="ic-badge">☀️</span></div>
                <div class="val">{pv_card_val}</div>
                <div class="sub">{pv_card_sub}</div>
              </div>
              <div class="glass-kpi">
                <div class="top"><span class="lbl">AC LOAD (OUTPUT)</span><span class="ic-badge">🏠</span></div>
                <div class="val">{int(sol['load'])} W</div>
                <div class="sub">สัดส่วนโหลดใช้งาน: <b>{sol['loadPct']}%</b></div>
              </div>
              <div class="glass-kpi">
                <div class="top"><span class="lbl">GRID IN (AC INPUT)</span><span class="ic-badge">⚡</span></div>
                <div class="val">{int(sol['gridP'])} W</div>
                <div class="sub">แรงดันไฟการไฟฟ้า: <b>{int(sol['gridV'])} V</b> · Temp: <b>{sol['invTemp']}°C</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        elif sol and not sol.get("ok"):
            st.warning(f"⚠️ ไม่สามารถดึงข้อมูลจาก Growatt ได้ในขณะนี้: {sol.get('error')}")
        else:
            st.info("💡 กดปุ่ม **'🔄 ดึงข้อมูลเรียลไทม์จาก Growatt Cloud'** ด้านบนเพื่อแสดงสถานะแบตเตอรี่ แผงโซลาร์ โหลดใช้งาน และไฟการไฟฟ้า")

        st.markdown("---")
        st.markdown("#### ⚡ วิเคราะห์พลังงานโซลาร์เซลล์จาก Google Sheets (Solar_Data_Log)")
        with st.expander("⚙️ แหล่งข้อมูล Google Sheets", expanded=False):
            sh_c1, sh_c2, sh_c3 = st.columns([3, 1, 1.4])
            solar_sheet_id = sh_c1.text_input("Sheet ID", value=SOLAR_SHEET_ID_DEFAULT, key="solar_sheet_id")
            solar_gid = sh_c2.text_input("GID (แท็บ)", value=SOLAR_SHEET_GID_DEFAULT, key="solar_sheet_gid")
            solar_date_order = sh_c3.selectbox("รูปแบบวันที่ในชีต", ["auto", "dmy", "mdy"], key="solar_date_order",
                                               format_func=lambda v: {"auto": "อัตโนมัติ (เดาให้)", "dmy": "วัน/เดือน/ปี", "mdy": "เดือน/วัน/ปี"}[v])
            if st.button("🔄 โหลดข้อมูลจากชีตใหม่", key="solar_sheet_reload"):
                load_solar_sheet.clear()
            solar_upload = st.file_uploader("หรืออัปโหลดไฟล์ CSV ที่ดาวน์โหลดจากชีตเอง (ใช้เมื่อดึงจากชีตตรงๆ ไม่ได้)", type=["csv"], key="solar_csv_upload")
        if solar_df is None:
            st.warning(f"⚠️ ดึงข้อมูลจากชีตไม่สำเร็จ: {solar_err}")
        else:
            render_solar_dashboard(solar_df)

        st.markdown("---")
        st.markdown("#### 📈 ประวัติการบันทึกค่าพลังงานโซลาร์เซลล์ (จากการกดดึง Growatt ในฐานข้อมูล)")
        sol_logs = list(db.iot_logs.find({"system": "SOLAR"}, {"_id": 0}).sort("datetime", -1).limit(200))
        if sol_logs:
            sol_rows = []
            for s in sol_logs:
                d = s.get("data", {})
                sol_rows.append({
                    "วัน-เวลา": s.get("datetime"),
                    "SOC (%)": d.get("soc"),
                    "แรงดันแบต (V)": d.get("vBat"),
                    "สถานะแบต": d.get("batMode"),
                    "กำลังแผง PV (W)": d.get("pvP"),
                    "กระแส PV (A)": d.get("pvI"),
                    "โหลด AC (W)": d.get("load"),
                    "โหลด (%)": d.get("loadPct"),
                    "ไฟ Grid (W)": d.get("gridP"),
                    "อุณหภูมิ (°C)": d.get("invTemp")
                })
            st.dataframe(pd.DataFrame(sol_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("ยังไม่มีประวัติการดึงค่าพลังงานในฐานข้อมูล")

    # -----------------------------------------------------------------
    # MODULE 7: SYSTEM SETTINGS, IOT CREDENTIALS & TECH ACCOUNTS
    # -----------------------------------------------------------------
    elif selected_admin_module.startswith("⚙️ 7."):
        st.subheader("⚙️ ตั้งค่าระบบ, เครือข่ายฮาร์ดแวร์ IoT และบัญชีช่าง")
        set_tab1, set_tab2, set_tab3, set_tab4, set_tab5 = st.tabs([
            "🔧 7.1 เกณฑ์แจ้งเตือน & โควต้าตรวจประจำวัน",
            "👷 7.2 จัดการบัญชีช่าง (เพิ่ม/แก้ไข/นำเข้า .txt)",
            "📡 7.3 ตั้งค่า MQTT, LINE OA & Growatt Solar",
            "🖥️ 7.4 MQTT Live Monitor (Raw Feed)",
            "📜 7.5 ประวัติการกระทำ"
        ])

        with set_tab1:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.markdown("#### ⚠️ ตั้งค่าเกณฑ์แจ้งเตือนอุปกรณ์ทั่วไปใกล้หมด")
                with st.form("low_stock_setting_form"):
                    new_threshold = st.number_input("แจ้งเตือนเมื่อจำนวนน้อยกว่าหรือเท่ากับ (ชิ้น)", min_value=0, value=low_stock_limit)
                    if st.form_submit_button("บันทึกค่าเกณฑ์การแจ้งเตือน", type="primary"):
                        set_settings_val('low_stock_threshold', new_threshold)
                        done("บันทึกค่าการแจ้งเตือนสำเร็จ!")
            with col_s2:
                st.markdown("#### 🔄 ตั้งค่าและเพิ่มโควต้าการตรวจเช็คประจำวัน (นับรวมทุกคน)")
                current_base_quota = int(get_settings_val('global_daily_quota', '3'))
                with st.form("global_quota_form"):
                    new_base_quota = st.number_input("กำหนดโควต้ารอบตรวจมาตรฐานต่อวัน (รอบ)", min_value=1, value=current_base_quota)
                    reset_date = st.date_input("เลือกวันที่ต้องการเพิ่มรอบตรวจพิเศษ", value=get_now_th().date())
                    date_str = reset_date.strftime("%Y-%m-%d")
                    current_extra = int(get_settings_val(f"extra_quota_{date_str}", '0'))
                    add_more_quota = st.number_input("ระบุจำนวนรอบพิเศษสำหรับวันนี้", min_value=0, value=current_extra)
                    if st.form_submit_button("บันทึกการตั้งค่าโควต้า", type="primary"):
                        set_settings_val('global_daily_quota', new_base_quota)
                        set_settings_val(f"extra_quota_{date_str}", add_more_quota)
                        done("บันทึกการตั้งค่าโควต้าเรียบร้อยแล้ว!")

        with set_tab2:
            st.markdown("#### 🪪 ตั้งชื่อแสดงผลบัญชีผู้ใช้")
            profile_users = [d.get("username", "") for d in db.tech_users.find({}, {"username": 1, "_id": 0})]
            profile_roles = {u: "ช่าง" for u in profile_users}
            try:
                profile_admin_user = str(st.secrets["admin"]["username"])
                if profile_admin_user:
                    profile_users.insert(0, profile_admin_user)
                    profile_roles[profile_admin_user] = "ผู้ดูแลระบบ"
            except Exception:
                pass
            profile_users = list(dict.fromkeys([u for u in profile_users if u]))
            profile_map = {d["username"]: d.get("display_name", "") for d in db.user_profiles.find({}, {"_id": 0, "username": 1, "display_name": 1})}
            editor_rows = [{"Username": u, "ประเภทบัญชี": profile_roles.get(u, "ช่าง"), "ชื่อแสดงผล": profile_map.get(u, "")} for u in profile_users]
            editor_key = f"user_profiles_editor_{st.session_state.get('profile_editor_ver', 0)}"
            edited_profiles = st.data_editor(
                pd.DataFrame(editor_rows),
                use_container_width=True,
                hide_index=True,
                disabled=["Username", "ประเภทบัญชี"],
                key=editor_key,
                column_config={"ชื่อแสดงผล": st.column_config.TextColumn("ชื่อแสดงผล", help="กรอกชื่อที่ต้องการให้แสดงแทน Username")},
            )
            if st.button("💾 บันทึกชื่อแสดงผลทั้งหมด", type="primary", key="save_all_display_names"):
                for _, profile_row in edited_profiles.iterrows():
                    username_value = str(profile_row["Username"])
                    display_value = str(profile_row.get("ชื่อแสดงผล", "") or "").strip()
                    if display_value:
                        db.user_profiles.update_one({"username": username_value}, {"$set": {"display_name": display_value}}, upsert=True)
                    else:
                        db.user_profiles.delete_one({"username": username_value})
                st.session_state.profile_editor_ver = st.session_state.get("profile_editor_ver", 0) + 1
                done("บันทึกชื่อแสดงผลทั้งหมดแล้ว")
            st.markdown("---")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**➕ เพิ่มบัญชีช่างใหม่ (รายบุคคล)**")
                with st.form("add_tech_form", clear_on_submit=True):
                    new_t_user = st.text_input("Username ช่าง")
                    new_t_pass = st.text_input("Password ช่าง", type="password")
                    if st.form_submit_button("สร้างบัญชีช่าง", type="primary"):
                        if new_t_user.strip() and new_t_pass.strip():
                            if not db.tech_users.find_one({"username": new_t_user}, {"_id": 1}):
                                t_id = get_next_sequence("tech_users_id")
                                db.tech_users.insert_one({"id": t_id, "username": new_t_user, "password": hash_user_password(new_t_pass)})
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
                            edit_p = st.text_input("Password ใหม่ (เว้นว่างหากไม่เปลี่ยน)", type="password")
                            col_tu1, col_tu2 = st.columns(2)
                            if col_tu1.form_submit_button("บันทึกการแก้ไข", type="primary"):
                                update_doc = {"username": edit_u}
                                if edit_p:
                                    update_doc["password"] = hash_user_password(edit_p)
                                db.tech_users.update_one({"id": t_id_int}, {"$set": update_doc})
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
                                    db.tech_users.insert_one({"id": get_next_sequence("tech_users_id"), "username": u, "password": hash_user_password(p)})
                                    existing_users.add(u)
                                    success_count += 1
                            get_tech_users_df.clear()
                            done(f"นำเข้าสำเร็จ! เพิ่มใหม่ {success_count} บัญชี (ซ้ำ {dup_count} บัญชี)")

        with set_tab3:
            st.markdown("#### 📡 ตั้งค่าการเชื่อมต่อ HiveMQ Cloud, LINE OA และ Growatt Solar")
            st.info("ข้อมูลเชื่อมต่ออ่านจาก App settings → Secrets ในส่วน [iot] เท่านั้น เพื่อไม่บันทึกข้อมูลลับลง MongoDB")
            cfg = get_iot_config()
            status_rows = [
                {"บริการ": "MQTT", "สถานะ": "ตั้งค่าแล้ว" if cfg["mqtt_server"] and cfg["mqtt_user"] and cfg["mqtt_pass"] else "ยังตั้งค่าไม่ครบ"},
                {"บริการ": "LINE", "สถานะ": "ตั้งค่าแล้ว" if cfg["line_token"] and cfg["line_group_id"] else "ยังตั้งค่าไม่ครบ"},
                {"บริการ": "Growatt", "สถานะ": "ตั้งค่าแล้ว" if cfg["growatt_user"] and cfg["growatt_pass"] and cfg["growatt_sn"] else "ยังตั้งค่าไม่ครบ"},
                {"บริการ": "Google Apps Script", "สถานะ": "ตั้งค่าแล้ว" if cfg["google_webapp_url"] else "ยังตั้งค่าไม่ครบ"},
            ]
            st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
            if st.button("🔄 เชื่อมต่อ MQTT ใหม่", type="primary"):
                iot_mgr.connect()
                done("สั่งเชื่อมต่อ MQTT ใหม่แล้ว")

        with set_tab4:
            st.markdown("#### 🖥️ มอนิเตอร์ข้อความ MQTT แบบสด (Live MQTT Broker Feed)")
            with st.form("custom_mqtt_pub"):
                cp1, cp2, cp3 = st.columns([1.2, 1.5, 0.8])
                custom_topic = cp1.text_input("Topic", value="esp8266/servo")
                custom_payload = cp2.text_input("Payload / Message", value="UP")
                if cp3.form_submit_button("📤 Publish", type="primary", use_container_width=True):
                    iot_mgr.publish(custom_topic, custom_payload)
                    log_audit("IOT_COMMAND", "MQTT", detail="Publish command requested")
                    st.toast(f"Published to {custom_topic}: {custom_payload}", icon="📡")
                    st.rerun()
            if iot_mgr.raw_mqtt_feed:
                st.dataframe(pd.DataFrame(iot_mgr.raw_mqtt_feed), use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีข้อความ MQTT เข้ามาในเซสชันนี้")

        with set_tab5:
            st.markdown("#### 📜 ประวัติการกระทำของผู้ใช้ (Audit Log)")
            st.caption("แสดงผู้กระทำ เวลา รายการ และค่าก่อน/หลัง เฉพาะการกระทำที่บันทึกในรุ่นนี้")
            audit_rows = list(db.audit_logs.find({}, {"_id": 0}).sort("datetime", -1).limit(500))
            if audit_rows:
                audit_df = pd.DataFrame(audit_rows)
                if "actor" in audit_df.columns:
                    audit_df["actor"] = audit_df["actor"].map(get_display_name)
                audit_df = audit_df.rename(columns={"datetime": "เวลา", "actor": "ผู้กระทำ", "role": "บทบาท", "action": "การกระทำ", "target": "รายการ", "before": "ค่าก่อน", "after": "ค่าหลัง", "detail": "รายละเอียด"})
                st.dataframe(audit_df, use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีประวัติการกระทำ")

# =====================================================================
#  ROLE 2: TECH VIEW (PURE INVENTORY ONLY - NO MQTT/DRAWER/WATER/FIRE)
# =====================================================================
elif st.session_state.role in TECH_ROLES:
    # ซ่อน Sidebar ของช่างทั้งหมด
    st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)

    # ส่วนหัวของช่าง: ไม่มีป้าย MQTT, Drawer, Water, Fire ใดๆ ทั้งสิ้น
    st.markdown(f"""
    <div class="app-hero">
      <div>
        <div class="t">🛠️ ระบบเช็คสถานะอุปกรณ์เครื่องมือช่าง & สระว่ายน้ำ</div>
        <div class="s">ประจำวันที่ {get_now_str("%d/%m/%Y")}</div>
      </div>
      <div class="badge-row">
        <span class="status-pill-top info">👷 {esc(get_display_name(st.session_state.username))} ({esc(st.session_state.role)})</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.role == ROLE_TECH_SP:
        col_banner, col_btn_back = st.columns([3, 1])
        with col_banner:
            st.info("⭐ คุณเข้าใช้งานในสถานะ **ช่างประจำอาคารพิเศษ** (สิทธิ์พิเศษจากแอดมิน)")
        with col_btn_back:
            if st.button("🔙 สลับกลับเป็น 'ผู้ออกแบบ/ดูแลระบบ'", type="primary", use_container_width=True, key="banner_switch_back"):
                switch_role(ROLE_ADMIN)

    # KPI เฉพาะคลังอุปกรณ์เท่านั้น
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="glass-kpi">
        <div class="top"><span class="lbl">รายการอุปกรณ์ทั้งหมด</span><span class="ic-badge">🛠️</span></div>
        <div class="val"><span class="cnt" style="--n:{len(items_df)}"></span></div>
      </div>
      <div class="glass-kpi">
        <div class="top"><span class="lbl">{abn_label}</span><span class="ic-badge">⚠️</span></div>
        <div class="val" style="color:{'#F87171' if abn_cnt else '#34D399'} !important;"><span class="cnt" style="--n:{abn_cnt}"></span></div>
      </div>
      <div class="glass-kpi">
        <div class="top"><span class="lbl">กำลังถูกยืมอยู่</span><span class="ic-badge">📤</span></div>
        <div class="val"><span class="cnt" style="--n:{borrowed_cnt}"></span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        if abn_cnt:
            with st.expander(f"❌ {abn_title} ({abn_cnt} รายการ)"):
                st.dataframe(abnormal_items[['name', 'category', 'status', 'quantity']], hide_index=True, use_container_width=True)
        else:
            st.success("✅ อุปกรณ์ทุกชิ้นอยู่ในสภาพปกติ")
    with col_a2:
        if low_cnt:
            with st.expander(f"⚠️ อุปกรณ์ทั่วไปเหลือน้อย ({low_cnt} รายการ)"):
                st.dataframe(low_stock_items[['name', 'category', 'quantity']], hide_index=True, use_container_width=True)
        else:
            st.success("✅ อุปกรณ์ทั่วไปทุกชิ้นมีจำนวนเพียงพอ")

    # แจ้งเตือนรายการที่ถูกปรับลดจำนวนใน 7 วันล่าสุด (ถ้าไม่มีการปรับลดเลย จะไม่แสดงอะไร)
    reduced_rows = get_recent_reductions(get_inspections_list(), days=7)
    if reduced_rows:
        with st.expander(f"📉 มีการปรับลดจำนวนอุปกรณ์ใน 7 วันล่าสุด ({len(reduced_rows)} รายการ)"):
            st.dataframe(pd.DataFrame(reduced_rows), hide_index=True, use_container_width=True)

    if borrowed_cnt:
        with st.expander(f"📤 อุปกรณ์ที่กำลังถูกยืม ({borrowed_cnt} รายการ)"):
            st.dataframe(pd.DataFrame([{
                "อุปกรณ์": item_name_map.get(t["item_id"], "Unknown"),
                "จำนวนที่ยืม": t.get("quantity", 1),
                "ผู้ยืม": t.get("borrower_name"),
                "ผู้ให้ยืม": get_display_name(t.get("giver_name")),
                "วันที่ยืม": t.get("borrow_date"),
            } for t in active_borrows]), hide_index=True, use_container_width=True)

    tech_main_tab = st.tabs(["📋 ตรวจสอบอุปกรณ์", "📦 เบิกอุปกรณ์", "🔄 ระบบยืม-คืน อุปกรณ์"])

    with tech_main_tab[2]:
        render_borrow_return_system()

    with tech_main_tab[1]:
        st.markdown("### 📦 คำขอเพิ่มสต็อก (อุปกรณ์ช่างทั่วไป & อุปกรณ์สระว่ายน้ำ)")
        tools_requisition_df = items_df[
            ((items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['subcategory'] == 'อุปกรณ์ช่างทั่วไป')) |
            (items_df['category'] == 'อุปกรณ์สระว่ายน้ำ')
        ] if not items_df.empty else pd.DataFrame()

        req_search_keyword = st.text_input("🔍 ค้นหาชื่ออุปกรณ์...", placeholder="พิมพ์ชื่ออุปกรณ์เพื่อค้นหา", key="req_general_search")
        if not tools_requisition_df.empty and req_search_keyword.strip():
            tools_requisition_df = tools_requisition_df[tools_requisition_df['name'].str.contains(req_search_keyword.strip(), case=False, na=False)]

        if not tools_requisition_df.empty:
            with st.form("requisition_request_form", clear_on_submit=True):
                item_dict = {f"{row['name']} (คงเหลือในคลัง: {row['quantity']} ชิ้น)": row['id']
                             for _, row in tools_requisition_df.iterrows()}
                sel_req_label = st.selectbox("เลือกอุปกรณ์ที่ต้องการเพิ่มจำนวน *", list(item_dict.keys()))
                req_qty = st.number_input("จำนวนที่ต้องการเพิ่มเข้าคลัง *", min_value=1, value=1)
                req_note = st.text_area("หมายเหตุ / เหตุผลที่ขอเพิ่ม *")

                if st.form_submit_button("📤 ส่งคำขอเบิกของ (รอผู้ออกแบบ/ดูแลระบบอนุมัติ)", type="primary"):
                    if req_note.strip():
                        req_selected_id = item_dict[sel_req_label]
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
        if my_reqs_list:
            st.dataframe(pd.DataFrame([{
                "รหัส": r["id"], "ชื่ออุปกรณ์": item_name_map.get(r["item_id"], "Unknown"),
                "จำนวนที่ขอ": r.get("quantity"), "หมายเหตุ": r.get("note"),
                "วันที่ขอ": r.get("request_date"), "วันที่อนุมัติ": r.get("approval_date"),
                "สถานะ": r.get("status")
            } for r in my_reqs_list]), use_container_width=True, hide_index=True)
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
                tools_all_df = items_df[(items_df['category'] == 'อุปกรณ์ช่าง') & (items_df['orig_quantity'] > 0)] if not items_df.empty else pd.DataFrame()
                if not tools_all_df.empty:
                    render_tool_inspection_list(tools_all_df)

                    st.markdown("### 📸 รูปถ่ายอุปกรณ์ที่ตรวจเช็ค")
                    st.info("💡 สามารถกดเลือกหรือถ่ายรูปให้ครบทั้ง 4 รูปพร้อมกันในช่องอัปโหลดด้านล่างนี้ได้เลยครับ")

                    photo_files = st.file_uploader(
                        "เลือก / ถ่ายรูปภาพรวมหน้างาน (ครบ 4 รูป)",
                        type=["jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key=f"tech_multi_uploader_{st.session_state.uploader_version}"
                    )

                    num_photos = len(photo_files) if photo_files else 0
                    st.progress(min(num_photos / 4.0, 1.0), text=f"📸 แนบรูปแล้ว {num_photos}/4 รูป")

                    if photo_files:
                        cols_prev = st.columns(min(num_photos, 4))
                        for p_idx, p_file in enumerate(photo_files):
                            with cols_prev[p_idx % 4]:
                                st.image(p_file, caption=f"รูปที่ {p_idx + 1}", use_container_width=True)

                    if st.button(f"💾 ยืนยันส่งผลตรวจ (รอบที่ {global_count + 1})", type="primary", use_container_width=True):
                        item_reports = {}
                        for _, row in tools_all_df.iterrows():
                            rid = int(row['id'])
                            subcat = str(row.get('subcategory', ''))
                            if subcat == "อุปกรณ์ช่างทั่วไป":
                                q_val = int(st.session_state.get(f"gen_q_{rid}", row['quantity']))
                                item_reports[rid] = {"type": "general", "quantity": q_val}
                            else:
                                sel_st = st.session_state.get(f"status_sel_{rid}", "ปกติ")
                                item_reports[rid] = {
                                    "type": "tool",
                                    "flagged": sel_st != "ปกติ",
                                    "status": sel_st,
                                    "detail": st.session_state.get(f"issue_detail_{rid}", "") or "",
                                    "qty": int(st.session_state.get(f"issue_qty_{rid}", 1) or 1),
                                }

                        error_msg = ""
                        for item_id, data in item_reports.items():
                            if data["type"] == "tool" and data["flagged"]:
                                if data["status"] == "กำลังใช้งาน" and not data["detail"].strip():
                                    error_msg = "❌ กรุณากรอกรายละเอียดการใช้งานสำหรับรายการที่เลือก 'กำลังใช้งาน'"
                                    break

                        if not error_msg and num_photos < 4:
                            error_msg = f"❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานให้ครบ 4 รูป (ปัจจุบันเลือกแล้ว {num_photos} รูป)"

                        if error_msg:
                            st.error(error_msg)
                        else:
                            with st.spinner("กำลังบันทึกผลการตรวจ..."):
                                photos_b64 = [compress_image_to_base64(f, max_size=(1000, 1000), quality=70) for f in photo_files]
                                flagged_summaries, bulk_operations = [], []
                                changes_list = []  # เก็บรายการที่จำนวนลดลง เพื่อแจ้งเตือนในหน้าช่าง
                                row_map = tools_all_df.set_index('id')

                                for item_id, data in item_reports.items():
                                    orig_q = int(row_map.loc[item_id, 'orig_quantity'])
                                    item_name = row_map.loc[item_id, 'name']
                                    if data["type"] == "general":
                                        new_q = data["quantity"]
                                        bulk_operations.append(pymongo.operations.UpdateOne(
                                            {"id": item_id}, {"$set": {"quantity": new_q, "orig_quantity": new_q, "status": "ปกติ"}}))
                                        if new_q != int(row_map.loc[item_id, 'quantity']):
                                            flagged_summaries.append(f"{item_name}: ปรับสต็อกเหลือ {new_q} ชิ้น")
                                        if new_q < int(row_map.loc[item_id, 'quantity']):
                                            changes_list.append({"item_id": int(item_id), "name": item_name, "old_qty": int(row_map.loc[item_id, 'quantity']), "new_qty": new_q, "reason": "ปรับสต็อก"})
                                    else:
                                        if data["flagged"]:
                                            final_st = f"กำลังใช้งาน ({data['detail']})" if (data["status"] == "กำลังใช้งาน" and data["detail"].strip()) else data["status"]
                                            new_q = 0 if data["status"] == "อุปกรณ์หมด" else max(0, orig_q - data["qty"])
                                            bulk_operations.append(pymongo.operations.UpdateOne(
                                                {"id": item_id}, {"$set": {"status": final_st, "quantity": new_q}}))
                                            detail_txt = f"{item_name}: {data['status']}" + (f" ({data['detail']})" if data['detail'] else "")
                                            flagged_summaries.append(detail_txt)
                                            if new_q < int(row_map.loc[item_id, 'quantity']):
                                                changes_list.append({"item_id": int(item_id), "name": item_name, "old_qty": int(row_map.loc[item_id, 'quantity']), "new_qty": new_q, "reason": data['status']})
                                        else:
                                            bulk_operations.append(pymongo.operations.UpdateOne(
                                                {"id": item_id}, {"$set": {"status": "ปกติ", "quantity": orig_q}}))

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
                                    "changes": changes_list,
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
                pool_photo_files = st.file_uploader(
                    "เลือก / ถ่ายรูปภาพสระว่ายน้ำรวม (ครบ 4 รูป)",
                    type=["jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                    key=f"tech_pool_multi_{st.session_state.uploader_version}"
                )

                num_pool_photos = len(pool_photo_files) if pool_photo_files else 0
                st.progress(min(num_pool_photos / 4.0, 1.0), text=f"📸 แนบรูปแล้ว {num_pool_photos}/4 รูป")

                if pool_photo_files:
                    cols_pool_prev = st.columns(min(num_pool_photos, 4))
                    for p_idx, p_file in enumerate(pool_photo_files):
                        with cols_pool_prev[p_idx % 4]:
                            st.image(p_file, caption=f"รูปที่ {p_idx + 1}", use_container_width=True)

                if st.button("💾 บันทึกจำนวนอุปกรณ์สระว่ายน้ำ", type="primary", use_container_width=True):
                    if num_pool_photos < 4:
                        st.error(f"❌ กรุณาอัปโหลดรูปถ่ายรวมหน้างานสระว่ายน้ำให้ครบ 4 รูป (ปัจจุบันเลือกแล้ว {num_pool_photos} รูป)")
                    else:
                        with st.spinner("กำลังบันทึกข้อมูล..."):
                            photos_b64 = [compress_image_to_base64(f, max_size=(1000, 1000), quality=70) for f in pool_photo_files]
                            pool_summaries, bulk_pool_ops, pool_changes = [], [], []
                            row_map = pool_all_df.set_index('id')

                            for item_id in pool_all_df['id']:
                                rid = int(item_id)
                                key = f"pool_q_{rid}"
                                if key not in st.session_state:
                                    continue
                                q_val = int(st.session_state[key])
                                old_q = int(row_map.loc[rid, 'quantity'])
                                if q_val != old_q:
                                    bulk_pool_ops.append(pymongo.operations.UpdateOne({"id": rid}, {"$set": {"quantity": q_val, "orig_quantity": q_val}}))
                                    pool_summaries.append(f"{row_map.loc[rid, 'name']}: ปรับจาก {old_q} เหลือ {q_val}")
                                    if q_val < old_q:
                                        pool_changes.append({"item_id": rid, "name": row_map.loc[rid, 'name'], "old_qty": old_q, "new_qty": q_val, "reason": "ปรับจำนวน"})

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
                                "changes": pool_changes,
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
