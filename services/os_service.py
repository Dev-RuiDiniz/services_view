from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from uuid import UUID
import datetime

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio.
    """
    
    # ----------------------------------------------------
    # LÓGICA DE ENRIQUECIMENTO DE DADOS (Métodos Auxiliares Síncronos)
    # ----------------------------------------------------
    def _calculate_status(self, os: OrdemServico) -> str:
        """
        Calcula e retorna um status customizado baseado na data de prazo.
        
        Args:
            os: Objeto OrdemServico.
            
        Returns:
            Status da OS (ex: 'Atrasado', 'Próximo', 'Pendente').
        """
        # Se a OS já está concluída ou cancelada, não precisa calcular.
        if os.status in ["Concluída", "Cancelada"]:
            return os.status
        
        # Lógica de negócio: verifica o prazo
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
            # Garante que o objeto é um datetime.date (ou compatível)
            return date_orm.strftime('%d/%m/%Y')
        return None
    
    
    def _enrich_os_data(self, os_list: List[OrdemServico]) -> List[Dict[str, Any]]:
        """
        Transforma a lista de objetos ORM em uma lista de dicionários enriquecidos.
        """
        enriched_list = []
        for os in os_list:
            # Converte o objeto ORM para um dicionário base
            os_dict = os.__dict__.copy()
            
            # Remove a chave de estado do SQLAlchemy (não é necessário para o usuário)
            os_dict.pop('_sa_instance_state', None)
            
            # Adiciona o status calculado
            os_dict['status_calculado'] = self._calculate_status(os)
            
            # Formata as datas
            os_dict['data_entrada_formatada'] = self._format_date(os.data_entrada)
            os_dict['prazo_entrega_formatado'] = self._format_date(os.prazo_entrega)
            
            # Converte UUID para string
            os_dict['id'] = str(os_dict['id'])
            
            enriched_list.append(os_dict)
        return enriched_list

    # ----------------------------------------------------
    # NOVO/ATUALIZADO: Método READ
    # ----------------------------------------------------
    async def get_all_os(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Busca todas as Ordens de Serviço e as retorna enriquecidas com status e datas formatadas.
        """
        from sqlalchemy import select
        query = select(OrdemServico)
        
        result = await db.execute(query)
        os_list = result.scalars().all()
        
        # CHAMADA DE ENRIQUECIMENTO:
        return self._enrich_os_data(os_list)
    
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