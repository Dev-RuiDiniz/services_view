from fastapi import FastAPI, Request, Form, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from tinydb import TinyDB
from uuid import uuid4
from datetime import datetime
import os

app = FastAPI()

DB_PATH = "db.json"
db = TinyDB(DB_PATH)
table = db.table("ordens")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def serialize_os(os):
    return {
        "id": os.get("id"),
        "os": os.get("os"),
        "tipo": os.get("tipo"),
        "cliente": os.get("cliente"),
        "equipamento": os.get("equipamento"),
        "entrada": os.get("entrada"),
        "prazo_entrega": os.get("prazo_entrega"),
        "status": os.get("status"),
    }


@app.get("/")
async def index(request: Request):
    os_list = sorted(
        table.all(),
        key=lambda x: (x["tipo"] != "garantia", x["prazo_entrega"])
    )
    os_serialized = [serialize_os(os) for os in os_list]
    return templates.TemplateResponse("index.html", {"request": request, "ordens": os_serialized})


@app.get("/os/novo")
async def criar_os_form(request: Request):
    return templates.TemplateResponse("os_form.html", {"request": request})


@app.post("/os/novo")
async def criar_os(
    request: Request,
    os_num: str = Form(...),
    tipo: str = Form(...),
    cliente: str = Form(...),
    equipamento: str = Form(...),
    entrada: str = Form(...),
    prazo_entrega: str = Form(...),
    status: str = Form(...)
):
    nova_os = {
        "id": str(uuid4()),
        "os": os_num,
        "tipo": tipo,
        "cliente": cliente,
        "equipamento": equipamento,
        "entrada": entrada,
        "prazo_entrega": prazo_entrega,
        "status": status,
    }
    table.insert(nova_os)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
