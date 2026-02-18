import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# 1. โหลดค่าการเชื่อมต่อจากไฟล์ .env
load_dotenv()

# 2. ตั้งค่าพาธไฟล์ Excel ของเพื่อน (ระบุที่อยู่ไฟล์ให้ถูกต้อง)
EXCEL_PATH = r"C:\data\problem.xlsx" 

def migrate_excel_to_mongodb():
    try:
        # --- อ่านข้อมูลจาก Excel ---
        print("🔍 กำลังอ่านไฟล์ Excel...")
        df = pd.read_excel(EXCEL_PATH)
        
        # ล้างค่าว่าง (NaN) ให้เป็นข้อความว่าง เพื่อป้องกัน Error ในฐานข้อมูล
        df = df.fillna("")
        
        # แปลงข้อมูลใน DataFrame ให้เป็น List ของ Dictionary (JSON format)
        records = df.to_dict('records')
        print(f"📦 พบข้อมูลทั้งหมด {len(records)} รายการ")

        # --- เชื่อมต่อ MongoDB Atlas ---
        client = MongoClient(os.getenv("MONGO_DETAILS"))
        db = client.factory_db
        
        # สร้าง Collection ใหม่ชื่อ 'troubleshooting_guide' สำหรับเก็บข้อมูลจาก Excel
        collection = db.troubleshooting_guide
        
        # ล้างข้อมูลเก่าออกก่อน (ถ้ามี) เพื่อให้ข้อมูลเป็นเวอร์ชันล่าสุดเสมอ
        print("🗑️ กำลังล้างข้อมูลเก่าใน Collection...")
        collection.delete_many({})
        
        # --- อัปโหลดข้อมูล ---
        print("🚀 กำลังส่งข้อมูลขึ้น MongoDB Atlas...")
        if records:
            collection.insert_many(records)
            print("✅ สำเร็จ! ข้อมูลคู่มือถูกเก็บไว้บน Cloud เรียบร้อยแล้ว")
        else:
            print("⚠️ ไม่พบข้อมูลในไฟล์ Excel")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    migrate_excel_to_mongodb()