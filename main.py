from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
import os

app = FastAPI()

# Config MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.os_viewer
collection = db.ordens

# Config Template e Static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Conversor BSON -> JSON
def serialize_os(os):
    os["id"] = str(os["_id"])
    os.pop("_id")
    return os

@app.get("/")
async def index(request: Request):
    os_cursor = collection.find().sort([
        ("tipo", 1),  # 'garantia' vem antes de 'serviço'
        ("prazo_entrega", 1)
    ])
    os_list = [serialize_os(os) async for os in os_cursor]
    return templates.TemplateResponse("index.html", {"request": request, "ordens": os_list})
