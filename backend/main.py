import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from datetime import datetime
from typing import Optional

# 1. โหลดค่า Environment Variables
load_dotenv()

app = FastAPI()

# 2. ตั้งค่า CORS ให้ Frontend สามารถเข้าถึงได้จากทุกที่
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. กำหนดค่า Cloudinary สำหรับเก็บรูปภาพ
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# 4. เชื่อมต่อ MongoDB Atlas
client = AsyncIOMotorClient(os.getenv("MONGO_DETAILS"))
database = client.factory_db
machine_collection = database.get_collection("machine_data")
# คอลเลกชันสำหรับเก็บคู่มือมาตรฐานจาก Excel
guide_collection = database.get_collection("troubleshooting_guide")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"status": "online", "message": "MachineSync Pro API v3.0 Active"}

# ดึงประวัติอุบัติการณ์ทั้งหมด
@app.get("/get-all-machines")
async def get_all_machines():
    try:
        machines = []
        # เรียงลำดับตามวันที่จากใหม่ไปเก่า
        cursor = machine_collection.find().sort("created_at", -1)
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            machines.append(doc)
        return machines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ค้นหาวิธีแก้ปัญหามาตรฐานจากข้อมูล Excel
@app.get("/get-standard-guide/{machine_id}")
async def get_standard_guide(machine_id: str):
    try:
        # ค้นหาโดยไม่สนใจพิมพ์เล็กพิมพ์ใหญ่
        guide = await guide_collection.find_one({
            "machine": {"$regex": f"^{machine_id}$", "$options": "i"}
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

# ลงทะเบียนอุบัติการณ์ใหม่พร้อมรูปภาพและข้อมูล MLP
@app.post("/upload")
async def upload_machine_data(
    file: UploadFile = File(...),
    machine_id: str = Form(...),
    model: str = Form("N/A"),
    line: str = Form("N/A"),
    process: str = Form("N/A"),
    description: str = Form(None)
):
    try:
        # อัปโหลดรูปภาพไปยัง Cloudinary
        res = cloudinary.uploader.upload(file.file, folder="machine_system")
        
        new_record = {
            "machine_id": machine_id.strip().upper(),
            "model": model.strip(),
            "line": line.strip(),
            "process": process.strip(),
            "description": description,
            "url": res.get("secure_url"),
            # บันทึกเวลาแบบละเอียดระดับวินาที
            "created_at": datetime.now().isoformat()
        }
        await machine_collection.insert_one(new_record)
        return {"status": "Success", "message": f"Asset {machine_id} registered successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ลบข้อมูลรายรายการโดยใช้ ID
@app.delete("/delete-record/{record_id}")
async def delete_record(record_id: str):
    try:
        await machine_collection.delete_one({"_id": ObjectId(record_id)})
        return {"status": "Deleted"}
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

# ล้างฐานข้อมูลอุบัติการณ์ทั้งหมด
@app.delete("/clear-database")
async def clear_database():
    try:
        await machine_collection.delete_many({})
        return {"status": "Database Cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # รันเซิร์ฟเวอร์ที่พอร์ต 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)