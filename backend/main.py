import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from typing import Optional
from datetime import datetime

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

MONGO_DETAILS = os.getenv("MONGO_DETAILS")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.factory_db
machine_collection = database.get_collection("machine_data")

@app.get("/get-machine-names")
async def get_machine_names():
    names = await machine_collection.distinct("machine_id")
    return names

@app.get("/get-all-machines")
async def get_all_machines():
    machines = []
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
            "created_at": datetime.utcnow().isoformat() 
        }
        await machine_collection.insert_one(new_record)
        return {"status": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))