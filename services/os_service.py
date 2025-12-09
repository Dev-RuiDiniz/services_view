from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, case, Date, cast, Integer
from uuid import UUID
import datetime
from fastapi import HTTPException 

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
    # Mapeamento READ All com Filtros
    # ----------------------------------------------------
    async def get_all_os(
        self, 
        db: AsyncSession,
        # NOVOS PARÂMETROS OPCIONAIS
        status: Optional[str] = None, 
        cliente: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ 
        Busca todas as Ordens de Serviço, aplicando filtros dinâmicos de status e cliente. 
        Retorna a lista de dicionários enriquecidos.
        """
        
        # 1. Inicia a query básica
        query = select(OrdemServico)
        
        # Lista para armazenar as condições de filtro
        conditions = []
        
        # 2. Constrói as condições dinamicamente
        
        if status:
            conditions.append(OrdemServico.status == status)

        if cliente:
            # Filtra por cliente, usando ILIKE para busca case-insensitive e parcial
            conditions.append(OrdemServico.cliente.ilike(f'%{cliente}%'))
            
        # 3. Aplica as condições à query
        if conditions:
            # Usa 'and_' para combinar todas as condições com lógica AND
            query = query.where(and_(*conditions))

        # 4. Executa a query
        result = await db.execute(query)
        os_list = result.scalars().all()
        
        # 5. Aplica a lógica de enriquecimento
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
    
    # ----------------------------------------------------
    # Mapeamento de Análise (KPIs)
    # ----------------------------------------------------
    async def get_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        # ... (implementação do get_kpis, já corrigida)
        
        # 1. Definição das Expressões Agregadas
        total_os = func.count(OrdemServico.id).label('total_os')
        
        atrasadas_count = func.sum(
            case(
                (
                    and_(
                        OrdemServico.prazo_entrega < datetime.date.today(),
                        OrdemServico.status.notin_(['Concluída', 'Cancelada'])
                    ),
                    1 # Se a condição for verdadeira, conta 1
                ),
                else_=0 # Senão, conta 0
            )
        ).label('atrasadas_count')
        
        media_prazo_dias = func.avg(
            cast(OrdemServico.prazo_entrega - OrdemServico.data_entrada, Integer) 
        ).label('media_prazo_dias')

        # 2. Constrói e Executa a Query
        query = select(total_os, atrasadas_count, media_prazo_dias)
        
        result = await db.execute(query)
        
        kpis_row = result.first() 

        if kpis_row is None:
            return {
                "total_os": 0,
                "atrasadas_count": 0,
                "media_prazo_dias": None
            }

        # 3. Formata e Retorna o Dicionário de KPIs
        kpis_dict = kpis_row._asdict()

        kpis = {
            "total_os": int(kpis_dict.get('total_os', 0) or 0),
            "atrasadas_count": int(kpis_dict.get('atrasadas_count', 0) or 0),
            "media_prazo_dias": round(float(kpis_dict.get('media_prazo_dias')), 2) 
                                  if kpis_dict.get('media_prazo_dias') is not None else None
        }
        
        return kpis
    
    # ----------------------------------------------------
    # NOVO: Mapeamento de Análise - Distribuição de Status
    # ----------------------------------------------------
    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
        """
        Retorna a contagem de Ordens de Serviço agrupadas pelo status.
        Ex: {"Pendente": 15, "Concluída": 10, "Aguardando Peça": 5}
        """
        # Seleciona o status e a contagem de registros agrupados por status
        query = select(
            OrdemServico.status,
            func.count(OrdemServico.id).label('count')
        ).group_by(OrdemServico.status)

        result = await db.execute(query)
        
        # Converte a lista de objetos Row em um dicionário {status: count}
        # Acessa os resultados pelo índice ou nome do label (status e count)
        status_distribution = {
            row.status: row.count for row in result.all()
        }
        
        return status_distribution
    
    # ----------------------------------------------------
    # NOVO: Mapeamento de Análise - Tendência Mensal
    # ----------------------------------------------------
    async def get_os_by_month(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Retorna a contagem de Ordens de Serviço agrupadas pelo mês e ano da data de entrada.
        O formato da chave de mês é 'YYYY-MM'.
        """
        # Formata a data de entrada para 'YYYY-MM' e a etiqueta como 'mes'
        # Em SQLite, func.strftime é usado para formatação de data.
        # Se você usar PostgreSQL, usaria func.to_char(OrdemServico.data_entrada, 'YYYY-MM').
        
        month_label = func.strftime('%Y-%m', OrdemServico.data_entrada).label('mes')
        
        query = select(
            month_label,
            func.count(OrdemServico.id).label('count')
        ).group_by(month_label).order_by(month_label) # Ordena pela data para o gráfico de tendência

        result = await db.execute(query)
        
        # Converte os resultados em uma lista de dicionários
        # Ex: [{"mes": "2025-11", "count": 15}, ...]
        os_by_month = [
            {"mes": row.mes, "count": row.count} 
            for row in result.all()
        ]
        
        return os_by_month