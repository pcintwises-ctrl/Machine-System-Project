from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# เปิด CORS ให้หน้าเว็บคุยกับ Backend ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# เชื่อมต่อ MongoDB Atlas 
client = AsyncIOMotorClient(os.getenv("MONGO_DETAILS"))
db = client.factory_db
# ใช้ Collection เดิมที่มีข้อมูล Excel 255 รายการอยู่
guide_collection = db.troubleshooting_guide 

# โครงสร้างข้อมูลที่หน้าเว็บใหม่ต้องการรับ-ส่ง
class GuideModel(BaseModel):
    machine: str
    model: str = "-"
    line: str = "-"
    process: str = "-"
    problem: str = "-"
    cause: str
    solution: str

# 1. API: ดึงข้อมูลทั้งหมด (และแปลงชื่อคอลัมน์ Excel เก่าให้เข้ากับ UI ใหม่)
@app.get("/api/guides")
async def get_guides():
    guides = []
    cursor = guide_collection.find({})
    async for doc in cursor:
        guides.append({
            "id": str(doc["_id"]),
            "machine": doc.get("machine", "Unknown"),
            "model": doc.get("model", "-"),
            "line": doc.get("line", "-"),
            "process": doc.get("process", "-"),
            "problem": doc.get("problem", "General Error"), 
            # แปลงชื่อคอลัมน์เก่าจาก Excel ให้แสดงผลใน UI ใหม่ได้
            "cause": doc.get("Cause & Positions to be checked", doc.get("cause", "-")),
            "solution": doc.get("solv", doc.get("solution", "-"))
        })
    # เรียงลำดับจากใหม่ไปเก่า (อิงจาก ObjectID)
    return guides[::-1]

# 2. API: เพิ่มข้อมูลใหม่จากหน้า Add Mode
@app.post("/api/guides")
async def create_guide(guide: GuideModel):
    new_guide = guide.dict()
    # บันทึกเผื่อชื่อคอลัมน์เก่าด้วย เพื่อให้ค้นหาแบบเดิมยังทำงานได้
    new_guide["Cause & Positions to be checked"] = guide.cause
    new_guide["solv"] = guide.solution
    
    result = await guide_collection.insert_one(new_guide)
    return {"id": str(result.inserted_id)}

# 3. API: อัปเดตข้อมูล (Edit Mode)
@app.put("/api/guides/{guide_id}")
async def update_guide(guide_id: str, guide: GuideModel):
    update_dict = {
        "machine": guide.machine,
        "model": guide.model,
        "line": guide.line,
        "process": guide.process,
        "problem": guide.problem,
        "cause": guide.cause,
        "solution": guide.solution,
        "Cause & Positions to be checked": guide.cause,
        "solv": guide.solution
    }
    
    result = await guide_collection.update_one(
        {"_id": ObjectId(guide_id)}, 
        {"$set": update_dict}
    )
    if result.matched_count == 1 or result.modified_count == 1:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="ไม่พบข้อมูลที่ต้องการแก้ไข")

# 4. API: ลบข้อมูล
@app.delete("/api/guides/{guide_id}")
async def delete_guide(guide_id: str):
    result = await guide_collection.delete_one({"_id": ObjectId(guide_id)})
    if result.deleted_count == 1:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="ไม่พบข้อมูลที่ต้องการลบ")

if __name__ == "__main__":
    import uvicorn
    # ให้ระบบเช็กว่า Render สั่งให้ใช้ Port ไหน ถ้าไม่มีให้ใช้ 8000 เป็นค่าเริ่มต้น
    port = int(os.environ.get("PORT", 8000)) 
    print(f"🚀 MTF SUP Backend API is running on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)