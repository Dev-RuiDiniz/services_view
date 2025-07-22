from tinydb import TinyDB
from uuid import uuid4
from datetime import datetime, timedelta

DB_PATH = "db.json"
db = TinyDB(DB_PATH)
table = db.table("ordens")

# Limpa os dados existentes
table.truncate()

# Dados de exemplo
dados = [
    {
        "id": str(uuid4()),
        "cliente": "João Silva",
        "tipo": "garantia",
        "descricao": "Substituição da placa de controle",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=2)).isoformat(),
        "status": "pendente"
    },
    {
        "id": str(uuid4()),
        "cliente": "Maria Souza",
        "tipo": "serviço",
        "descricao": "Reparo no motor principal",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=5)).isoformat(),
        "status": "pendente"
    },
    {
        "id": str(uuid4()),
        "cliente": "Empresa XYZ",
        "tipo": "garantia",
        "descricao": "Garantia do inversor de frequência",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=1)).isoformat(),
        "status": "pendente"
    },
    {
        "id": str(uuid4()),
        "cliente": "Carlos Mendes",
        "tipo": "serviço",
        "descricao": "Limpeza e calibração",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=3)).isoformat(),
        "status": "pendente"
    }
]

# Insere no banco
table.insert_multiple(dados)
print("Banco populado com sucesso!")
