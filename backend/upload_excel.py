import pandas as pd
from pymongo import MongoClient
import math

# --- ⚙️ ตั้งค่าระบบ ---
# 1. ใส่ลิงก์ MongoDB Atlas ของเพื่อนตรงนี้
MONGO_URL = "mongodb+srv://phonlawat_api:kPOIUadGVRbjOM59@cluster0.bkogsh0.mongodb.net/?appName=Cluster0"
DB_NAME = "factory_db"
COLLECTION_NAME = "troubleshooting_guide"

# 2. ใส่ชื่อไฟล์ Excel ของเพื่อนตรงนี้
EXCEL_FILE = r"C:\Users\Lenovo\OneDrive\Desktop\Machine-System-Project\backend\data.xlsx" 

def import_to_database():
    try:
        print(f"⏳ กำลังอ่านข้อมูลจาก {EXCEL_FILE} (ชีต: Sheet2)...")
        # สั่งให้อ่านเฉพาะ 'Sheet2' ตามที่เพื่อนระบุ
        df = pd.read_excel(EXCEL_FILE, sheet_name='Sheet2', engine='openpyxl')
        
        # จัดการช่องว่างใน Excel ให้กลายเป็น "-"
        df = df.fillna("-")

        # เชื่อมต่อฐานข้อมูล Cloud
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # 🌟 เพิ่มคำสั่งลบข้อมูลเก่าทั้งหมดตรงนี้ 🌟
        print("🗑️ กำลังล้างข้อมูลเก่าทั้งหมดใน Database...")
        deleted_result = collection.delete_many({})
        print(f"✅ ลบข้อมูลเก่าทิ้งไปแล้วจำนวน {deleted_result.deleted_count} รายการ!")

        records_to_insert = []
        for index, row in df.iterrows():
            # ดึงข้อมูลให้ตรงกับหัวคอลัมน์ใน Excel ที่สแกนเจอเป๊ะๆ
            machine_val = str(row.get('machine', '-')).strip()
            model_val = str(row.get('Model', '-')).strip()
            line_val = str(row.get('Line', '-')).strip()
            problem_val = str(row.get('problem', '-')).strip()
            cause_val = str(row.get('Cause & Positions to be checked', '-')).strip()
            solv_val = str(row.get('solv', '-')).strip()
            error_code_val = str(row.get('error code', '-')).strip()
            link_doc_val = str(row.get('link document', '-')).strip()
            image_path_val = str(row.get('image_path', '-')).strip()
            
            # ป้องกันค่า 'nan' โผล่ไปในฐานข้อมูล
            def clean_val(val):
                return "-" if val.lower() == 'nan' else val

            # โครงสร้างที่จะโยนขึ้น Database
            doc = {
                "machine": clean_val(machine_val),
                "model": clean_val(model_val),
                "line": clean_val(line_val),
                "process": "-",   # ในไฟล์ไม่มีคอลัมน์ process ให้เป็น - ไว้ก่อน
                "problem": clean_val(problem_val),
                "cause": clean_val(cause_val),
                "solution": clean_val(solv_val), 
                
                # เก็บข้อมูลใหม่ที่มีใน Excel เข้าไปด้วย
                "error_code": clean_val(error_code_val),
                "link_document": clean_val(link_doc_val),
                "image_path": clean_val(image_path_val),
                
                # เก็บชื่อคอลัมน์เดิมไว้เผื่อ API เก่าเรียกใช้งาน
                "Cause & Positions to be checked": clean_val(cause_val),
                "solv": clean_val(solv_val)
            }
            records_to_insert.append(doc)

        if records_to_insert:
            # โยนข้อมูลทั้งหมดเข้า Database รวดเดียว!
            collection.insert_many(records_to_insert)
            print(f"✅ อัปโหลดข้อมูลใหม่สำเร็จจำนวน {len(records_to_insert)} รายการ!")
        else:
            print("⚠️ ไม่พบข้อมูลใน Sheet2 เลยครับ")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {str(e)}")

if __name__ == "__main__":
    # ⚠️ แจ้งเตือนก่อนรันเพื่อความปลอดภัย
    confirm = input("⚠️ คำเตือน: ข้อมูลเก่าทั้งหมดในระบบจะถูกลบทิ้ง! พิมพ์ 'Y' เพื่อยืนยันการทำต่อ: ")
    if confirm.upper() == 'Y':
        import_to_database()
    else:
        print("🛑 ยกเลิกการอัปเดตข้อมูล")