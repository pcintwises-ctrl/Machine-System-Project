import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from typing import Optional
from datetime import datetime

# 1. โหลดค่า Environment Variables
load_dotenv()

app = FastAPI()

# 2. ตั้งค่า CORS ให้ Frontend ติดต่อได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. กำหนดค่า Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# 4. เชื่อมต่อ MongoDB Atlas
MONGO_DETAILS = os.getenv("MONGO_DETAILS")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.factory_db
machine_collection = database.get_collection("machine_data")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"status": "online", "message": "MachineSync Pro API v2.5 Active"}

@app.get("/get-machine-names")
async def get_machine_names():
    try:
        # ดึงชื่อ Machine ID ทั้งหมดแบบไม่ซ้ำกันเพื่อทำ Auto-suggestion
        names = await machine_collection.distinct("machine_id")
        return names
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-all-machines")
async def get_all_machines():
    try:
        machines = []
        # เรียงลำดับตามวันที่จากใหม่ไปเก่า
        cursor = machine_collection.find().sort("created_at", -1)
        async for document in cursor:
            document["_id"] = str(document["_id"])
            machines.append(document)
        return machines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search-troubleshoot")
async def search_troubleshoot(machine_id: Optional[str] = None, issue: Optional[str] = None):
    try:
        query = {}
        if machine_id:
            query["machine_id"] = {"$regex": machine_id, "$options": "i"}
        if issue:
            query["description"] = {"$regex": issue, "$options": "i"}
            
        results = []
        cursor = machine_collection.find(query).sort("created_at", -1)
        async for document in cursor:
            document["_id"] = str(document["_id"])
            results.append(document)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_machine_data(
    file: UploadFile = File(...),
    description: str = Form(None),
    machine_id: str = Form(...)
):
    try:
        # อัปโหลดรูปภาพไปยัง Cloudinary
        upload_result = cloudinary.uploader.upload(file.file, folder="machine_system")
        image_url = upload_result.get("secure_url")

        # สร้างชุดข้อมูลใหม่พร้อม Timestamp แบบละเอียด
        new_record = {
            "machine_id": machine_id,
            "description": description,
            "url": image_url,
            "public_id": upload_result.get("public_id"),
            # บันทึกวันเดือนปีและเวลาปัจจุบัน (ISO 8601)
            "created_at": datetime.now().isoformat() 
        }
        
        # บันทึกลง MongoDB
        await machine_collection.insert_one(new_record)
        return {"status": "Success", "message": f"Asset {machine_id} registered at {new_record['created_at']}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear-database")
async def clear_database():
    try:
        result = await machine_collection.delete_many({})
        return {"status": "Success", "deleted_count": result.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # รันเซิร์ฟเวอร์ที่พอร์ต 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)