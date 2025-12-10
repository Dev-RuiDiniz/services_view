🛠️ Sistema de Gerenciamento de Ordens de Serviço (OS)
🌟 Visão Geral
Este projeto é um sistema de gerenciamento de Ordens de Serviço (OS) construído com FastAPI (para o backend API e rotas web), SQLAlchemy 2.0+ (modo Async) para interação com o banco de dados SQLite, e Jinja2 para o frontend.

O objetivo é fornecer uma interface robusta e moderna para:

Visualizar e filtrar a listagem de Ordens de Serviço.

Criar, editar e excluir Ordens de Serviço.

Exibir um Dashboard com KPIs (Key Performance Indicators) e gráficos de distribuição de status e tendências mensais, usando Altair/Vega-Lite para visualização de dados.

Utilizar um Service Layer para desacoplamento da lógica de negócio.

🏗️ Estrutura do Projeto
A estrutura segue o padrão comum em aplicações FastAPI que utilizam camadas de serviço e modelos de banco de dados:

services_view/
├── database/               # Configuração da conexão e setup do DB (db_setup.py)
├── models/                 # Definição dos modelos ORM do SQLAlchemy (os_model.py)
├── routers/                # Rotas (endpoints) da aplicação (os_routers.py)
├── services/               # Lógica de Negócio e CRUD (os_service.py)
├── static/                 # Arquivos estáticos (CSS, JS, Imagens)
│   └── main.css
├── templates/              # Arquivos HTML (Jinja2) para o Frontend
│   ├── dashboard.html
│   ├── editar_os.html
│   ├── index.html
│   └── nova_os.html
├── tests/                  # Testes de unidade e integração (pytest)
│   ├── test_integration.py
│   └── test_os_service.py
├── main.py                 # Ponto de entrada e configuração do FastAPI
├── db.sqlite               # Banco de dados SQLite gerado (ignorado pelo .gitignore)
├── requirements.txt        # Dependências do Python
└── README.md               # Documentação principal
⚙️ Como Instalar e Configurar o Ambiente
Siga os passos abaixo para preparar seu ambiente de desenvolvimento Python:

1. Criar e Ativar o Ambiente Virtual (venv)
Acesse o diretório raiz do projeto e crie o ambiente virtual:

Bash

# Cria o ambiente virtual
python -m venv venv

# Ativa o ambiente virtual (Windows PowerShell)
.\venv\Scripts\Activate

# Ativa o ambiente virtual (Linux/macOS ou Git Bash)
source venv/bin/activate
(O prompt do seu terminal deve mudar para (venv) indicando que o ambiente está ativo.)

2. Instalar as Dependências
Instale todas as bibliotecas necessárias listadas no requirements.txt:

Bash

pip install -r requirements.txt
As principais dependências do projeto são: fastapi, uvicorn[standard], sqlalchemy[asyncio], aiosqlite, jinja2, python-multipart, pytest, httpx, pandas, e altair.

▶️ Como Rodar a Aplicação
A aplicação utiliza o Uvicorn como servidor ASGI.

1. Inicialização
Certifique-se de que o ambiente virtual está ativo ((venv)) e execute:

Bash

uvicorn main:app --reload
main:app: Indica ao Uvicorn para procurar o objeto app no arquivo main.py.

--reload: Ativa o modo de recarga automática para desenvolvimento (a aplicação reinicia ao salvar mudanças no código).

2. Acessar a Aplicação
A aplicação estará acessível em:

Frontend (Dashboard/Listagem):

http://127.0.0.1:8000/os/
Documentação Interativa (Swagger UI - Gerada Automaticamente):

http://127.0.0.1:8000/docs
✅ Executando os Testes
O projeto utiliza o pytest para validação de código. Os testes utilizam uma sessão de banco de dados SQLite em memória (:memory:) que é populada com dados de teste, garantindo que os testes sejam rápidos e isolados do banco de dados de produção (db.sqlite).

Para rodar todos os testes de unidade (test_os_service.py) e de integração (test_integration.py):

Bash

pytest -v
NOTA: Todos os 10 testes de unidade e integração estão passando no momento, validando as funcionalidades CRUD, filtros, e o cálculo de KPIs.