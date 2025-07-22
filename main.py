from fastapi import FastAPI, Request, Form, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from tinydb import TinyDB, Query
from uuid import uuid4
from datetime import datetime

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
    os_list = table.all()

    # Atualiza status dinâmico para atrasado se for serviço e passou do prazo
    for os in os_list:
        if os["tipo"] == "serviço":
            prazo = datetime.strptime(os["prazo_entrega"], "%Y-%m-%d")
            hoje = datetime.today()
            if os["status"] == "pendente" and hoje > prazo:
                os["status"] = "atrasado"

    os_list = sorted(
        os_list,
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


@app.get("/os/{os_id}/editar")
async def editar_os_form(request: Request, os_id: str):
    query = Query()
    os_item = table.get(query.id == os_id)
    if not os_item:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("os_edit_form.html", {"request": request, "os": os_item})


@app.post("/os/{os_id}/editar")
async def editar_os(
    request: Request,
    os_id: str,
    os_num: str = Form(...),
    tipo: str = Form(...),
    cliente: str = Form(...),
    equipamento: str = Form(...),
    entrada: str = Form(...),
    prazo_entrega: str = Form(...),
    status: str = Form(...)
):
    query = Query()
    table.update({
        "os": os_num,
        "tipo": tipo,
        "cliente": cliente,
        "equipamento": equipamento,
        "entrada": entrada,
        "prazo_entrega": prazo_entrega,
        "status": status,
    }, query.id == os_id)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/os/{os_id}/deletar")
async def deletar_os(os_id: str):
    query = Query()
    table.remove(query.id == os_id)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
