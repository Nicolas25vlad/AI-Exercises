# Assessor.AI

## Instalação

Use Python 3.11 ou mais recente e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure o `.env` com `GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL` e `MONGODB_URI`. O PostgreSQL e o MongoDB precisam estar acessíveis antes de usar as ferramentas e as sessões.

## Execução

Na raiz do projeto:

```powershell
uvicorn app.main:app --reload
```

Abra `http://localhost:8000/` ou `http://localhost:8000/docs`. O endpoint de saúde é `GET /health`.

## Limite atual

As ferramentas de agenda não foram criadas porque o projeto original não contém um módulo de eventos para migrar. O agente de agenda permanece disponível, mas sem tools.
