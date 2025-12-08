from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from uuid import UUID
import datetime
# Adicionando o HTTPException para indicar erro de objeto não encontrado (boa prática)
from fastapi import HTTPException 

class OrdemServicoService:
    # ... (Métodos CREATE, READ All e Auxiliares omitidos)

    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
        """
        Busca uma única Ordem de Serviço pelo seu ID (UUID) e retorna o objeto ORM puro.
        """
        query = select(OrdemServico).where(OrdemServico.id == os_id)
        result = await db.execute(query)
        return result.scalars().one_or_none()
        
    # ----------------------------------------------------
    # NOVO: Método UPDATE
    # ----------------------------------------------------
    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
        """
        Busca uma OS pelo ID, atualiza seus atributos e persiste as mudanças.

        Argumentos:
            db (AsyncSession): A sessão do banco de dados injetada.
            os_id (UUID): O ID da Ordem de Serviço a ser atualizada.
            os_data (dict): Dicionário contendo os dados a serem atualizados.
            
        Retorna:
            OrdemServico: A instância do objeto após a atualização.
        """
        # 1. Busca o objeto existente usando o método já implementado (READ by ID)
        os_existente = await self.get_os_by_id(db, os_id)
        
        # 2. Verifica se a OS foi encontrada
        if not os_existente:
            # Lançamos uma exceção que o FastAPI irá capturar e transformar em resposta HTTP 404
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        # 3. Atualiza os atributos do objeto com os novos dados
        # Iteramos sobre os dados fornecidos, garantindo que o ID não seja sobrescrito.
        # Note que os_data deve conter as chaves do modelo (ex: 'os_num', 'cliente').
        for key, value in os_data.items():
            # Evita tentar atualizar o ID, a data de criação ou a data de entrada 
            # se não estiver explicitamente permitido pela lógica de negócio.
            if key not in ['id', 'data_criacao', 'data_entrada'] and hasattr(os_existente, key):
                setattr(os_existente, key, value)
                
        # 4. Executa o commit assíncrono para persistir no banco.
        # O SQLAlchemy detecta automaticamente as mudanças no objeto 'os_existente'.
        await db.commit()
        
        # 5. Atualiza a instância para refletir quaisquer mudanças automáticas do banco (ex: triggers)
        await db.refresh(os_existente)
        
        return os_existente