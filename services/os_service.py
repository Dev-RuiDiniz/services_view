from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico # Importa o modelo que vamos manipular
from typing import List, Optional

# A Camada de Serviço é uma classe que orquestra as operações de negócio.

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio.
    Esta classe não cria a sessão do DB, mas a utiliza.
    """
    
    # ----------------------------------------------------
    # O método create_os usa a sessão (db) que será injetada
    # ----------------------------------------------------
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """
        Cria uma nova Ordem de Serviço no banco de dados.

        Argumentos:
            db (AsyncSession): A sessão do banco de dados injetada pela rota.
            os_data (dict): Dicionário contendo os dados da nova OS.
            
        Retorna:
            OrdemServico: A instância do objeto após ser persistido e atualizado (refresh).
        """
        
        # 1. Instancia o modelo com os dados recebidos.
        # Os campos default (id, data_entrada, data_criacao, status) são preenchidos
        # automaticamente se não estiverem em os_data.
        novo_os = OrdemServico(**os_data)
        
        # 2. Adiciona o objeto à sessão.
        db.add(novo_os)
        
        # 3. Executa o commit assíncrono para persistir no banco.
        # Note o 'await' e a chamada direta ao db.commit().
        await db.commit()
        
        # 4. Atualiza a instância para garantir que o objeto Python tenha
        # os valores gerados pelo banco (como o ID e timestamps).
        await db.refresh(novo_os) 
        
        return novo_os

    # Mantendo o método de busca para referência futura
    async def get_all_ordens_servico(self, db: AsyncSession) -> List[OrdemServico]:
        """
        Busca todas as Ordens de Serviço.
        """
        from sqlalchemy import select
        result = await db.execute(select(OrdemServico))
        # O .scalars().all() é o padrão do SQLAlchemy 2.0 para obter os objetos modelo
        return result.scalars().all()