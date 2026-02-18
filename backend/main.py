from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime

# 1. โหลดค่าการตั้งค่าจากไฟล์ .env
load_dotenv()

app = FastAPI()

# ตั้งค่า CORS ให้หน้าเว็บ index.html คุยกับ Backend ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. ตั้งค่าการเชื่อมต่อฐานข้อมูล MongoDB Atlas
# MONGO_DETAILS ต้องระบุในไฟล์ .env ให้ถูกต้อง
client = AsyncIOMotorClient(os.getenv("MONGO_DETAILS"))
db = client.factory_db
machine_collection = db.machine_data
guide_collection = db.troubleshooting_guide

# 3. ตั้งค่า Cloudinary สำหรับเก็บรูปภาพ
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# --- API Endpoints ---

# ดึงประวัติอุบัติการณ์ทั้งหมด (ใช้สำหรับระบบแนะนำ Machine ID ในหน้าเว็บ)
@app.get("/get-all-machines")
async def get_all_machines():
    try:
        # ดึงข้อมูลจาก machine_data เรียงตามเวลาล่าสุด
        cursor = machine_collection.find().sort("created_at", -1)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ดึงคู่มือมาตรฐานจากข้อมูล Excel (สำหรับแสดงวิธีแก้ปัญหาในกล่องสีเขียว)
@app.get("/get-standard-guide/{machine_id}")
async def get_standard_guide(machine_id: str):
    try:
        # ค้นหาชื่อเครื่องจักรแบบไม่สนตัวพิมพ์เล็กใหญ่ (Case-insensitive)
        guide = await guide_collection.find_one({
            "machine": {"$regex": f"^{machine_id.strip()}$", "$options": "i"}
        })
        if guide:
            return {
                "status": "found",
                "solution": guide.get("solv", "ไม่ระบุวิธีแก้ไข"),
                "cause": guide.get("Cause & Positions to be checked", "ไม่ระบุสาเหตุ")
            }
        return {"status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# บันทึกข้อมูลอุบัติการณ์ใหม่
@app.post("/upload")
async def upload_incident(
    file: UploadFile = File(...),
    machine_id: str = Form(...),
    description: str = Form(None)
):
    try:
        # อัปโหลดรูปภาพไปยัง Cloudinary
        upload_result = cloudinary.uploader.upload(file.file)
        new_doc = {
            "machine_id": machine_id.strip().upper(),
            "description": description,
            "url": upload_result["secure_url"],
            "created_at": datetime.utcnow().isoformat()
        }
        await machine_collection.insert_one(new_doc)
        return {"status": "success", "url": upload_result["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ล้างฐานข้อมูลอุบัติการณ์ (ระวัง: ข้อมูลจะหายทั้งหมด)
@app.delete("/clear-database")
async def clear_database():
    await machine_collection.delete_many({})
    return {"message": "All records cleared successfully."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 MachineSync Pro API v3.5 Starting...")
    uvicorn.run(app, host="0.0.0.0", port=8000)