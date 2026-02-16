from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import shutil
import os

app = FastAPI()

# 1. เชื่อมต่อ MongoDB
MONGO_DETAILS = "mongodb+srv://phonlawat_api:kPOIUadGVRbjOM59@cluster0.bkogsh0.mongodb.net/?appName=Cluster0"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.factory_db
image_collection = database.get_collection("machine_data")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

# ฟังก์ชันช่วยแปลงข้อมูล MongoDB เป็น JSON
def machine_helper(machine) -> dict:
    return {
        "id": str(machine["_id"]),
        "machine_id": machine["machine_id"],
        "filename": machine["filename"],
        "description": machine["description"],
        "url": machine["url"],
    }

@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...), 
    description: str = Form(...),
    machine_id: str = Form(...)
):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # ปรับ URL ให้เรียกผ่าน Port ที่เปิดไว้ (8000)
    image_data = {
        "machine_id": machine_id,
        "filename": file.filename,
        "description": description,
        "url": f"http://localhost:8000/images/{file.filename}" 
    }
    await image_collection.insert_one(image_data)
    return {"status": "Success", "message": "บันทึกข้อมูลเครื่องเรียบร้อย!"}

# --- เพิ่มส่วนนี้: สำหรับดึงข้อมูลทั้งหมดไปแสดงในแท็บ Database ---
@app.get("/get-all-machines")
async def get_all_machines():
    machines = []
    async for machine in image_collection.find():
        machines.append(machine_helper(machine))
    return machines

@app.get("/get-machine/{m_id}")
async def get_machine(m_id: str):
    data = await image_collection.find_one({"machine_id": m_id})
    if data:
        return machine_helper(data)
    raise HTTPException(status_code=404, detail="ไม่พบหมายเลขเครื่องนี้")

if __name__ == "__main__":
    import uvicorn
    # สำคัญ: host="0.0.0.0" เพื่อให้ Docker เชื่อมต่อได้
    uvicorn.run(app, host="0.0.0.0", port=8000)