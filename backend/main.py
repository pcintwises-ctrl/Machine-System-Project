import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from typing import Optional
from datetime import datetime

# 1. โหลด Environment
load_dotenv()

app = FastAPI()

# 2. CORS เพื่อให้หน้าเว็บติดต่อได้
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

# 4. เชื่อมต่อ MongoDB
MONGO_DETAILS = os.getenv("MONGO_DETAILS")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.factory_db
machine_collection = database.get_collection("machine_data")

@app.get("/")
async def root():
    return {"message": "MachineSync Pro API Active"}

@app.get("/get-machine-names")
async def get_machine_names():
    try:
        names = await machine_collection.distinct("machine_id")
        return names
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-all-machines")
async def get_all_machines():
    machines = []
    # เรียงลำดับจากอดีตไปปัจจุบันเพื่อใช้ในกราฟ
    cursor = machine_collection.find().sort("created_at", 1)
    async for document in cursor:
        document["_id"] = str(document["_id"])
        machines.append(document)
    return machines

@app.post("/upload")
async def upload_machine_data(
    file: UploadFile = File(...),
    description: str = Form(None),
    machine_id: str = Form(...)
):
    try:
        upload_result = cloudinary.uploader.upload(file.file, folder="machine_system")
        
        new_record = {
            "machine_id": machine_id,
            "description": description,
            "url": upload_result.get("secure_url"),
            "public_id": upload_result.get("public_id"),
            # บันทึกเวลาแบบ ISO เพื่อให้ JS หน้าบ้านดึงไปทำแกน X ได้
            "created_at": datetime.utcnow().isoformat() 
        }
        await machine_collection.insert_one(new_record)
        return {"status": "Success", "message": f"Asset {machine_id} logged."}
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

@app.delete("/clear-database")
async def clear_database():
    try:
        result = await machine_collection.delete_many({})
        return {"status": "Success", "count": result.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)