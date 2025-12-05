from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional
from sqlalchemy import select
from uuid import UUID

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio.
    """
    
    # Método CREATE (Implementado anteriormente)
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """
        Cria uma nova Ordem de Serviço no banco de dados.
        """
        novo_os = OrdemServico(**os_data)
        db.add(novo_os)
        await db.commit()
        await db.refresh(novo_os) 
        return novo_os

    # ----------------------------------------------------
    # NOVO/ATUALIZADO: Método READ
    # ----------------------------------------------------
    async def get_all_os(self, db: AsyncSession) -> List[OrdemServico]:
        """
        Busca todas as Ordens de Serviço no banco de dados de forma assíncrona.

        Argumentos:
            db (AsyncSession): A sessão do banco de dados injetada pela rota.
            
        Retorna:
            List[OrdemServico]: Uma lista de objetos modelo OrdemServico.
        """
        # 1. Cria a instrução SELECT (SQLAlchemy 2.0 Style)
        # Equivalente a: SELECT * FROM ordens_servico;
        query = select(OrdemServico)
        
        # 2. Executa a instrução de forma assíncrona
        result = await db.execute(query)
        
        # 3. Mapeia o resultado para uma lista de objetos modelo
        # scalars() transforma os objetos 'Row' em objetos Python 'OrdemServico'
        return result.scalars().all()
    
    # ----------------------------------------------------
    # NOVO: Método READ by ID
    # ----------------------------------------------------
    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
        """
        Busca uma única Ordem de Serviço pelo seu ID (UUID).

        Argumentos:
            db (AsyncSession): A sessão do banco de dados.
            os_id (UUID): O ID único (UUID) da Ordem de Serviço.
            
        Retorna:
            Optional[OrdemServico]: O objeto OrdemServico se encontrado, ou None.
        """
        # 1. Cria a instrução SELECT com filtro WHERE
        query = select(OrdemServico).where(OrdemServico.id == os_id)
        
        # 2. Executa a instrução de forma assíncrona
        result = await db.execute(query)
        
        # 3. Mapeia o resultado para um único objeto ou None
        # O .one_or_none() garante que a consulta retorne no máximo um item, 
        # ideal para busca por chave primária.
        return result.scalars().one_or_none()