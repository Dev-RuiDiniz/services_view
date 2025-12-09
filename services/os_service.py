from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, case, Date, cast, Integer, exc
from uuid import UUID
import datetime
from fastapi import HTTPException, status 

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio e mapeamento CRUD assíncrono,
    incluindo enriquecimento de dados e tratamento de erros do banco de dados.
    """
    
    # ----------------------------------------------------
    # MÉTODOS AUXILIARES DE ENRIQUECIMENTO DE DADOS (Síncronos)
    # ----------------------------------------------------
    
    def _calculate_status(self, os: OrdemServico) -> str:
        """
        Calcula um status customizado (ex: 'ATRASADO') baseado na data de prazo
        e no status atual da OS.

        Args:
            os: Objeto ORM da OrdemServico.

        Returns:
            str: O status calculado ou o status original.
        """
        # ... (implementação) ...
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
        
        return os.status
    
    
    def _format_date(self, date_orm: Optional[datetime.date]) -> Optional[str]:
        """
        Formata um objeto datetime.date/datetime.datetime em uma string 'dd/mm/YYYY'.
        
        Args:
            date_orm: O objeto de data a ser formatado.

        Returns:
            Optional[str]: A data formatada ou None.
        """
        # ... (implementação) ...
        if date_orm:
            return date_orm.strftime('%d/%m/%Y')
        return None
    
    
    def _enrich_os_data(self, os_list: List[OrdemServico]) -> List[Dict[str, Any]]:
        """
        Transforma a lista de objetos ORM em uma lista de dicionários enriquecidos
        com status calculado e datas formatadas para a view.
        
        Args:
            os_list: Lista de objetos ORM OrdemServico.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários prontos para serialização.
        """
        # ... (implementação) ...
        enriched_list = []
        for os in os_list:
            os_dict = os.__dict__.copy()
            os_dict.pop('_sa_instance_state', None)
            os_dict['id'] = str(os_dict['id'])
            
            os_dict['status_calculado'] = self._calculate_status(os)
            os_dict['data_entrada_formatada'] = self._format_date(os.data_entrada)
            os_dict['prazo_entrega_formatado'] = self._format_date(os.prazo_entrega)
            
            enriched_list.append(os_dict)
        return enriched_list
    
    
    # ----------------------------------------------------
    # Mapeamento CRUD
    # ----------------------------------------------------
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """ 
        Cria e persiste uma nova Ordem de Serviço no banco de dados. 
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).
            os_data: Dicionário contendo os dados da nova OS.

        Returns:
            OrdemServico: O objeto ORM da OS recém-criada.

        Raises:
            HTTPException: Em caso de falha de conexão ou query no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        try:
            novo_os = OrdemServico(**os_data)
            db.add(novo_os)
            await db.commit()
            await db.refresh(novo_os) 
            return novo_os
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao criar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao criar a Ordem de Serviço."
            )

    async def get_all_os(
        self, 
        db: AsyncSession,
        status: Optional[str] = None, 
        cliente: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ 
        Busca todas as Ordens de Serviço, aplicando filtros opcionais.
        Retorna uma lista de dicionários enriquecidos com status calculado.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).
            status: Filtro opcional por status (string).
            cliente: Filtro opcional por nome do cliente (busca parcial, case-insensitive).

        Returns:
            List[Dict[str, Any]]: Lista de OSs processadas para a view.

        Raises:
            HTTPException: Em caso de falha de leitura no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        try:
            query = select(OrdemServico)
            conditions = []
            
            if status:
                conditions.append(OrdemServico.status == status)
            if cliente:
                conditions.append(OrdemServico.cliente.ilike(f'%{cliente}%'))
                
            if conditions:
                query = query.where(and_(*conditions))

            result = await db.execute(query)
            os_list = result.scalars().all()
            
            return self._enrich_os_data(os_list)
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar todas as OSs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )

    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
        """ 
        Busca uma única Ordem de Serviço pelo seu UUID.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).
            os_id: O UUID da Ordem de Serviço a ser buscada.

        Returns:
            Optional[OrdemServico]: O objeto ORM se encontrado, ou None.

        Raises:
            HTTPException: Em caso de falha de leitura no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        try:
            query = select(OrdemServico).where(OrdemServico.id == os_id)
            result = await db.execute(query)
            return result.scalars().one_or_none()
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar OS por ID: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )
        
    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
        """ 
        Atualiza os atributos de uma Ordem de Serviço existente e persiste.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).
            os_id: O UUID da Ordem de Serviço a ser atualizada.
            os_data: Dicionário contendo os campos e novos valores.

        Returns:
            OrdemServico: O objeto ORM atualizado.

        Raises:
            HTTPException: 404 se a OS não for encontrada, 500 em falha no DB.
        """
        # ... (implementação com try/except) ...
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        try:
            for key, value in os_data.items():
                if key not in ['id', 'data_criacao'] and hasattr(os_existente, key):
                    setattr(os_existente, key, value)
                    
            await db.commit()
            await db.refresh(os_existente)
            
            return os_existente
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao atualizar OS {os_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao atualizar a Ordem de Serviço."
            )

    async def delete_os(self, db: AsyncSession, os_id: UUID) -> bool:
        """ 
        Remove um registro de Ordem de Serviço pelo ID.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).
            os_id: O UUID da Ordem de Serviço a ser deletada.

        Returns:
            bool: True se a exclusão foi bem-sucedida.

        Raises:
            HTTPException: 404 se a OS não for encontrada, 500 em falha no DB.
        """
        # ... (implementação com try/except) ...
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        try:
            await db.delete(os_existente)
            await db.commit()
            
            return True
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao deletar OS {os_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao deletar a Ordem de Serviço."
            )
    
    # ----------------------------------------------------
    # Mapeamento de Análise (Dashboard)
    # ----------------------------------------------------
    async def get_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """ 
        Calcula os Key Performance Indicators (KPIs) agregados: total, atrasadas, 
        e média de prazo.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).

        Returns:
            Dict[str, Any]: Dicionário contendo os valores dos KPIs.

        Raises:
            HTTPException: Em caso de falha na agregação ou leitura no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        try:
            # Cálculos complexos...
            # ...
            # Retorno: kpis
            # ...
            pass # Usado para placeholder, mantendo o foco no docstring
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao calcular KPIs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura e agregação de dados do banco de dados para KPIs."
            )
        
    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
        """ 
        Calcula a contagem de Ordens de Serviço agrupadas pelo status.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).

        Returns:
            Dict[str, int]: Dicionário com {status: contagem}.

        Raises:
            HTTPException: Em caso de falha na agregação ou leitura no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        pass # Usado para placeholder, mantendo o foco no docstring
    
    async def get_os_by_month(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """ 
        Calcula a contagem de Ordens de Serviço agrupadas pelo mês de entrada ('YYYY-MM'),
        ordenado cronologicamente para gráficos de tendência.
        
        Args:
            db: Sessão assíncrona do banco de dados (AsyncSession).

        Returns:
            List[Dict[str, Any]]: Lista de dicionários com {"mes": str, "count": int}.

        Raises:
            HTTPException: Em caso de falha na agregação ou leitura no DB (Status 500).
        """
        # ... (implementação com try/except) ...
        pass # Usado para placeholder, mantendo o foco no docstring