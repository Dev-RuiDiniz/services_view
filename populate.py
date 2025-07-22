import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta

MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client.os_viewer
collection = db.ordens

dados = [
    {
        "cliente": "João Silva",
        "tipo": "garantia",
        "descricao": "Substituição da placa de controle",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=2)).isoformat(),
        "status": "pendente"
    },
    {
        "cliente": "Maria Souza",
        "tipo": "serviço",
        "descricao": "Reparo no motor principal",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=5)).isoformat(),
        "status": "pendente"
    },
    {
        "cliente": "Empresa XYZ",
        "tipo": "garantia",
        "descricao": "Garantia do inversor de frequência",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=1)).isoformat(),
        "status": "pendente"
    },
    {
        "cliente": "Carlos Mendes",
        "tipo": "serviço",
        "descricao": "Limpeza e calibração",
        "data_criacao": datetime.now().isoformat(),
        "prazo_entrega": (datetime.now() + timedelta(days=3)).isoformat(),
        "status": "pendente"
    }
]

async def popular_banco():
    await collection.delete_many({})
    await collection.insert_many(dados)
    print("Banco populado com sucesso!")

if __name__ == "__main__":
    asyncio.run(popular_banco())
