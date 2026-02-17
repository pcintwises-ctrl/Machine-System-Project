import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from typing import Optional

# 1. โหลดค่าจากไฟล์ .env
load_dotenv()

app = FastAPI()

# 2. ตั้งค่า CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. ตั้งค่า Cloudinary
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
    return {"message": "Machine Management API is running with Suggestion System!"}

# **NEW**: ดึงรายชื่อ Machine ID ทั้งหมด (เพื่อใช้ทำ Auto-suggestion)
@app.get("/get-machine-names")
async def get_machine_names():
    try:
        # ดึง machine_id ทั้งหมดแบบไม่ซ้ำกัน
        names = await machine_collection.distinct("machine_id")
        return names
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# **UPDATED**: ค้นหาแบบยืดหยุ่น (ใส่ช่องไหนก็ได้ หรือไม่ใส่เลย)
@app.get("/search-troubleshoot")
async def search_troubleshoot(machine_id: Optional[str] = None, issue: Optional[str] = None):
    try:
        query = {}
        # ใช้ $regex เพื่อให้ค้นหาแบบบางส่วนได้ (เช่น พิมพ์ 001 ก็เจอ machine-001)
        # options: "i" คือไม่สนตัวพิมพ์เล็ก-ใหญ่
        if machine_id:
            query["machine_id"] = {"$regex": machine_id, "$options": "i"}
        if issue:
            query["description"] = {"$regex": issue, "$options": "i"}
            
        machines = []
        cursor = machine_collection.find(query)
        async for document in cursor:
            document["_id"] = str(document["_id"])
            machines.append(document)
        return machines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_machine_data(
    file: UploadFile = File(...),
    description: str = Form(None),
    machine_id: str = Form(...)
):
    try:
        upload_result = cloudinary.uploader.upload(file.file, folder="machine_system")
        image_url = upload_result.get("secure_url")

        new_record = {
            "machine_id": machine_id,
            "description": description,
            "url": image_url,
            "public_id": upload_result.get("public_id"),
            "created_at": os.popen('date').read().strip()
        }
        await machine_collection.insert_one(new_record)
        return {"status": "Success", "message": f"Uploaded {machine_id}", "image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-all-machines")
async def get_all_machines():
    machines = []
    cursor = machine_collection.find()
    async for document in cursor:
        document["_id"] = str(document["_id"])
        machines.append(document)
    return machines

@app.get("/get-machine/{machine_id}")
async def get_machine(machine_id: str):
    machine = await machine_collection.find_one({"machine_id": machine_id})
    if machine:
        machine["_id"] = str(machine["_id"])
        return machine
    raise HTTPException(status_code=404, detail="Machine ID not found")

@app.delete("/clear-database")
async def clear_database():
    try:
        result = await machine_collection.delete_many({})
        return {"status": "Success", "message": f"Deleted {result.deleted_count} items"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)