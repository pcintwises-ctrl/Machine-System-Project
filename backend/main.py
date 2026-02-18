from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime
import uvicorn

load_dotenv()
app = FastAPI()

# เปิด CORS เพื่อให้หน้าเว็บ Render คุยกับ API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# เชื่อมต่อฐานข้อมูล
client = AsyncIOMotorClient(os.getenv("MONGO_DETAILS"))
db = client.factory_db
machine_collection = db.machine_data
guide_collection = db.troubleshooting_guide

# ตั้งค่า Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

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
        # ค้นหาวิธีแก้ปัญหาจากคู่มือ Excel แบบไม่สนตัวพิมพ์เล็กใหญ่
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

if __name__ == "__main__":
 
    uvicorn.run(app, host="0.0.0.0", port=8000)