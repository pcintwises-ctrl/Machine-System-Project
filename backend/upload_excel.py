import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import sys

# 1. โหลดค่าการเชื่อมต่อจากไฟล์ .env
load_dotenv()

# 2. ตั้งค่าพาธไฟล์ Excel (ตรวจสอบให้มั่นใจว่าไฟล์อยู่ที่นี่จริงๆ)
EXCEL_PATH = r"C:\data\problem.xlsx" 

def migrate_excel_to_mongodb():
    try:
        # --- ขั้นตอนที่ 1: อ่านไฟล์ Excel ---
        if not os.path.exists(EXCEL_PATH):
            print(f"❌ ไม่พบไฟล์ Excel ที่: {EXCEL_PATH}")
            return

        print("🔍 กำลังอ่านไฟล์ Excel...")
        df = pd.read_excel(EXCEL_PATH)
        
        # ล้างค่าว่าง (NaN) ให้เป็นข้อความว่างเพื่อป้องกัน Error
        df = df.fillna("")
        
        # ตรวจสอบชื่อคอลัมน์ (เลือกเฉพาะคอลัมน์ที่จำเป็น)
        # หากชื่อคอลัมน์ใน Excel ของเพื่อนต่างออกไป ให้แก้ชื่อใน [] นะครับ
        required_cols = ["machine", "solv", "Cause & Positions to be checked"]
        for col in required_cols:
            if col not in df.columns:
                print(f"⚠️ คำเตือน: ไม่พบคอลัมน์ '{col}' ในไฟล์ Excel (ข้อมูลอาจแสดงผลไม่ครบ)")

        records = df.to_dict('records')
        print(f"📦 พบข้อมูลทั้งหมด {len(records)} รายการ")

        # --- ขั้นตอนที่ 2: เชื่อมต่อ MongoDB Atlas ---
        mongo_uri = os.getenv("MONGO_DETAILS")
        if not mongo_uri:
            print("❌ ไม่พบ MONGO_DETAILS ในไฟล์ .env")
            return

        client = MongoClient(mongo_uri)
        # ระบุชื่อ Database และ Collection ให้ชัดเจน
        db = client.factory_db
        collection = db.troubleshooting_guide
        
        print(f"📡 กำลังเชื่อมต่อ Database: {db.name}")

        # --- ขั้นตอนที่ 3: ล้างข้อมูลเก่าและอัปโหลดใหม่ ---
        print("🗑️ กำลังล้างข้อมูลเก่าใน Collection: troubleshooting_guide...")
        delete_result = collection.delete_many({})
        print(f"🧹 ลบข้อมูลเดิมออกแล้ว {delete_result.deleted_count} รายการ")
        
        print("🚀 กำลังส่งข้อมูลขึ้น MongoDB Atlas...")
        if records:
            result = collection.insert_many(records)
            print(f"✅ สำเร็จ! อัปโหลดข้อมูลใหม่ {len(result.inserted_ids)} รายการเรียบร้อยแล้ว")
        else:
            print("⚠️ ไม่มีข้อมูลให้อัปโหลด")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดร้ายแรง: {e}")

if __name__ == "__main__":
    migrate_excel_to_mongodb()