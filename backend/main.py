import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# 1. โหลดค่าจากไฟล์ .env
load_dotenv()

app = FastAPI()

# 2. ตั้งค่า CORS เพื่อให้ Frontend (Static Site) ติดต่อได้จากทุกที่
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. ตั้งค่า Cloudinary ด้วยค่าจาก Environment Variables
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
    """เช็คสถานะการทำงานของ API"""
    return {"message": "Machine Management API is running with Cloudinary!"}

@app.post("/upload")
async def upload_machine_data(
    file: UploadFile = File(...),
    description: str = Form(None),
    machine_id: str = Form(...)
):
    """ฟังก์ชันอัปโหลดรูปขึ้น Cloudinary และบันทึกข้อมูลลง MongoDB"""
    try:
        # A. อัปโหลดไฟล์ภาพตรงไปยัง Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="machine_system"
        )
        
        # B. ดึง URL ที่ปลอดภัย (HTTPS) มาใช้งาน
        image_url = upload_result.get("secure_url")

        # C. สร้างก้อนข้อมูลเพื่อบันทึกลง MongoDB
        new_record = {
            "machine_id": machine_id,
            "description": description,
            "url": image_url,  # เก็บ URL จาก Cloudinary แทนที่การเก็บไฟล์ในเครื่อง
            "public_id": upload_result.get("public_id"), # สำหรับใช้อ้างอิงในอนาคต
            "created_at": os.popen('date').read().strip()
        }
        
        await machine_collection.insert_one(new_record)
        
        return {
            "status": "Success",
            "message": f"Successfully uploaded {machine_id} to Cloudinary and Database",
            "image_url": image_url
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-all-machines")
async def get_all_machines():
    """ดึงรายการเครื่องจักรทั้งหมดจากฐานข้อมูล"""
    machines = []
    cursor = machine_collection.find()
    async for document in cursor:
        document["_id"] = str(document["_id"])
        machines.append(document)
    return machines

@app.get("/get-machine/{machine_id}")
async def get_machine(machine_id: str):
    """ค้นหาเครื่องจักรรายตัวด้วย Machine ID"""
    machine = await machine_collection.find_one({"machine_id": machine_id})
    if machine:
        machine["_id"] = str(machine["_id"])
        return machine
    raise HTTPException(status_code=404, detail="Machine ID not found")

# เพิ่ม Endpoint สำหรับลบข้อมูลทั้งหมด
@app.delete("/clear-database")
async def clear_database():
    try:
        # ลบข้อมูลทั้งหมดใน collection
        result = await machine_collection.delete_many({})
        return {"status": "Success", "message": f"ลบข้อมูลทั้งหมดเรียบร้อยแล้ว ({result.deleted_count} รายการ)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ส่วนสำหรับรัน Server
if __name__ == "__main__":
    import uvicorn
    # รับ Port จากระบบ (Render จะกำหนดมาให้) หรือใช้ 8000 ถ้าทดสอบในเครื่อง
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)