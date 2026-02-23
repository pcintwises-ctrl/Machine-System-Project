import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# โหลดค่าการเชื่อมต่อจากไฟล์ .env
load_dotenv()

# ตั้งค่าพาธไฟล์ Excel
EXCEL_PATH = r"C:\data\problem.xlsx" 

def migrate_excel_to_mongodb():
    try:
        if not os.path.exists(EXCEL_PATH):
            print(f"❌ ไม่พบไฟล์ Excel ที่: {EXCEL_PATH}")
            return

        print("🔍 กำลังอ่านไฟล์ Excel...")
        df = pd.read_excel(EXCEL_PATH)
        
        # เปลี่ยนชื่อคอลัมน์ให้ตรงกับที่หน้าเว็บ (JS) เรียกใช้งาน
        rename_map = {
            "solv": "solution",
            "Cause & Positions to be checked": "cause",
            "link document": "link_document",
            "error code": "error_code",
            "ModelLine": "model" # ใช้ ModelLine เป็น model ไปก่อน
        }
        df.rename(columns=rename_map, inplace=True)
        
        # จัดการค่าว่างให้เป็น None (ไม่ใส่ NaN เพราะ MongoDB จะ Error)
        df = df.where(pd.notnull(df), None)
        
        records = df.to_dict('records')
        print(f"📦 พบข้อมูลทั้งหมด {len(records)} รายการ")

        # เชื่อมต่อ MongoDB Atlas
        mongo_uri = os.getenv("MONGO_DETAILS")
        if not mongo_uri:
            print("❌ ไม่พบ MONGO_DETAILS ในไฟล์ .env")
            return

        client = MongoClient(mongo_uri)
        db = client.factory_db
        collection = db.troubleshooting_guide
        
        # ล้างข้อมูลเก่าและอัปโหลดใหม่
        print("🗑️ กำลังล้างข้อมูลเก่า...")
        collection.delete_many({})
        
        print("🚀 กำลังส่งข้อมูลขึ้น MongoDB Atlas...")
        if records:
            result = collection.insert_many(records)
            print(f"✅ สำเร็จ! อัปโหลดข้อมูลใหม่ {len(result.inserted_ids)} รายการเรียบร้อยแล้ว")
        else:
            print("⚠️ ไม่มีข้อมูลให้อัปโหลด")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    migrate_excel_to_mongodb()