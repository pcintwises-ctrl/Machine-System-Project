from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from bson import ObjectId
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime
import uvicorn

load_dotenv()
app = FastAPI()

# เปิด CORS เพื่อให้หน้าเว็บคุยกับ API ได้ (ทั้งจากเครื่องตัวเองและเครื่องคนอื่นใน LAN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# เชื่อมต่อฐานข้อมูล MongoDB
client = AsyncIOMotorClient(os.getenv("MONGO_DETAILS"))
db = client.factory_db
machine_collection = db.machine_data
guide_collection = db.troubleshooting_guide

# ตั้งค่า Cloudinary (สำหรับอัปโหลดรูป)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ==========================================
# 📌 Model สำหรับรับข้อมูลจากหน้าเว็บล่าสุด
# ==========================================
class GuideModel(BaseModel):
    machine: str
    model: str
    line: str
    process: str
    problem: str
    cause: str
    solution: str

# ==========================================
# 📌 ส่วนที่ 1: API ดั้งเดิมของคุณ (อัปโหลดรูป & ดึงประวัติ)
# ==========================================
@app.get("/get-all-machines")
async def get_all_machines():
    try:
        cursor = machine_collection.find().sort("created_at", -1)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-standard-guide/{machine_id}")
async def get_standard_guide(machine_id: str):
    try:
        guide = await guide_collection.find_one({
            "machine": {"$regex": f"^{machine_id.strip()}$", "$options": "i"}
        })
        if guide:
            # รองรับทั้งชื่อฟิลด์จาก Excel เดิม และฟิลด์ใหม่ที่เราเพิ่งสร้าง
            return {
                "status": "found",
                "solution": guide.get("solution", guide.get("solv", "ไม่ระบุวิธีแก้ไข")),
                "cause": guide.get("cause", guide.get("Cause & Positions to be checked", "ไม่ระบุสาเหตุ"))
            }
        return {"status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-machine-issues/{machine_id}")
async def get_machine_issues(machine_id: str):
    try:
        issues = await machine_collection.distinct(
            "description", 
            {"machine_id": {"$regex": f"^{machine_id.strip()}$", "$options": "i"}}
        )
        return [issue for issue in issues if issue]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_incident(file: UploadFile = File(...), machine_id: str = Form(...), description: str = Form(None)):
    try:
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

@app.delete("/clear-database")
async def clear_database():
    await machine_collection.delete_many({})
    return {"message": "All incident records cleared."}

# ==========================================
# 📌 ส่วนที่ 2: API ใหม่สำหรับหน้า Database (เพิ่ม/ลด/แก้ไข Master Data)
# ==========================================
@app.get("/api/guides")
async def get_all_guides():
    try:
        cursor = guide_collection.find().sort("_id", -1)
        results = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id")) # เปลี่ยน _id เป็น id ให้ฝั่งเว็บใช้ง่ายๆ
            results.append(doc)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guides")
async def add_guide(guide: GuideModel):
    try:
        new_guide = guide.dict()
        result = await guide_collection.insert_one(new_guide)
        return {"status": "success", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/guides/{guide_id}")
async def update_guide(guide_id: str, guide: GuideModel):
    try:
        updated_data = guide.dict()
        result = await guide_collection.update_one(
            {"_id": ObjectId(guide_id)}, 
            {"$set": updated_data}
        )
        if result.modified_count == 1:
            return {"status": "success", "message": "Updated successfully"}
        return {"status": "failed", "message": "Not found or no changes"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/guides/{guide_id}")
async def delete_guide(guide_id: str):
    try:
        result = await guide_collection.delete_one({"_id": ObjectId(guide_id)})
        if result.deleted_count == 1:
            return {"status": "success"}
        return {"status": "failed", "message": "Not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # รันบนพอร์ต 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)