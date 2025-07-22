from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from uuid import uuid4
from tinydb import TinyDB, Query
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db = TinyDB("db.json")
table = db.table("ordens")

def calcular_status(os):
    hoje = datetime.now().date()
    prazo = datetime.strptime(os["prazo_entrega"], "%Y-%m-%d").date()
    if os["status"] != "finalizada":
        if os["tipo"] == "serviço" and prazo < hoje:
            return "atrasado"
        return "pendente"
    return "finalizada"

def formatar_data(data_iso):
    return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    ordens = table.all()
    for os in ordens:
        os["status"] = calcular_status(os)
        os["prazo_formatado"] = formatar_data(os["prazo_entrega"])
        os["entrada_formatada"] = formatar_data(os["entrada"])
    return templates.TemplateResponse("index.html", {"request": request, "ordens": ordens})

@app.get("/os/novo", response_class=HTMLResponse)
def nova_os_form(request: Request):
    return templates.TemplateResponse("nova_os.html", {"request": request})

@app.post("/os/novo")
def criar_os(
    os_num: str = Form(...),
    tipo: str = Form(...),
    cliente: str = Form(...),
    equipamento: str = Form(...),
    entrada: str = Form(...),
    prazo_entrega: str = Form(...),
    status: str = Form(...)
):
    nova = {
        "id": str(uuid4()),
        "os": os_num,
        "tipo": tipo,
        "cliente": cliente,
        "equipamento": equipamento,
        "entrada": entrada,
        "prazo_entrega": prazo_entrega,
        "status": status
    }
    table.insert(nova)
    return RedirectResponse(url="/", status_code=303)

@app.get("/os/{os_id}/editar", response_class=HTMLResponse)
def editar_os_form(request: Request, os_id: str):
    os_encontrada = next((o for o in table.all() if o["id"] == os_id), None)
    return templates.TemplateResponse("editar_os.html", {"request": request, "os": os_encontrada})

@app.post("/os/{os_id}/editar")
def editar_os(
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
    OS = Query()
    table.update({
        "os": os_num,
        "tipo": tipo,
        "cliente": cliente,
        "equipamento": equipamento,
        "entrada": entrada,
        "prazo_entrega": prazo_entrega,
        "status": status
    }, OS.id == os_id)
    return RedirectResponse(url="/", status_code=303)

@app.post("/os/{os_id}/deletar")
def deletar_os(os_id: str):
    OS = Query()
    table.remove(OS.id == os_id)
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
