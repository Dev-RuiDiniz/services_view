from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from uuid import UUID
import datetime
from fastapi import HTTPException # Importação necessária para tratamento de erros

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio e mapeamento CRUD assíncrono.
    """
    
    # ----------------------------------------------------
    # MÉTODOS AUXILIARES DE ENRIQUECIMENTO DE DADOS (Síncronos)
    # ----------------------------------------------------
    
    def _calculate_status(self, os: OrdemServico) -> str:
        """
        Calcula e retorna um status customizado baseado na data de prazo.
        """
        # Se a OS já está concluída ou cancelada, não precisa calcular.
        if os.status in ["Concluída", "Cancelada"]:
            return os.status
        
        if os.prazo_entrega is not None:
            hoje = datetime.date.today()
            diferenca = (os.prazo_entrega - hoje).days

            if diferenca < 0:
                return "ATRASADO"
            elif diferenca <= 3:
                return "PRÓXIMO DO PRAZO"
        
        return os.status # Retorna o status original se nenhuma regra se aplicar
    
    
    def _format_date(self, date_orm: Optional[datetime.date]) -> Optional[str]:
        """
        Formata um objeto datetime.date/datetime.datetime em uma string amigável.
        """
        if date_orm:
            # Formato brasileiro: dd/mm/YYYY
            return date_orm.strftime('%d/%m/%Y')
        return None
    
    
    def _enrich_os_data(self, os_list: List[OrdemServico]) -> List[Dict[str, Any]]:
        """
        Transforma a lista de objetos ORM em uma lista de dicionários enriquecidos
        com status calculado e datas formatadas.
        """
        enriched_list = []
        for os in os_list:
            # Cria um dicionário a partir dos atributos do objeto ORM
            os_dict = os.__dict__.copy()
            
            # Limpeza e conversão de tipos para serialização (JSON ou View)
            os_dict.pop('_sa_instance_state', None) # Remove metadados do SQLAlchemy
            os_dict['id'] = str(os_dict['id']) # Converte UUID para string
            
            # Adiciona a lógica de enriquecimento
            os_dict['status_calculado'] = self._calculate_status(os)
            os_dict['data_entrada_formatada'] = self._format_date(os.data_entrada)
            os_dict['prazo_entrega_formatado'] = self._format_date(os.prazo_entrega)
            
            enriched_list.append(os_dict)
        return enriched_list
    
    
    # ----------------------------------------------------
    # Mapeamento CREATE
    # ----------------------------------------------------
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """ Cria uma nova Ordem de Serviço. """
        novo_os = OrdemServico(**os_data)
        db.add(novo_os)
        await db.commit()
        await db.refresh(novo_os) 
        return novo_os

    # ----------------------------------------------------
    # Mapeamento READ All
    # ----------------------------------------------------
    async def get_all_os(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """ Busca todas as Ordens de Serviço e retorna-as enriquecidas. """
        query = select(OrdemServico)
        result = await db.execute(query)
        os_list = result.scalars().all()
        # Aplica a lógica de enriquecimento
        return self._enrich_os_data(os_list)
    
    # ----------------------------------------------------
    # Mapeamento READ by ID
    # ----------------------------------------------------
    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
        """ Busca uma única Ordem de Serviço pelo seu ID. """
        query = select(OrdemServico).where(OrdemServico.id == os_id)
        result = await db.execute(query)
        # Retorna o objeto ORM puro ou None
        return result.scalars().one_or_none()
        
    # ----------------------------------------------------
    # Mapeamento UPDATE
    # ----------------------------------------------------
    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
        """ Busca a OS, atualiza seus atributos e persiste as mudanças. """
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        for key, value in os_data.items():
            # Atualiza apenas os atributos permitidos
            if key not in ['id', 'data_criacao'] and hasattr(os_existente, key):
                setattr(os_existente, key, value)
                
        await db.commit()
        await db.refresh(os_existente)
        
        return os_existente

    # ----------------------------------------------------
    # Mapeamento DELETE
    # ----------------------------------------------------
    async def delete_os(self, db: AsyncSession, os_id: UUID) -> bool:
        """ Busca uma OS pelo ID e a remove do banco de dados. """
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        await db.delete(os_existente)
        await db.commit()
        
        return True