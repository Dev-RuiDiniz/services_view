from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico # Importa o modelo que vamos manipular
from typing import List

# A Camada de Serviço é uma classe (ou conjunto de funções) que orquestra
# as operações de negócio e o acesso ao banco de dados.

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio.
    """

    # O método recebe a sessão (db) injetada pela rota
    async def create_ordem_servico(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """
        Cria uma nova Ordem de Serviço no banco de dados.
        """
        # Cria a instância do modelo
        novo_os = OrdemServico(**os_data)
        
        # Adiciona à sessão e marca para ser commitado
        db.add(novo_os)
        await db.commit()
        await db.refresh(novo_os) # Atualiza a instância com o ID gerado (se não for UUID)
        
        return novo_os

    async def get_all_ordens_servico(self, db: AsyncSession) -> List[OrdemServico]:
        """
        Busca todas as Ordens de Serviço.
        """
        # Exemplo de consulta simples (usando SQLAlchemy 2.0 Style)
        # Note que a sessão (db) é usada aqui, e não criada.
        from sqlalchemy import select
        result = await db.execute(select(OrdemServico))
        return result.scalars().all()


# Exemplo de como você usaria essa classe na sua rota (routes/):
# @router.post("/")
# async def criar_os(os_data: Schema, db: AsyncSession = Depends(get_db)):
#     service = OrdemServicoService()
#     return await service.create_ordem_servico(db, os_data)