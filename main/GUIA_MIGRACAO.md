# Guia de Migração — do script local para uma API com FastAPI

Este documento descreve **a estrutura de pastas** do projeto migrado e **o que cada
arquivo precisa conter**. Ele é um guia de organização: ninguém precisa ter
exatamente os mesmos arquivos que o colega, mas todos precisam ter os mesmos
**conteúdos** distribuídos nos mesmos lugares.

---

## 1. Por que migrar? A ideia por trás da reorganização

Hoje o projeto é um **script**: você roda `python main.py`, ele abre um
`while True` com `input()`, você conversa no terminal e, quando o programa fecha,
acabou. Um usuário por vez, uma máquina só, tudo dentro de um arquivo.

Migrar para FastAPI transforma esse script em um **serviço**. A diferença central:


| No script                          | No serviço                                                               |
| ---------------------------------- | ------------------------------------------------------------------------ |
| O `while True` controla a conversa | O **navegador** controla: cada mensagem é uma requisição HTTP            |
| `input()` lê do teclado            | O corpo (JSON) da requisição traz a pergunta                             |
| `print()` escreve no terminal      | A resposta HTTP devolve o texto                                          |
| `session_id = "id_usuario"` fixo   | O `session_id` chega em cada requisição — vários usuários ao mesmo tempo |
| Tudo em um arquivo                 | Responsabilidades separadas em camadas                                   |


O ganho não é só "ficar bonito". É que **cada pedaço passa a ter um motivo único
para mudar**. Se amanhã trocarmos o Gemini por outro modelo, mexemos em um arquivo.
Se trocarmos o FAISS pelo Qdrant, mexemos em outro. Se mudarmos a cara da tela,
nenhum arquivo Python é tocado. Isso se chama **separação de responsabilidades**, e é
o princípio que organiza a árvore abaixo.

### As quatro camadas

O projeto migrado se divide em quatro camadas, de fora para dentro:

1. **Apresentação** (`frontend/`) — o que o usuário vê. Não sabe nada de LangGraph.
2. **API** (`app/routes/`, `app/schemas.py`) — traduz HTTP em chamadas Python. Não
  sabe *como* a resposta é gerada, só sabe pedir.
3. **Domínio** (`app/graph.py`, `app/agents.py`, `app/prompts.py`, `app/guardrail.py`) —
  a inteligência do assessor. Não sabe que existe HTTP.
4. **Infraestrutura** (`app/tools/`, `app/memory.py`, `app/llms.py`, `app/config.py`) —
  conversa com o mundo externo: Postgres, MongoDB, APIs de LLM, arquivos.

Regra de ouro: **as camadas de fora chamam as de dentro, nunca o contrário.**
Uma rota pode importar o grafo; o grafo nunca importa uma rota.

---



## 2. A estrutura completa

```
migracao_fastAPI/
├── .env                     ← chaves e senhas (NUNCA versionar no Git)
├── requirements.txt
├── README.md
│
├── app/                     ← todo o código Python do servidor
│   ├── main.py              ← ponto de entrada do FastAPI
│   ├── config.py            ← único lugar que lê o .env
│   ├── schemas.py           ← formato dos dados que entram e saem da API
│   ├── llms.py              ← criação dos modelos de linguagem
│   ├── prompts.py           ← textos que definem o comportamento dos agentes
│   ├── guardrail.py         ← proteções de entrada e de saída
│   ├── memory.py            ← persistência das conversas no MongoDB
│   ├── agents.py            ← montagem dos 5 agentes
│   ├── graph.py             ← o fluxo (LangGraph) que liga tudo
│   │
│   ├── routes/              ← os endpoints HTTP
│   │   ├── chat.py
│   │   └── sessions.py
│   │
│   └── tools/               ← ferramentas que os agentes podem usar
│       ├── db.py
│       ├── financeiro.py
│       ├── agenda.py
│       └── faq.py
│
├── data/                    ← arquivos de dados usados pelo sistema
│   └── FAQ_assessor_v1.1.pdf
│
└── frontend/                ← a interface no navegador
    ├── index.html
    ├── style.css
    └── app.js
```

**16 arquivos, 5 pastas.** Nenhum `__init__.py`: a partir do Python 3.3 as pastas
funcionam como pacotes sem ele (*namespace packages*). A consequência prática é que
os imports sempre usam o caminho completo, como `from app.tools.financeiro import TOOLS`.

---



## 3. De onde vem cada coisa

Tabela de referência da migração. À esquerda, o que você já tem; à direita, para
onde vai.


| Arquivo atual           | Destino                                                          | Observação                      |
| ----------------------- | ---------------------------------------------------------------- | ------------------------------- |
| `main.py`               | quebrado em 5 arquivos                                           | ver seção 5                     |
| `pg_tools_all.py`       | `app/tools/financeiro.py`                                        | quase cópia direta              |
| `event_tools.py`        | `app/tools/agenda.py`                                            | quase cópia direta              |
| `faq_tools.py`          | `app/tools/faq.py`                                               | precisa de ajuste (seção 6.4)   |
| `prompts.py`            | `app/prompts.py`                                                 | cópia direta                    |
| `guardrail.py`          | `app/guardrail.py`                                               | cópia direta                    |
| `memory_mongodb.py`     | `app/memory.py`                                                  | cópia direta                    |
| `FAQ_assessor_v1.1.pdf` | `data/FAQ_assessor_v1.1.pdf`                                     | muda de caminho                 |
| `.env`                  | `.env` na raiz                                                   | falta acrescentar `MONGODB_URI` |
| —                       | `app/main.py`, `schemas.py`, `config.py`, `routes/`, `frontend/` | arquivos novos                  |


Os arquivos que **não** vão para o projeto novo: todas as outras `aula*.py`,
`main.py`, `memory.py`, `memory_old.py`, `guardrail_completo.py`, `pg_tools.py`,
`tool_mongodb.py`, os `.txt` de rascunho e os `.zip`.

---



## 4. As pastas, uma a uma



### `migracao_fastAPI/` (raiz)

A raiz guarda apenas o que descreve o projeto como um todo — nunca código de
funcionalidade.

- `.env` — todas as chaves e strings de conexão. Precisa conter:
`GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL` (Postgres) e `MONGODB_URI`.
Atenção: hoje o `MONGODB_URI` **não está** no `.env`; o código usa
`mongodb://localhost:27017` como valor padrão. Torne-o explícito.
- `requirements.txt` — a lista de bibliotecas com suas versões. É o que permite
outra pessoa rodar seu projeto. Precisa incluir, no mínimo: `fastapi`, `uvicorn`,
`python-dotenv`, `langchain`, `langgraph`, `langchain-google-genai`, `langchain-groq`,
`langchain-community`, `langchain-text-splitters`, `faiss-cpu`, `pypdf`, `psycopg2-binary`,
`pymongo`, `pydantic`.
- `README.md` — como instalar, configurar o `.env` e rodar. Escreva pensando em
alguém que nunca viu o projeto.



### `app/` — o servidor

Todo o Python que roda no servidor. É onde ficam as camadas 2, 3 e 4.

A pasta é **plana** de propósito: `guardrail.py`, `prompts.py` e `memory.py` são um
arquivo cada, e transformá-los em subpastas só criaria um nível a mais para navegar,
sem ganho nenhum. Viram subpasta apenas as duas coisas que naturalmente crescem:
`routes/` (mais endpoints) e `tools/` (mais ferramentas).

### `app/routes/` — a fronteira HTTP

Um arquivo por **grupo de endpoints relacionados**. Rotas são a camada mais fina do
sistema: elas recebem o pedido, chamam quem sabe fazer o trabalho e devolvem o
resultado. Se uma rota está ficando comprida, é sinal de que ela está fazendo
trabalho que pertence a `graph.py` ou a `memory.py`.

### `app/tools/` — as ferramentas dos agentes

"Tool" é uma função que o LLM pode decidir chamar sozinho. Um arquivo por **domínio**
de ferramenta, e a docstring de cada tool é o que o modelo lê para decidir se ela
serve — ou seja, docstring aqui não é comentário, é parte do funcionamento.

### `data/` — arquivos de dados

Conteúdo que o sistema lê, mas que não é código. Hoje contém só o PDF do FAQ.
Separar dados de código evita que alguém apague um por engano ao mexer no outro, e
deixa claro que trocar o PDF não exige alterar Python nenhum.

### `frontend/` — a interface

HTML, CSS e JavaScript servidos pelo FastAPI como arquivos estáticos. Está fora de
`app/` por um motivo: se um dia o front virar um projeto separado (React, Vue), basta
mover essa pasta inteira, sem tocar em nenhuma linha de Python.

---



## 5. O que cada arquivo precisa ter



### `app/config.py`

**Responsabilidade:** ser o **único** lugar do projeto que lê o `.env`.

Hoje o `load_dotenv()` aparece repetido em cinco arquivos diferentes. Isso significa
que, para saber de quais variáveis o projeto depende, é preciso abrir cinco arquivos.
Centralizar resolve isso.

Precisa ter:

- um `load_dotenv()` — o único do projeto;
- as variáveis lidas em constantes: `GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`,
`MONGODB_URI`;
- os caminhos de arquivos, montados de forma absoluta a partir da raiz do projeto —
por exemplo, `BASE_DIR` apontando para `migracao_fastAPI/` e `FAQ_PDF_PATH = BASE_DIR / "data" / "FAQ_assessor_v1.1.pdf"`.
Isso é importante: caminho relativo (`"FAQ_assessor_v1.1.pdf"`) quebra dependendo
da pasta de onde você roda o servidor;
- opcionalmente, uma verificação que avisa na hora do boot se alguma chave está
faltando — erro claro no início é melhor do que erro estranho no meio da conversa.

Não pode ter: nada de LangChain, nada de banco, nada de FastAPI. Só leitura de configuração.

### `app/llms.py`

**Responsabilidade:** criar os objetos de modelo de linguagem, uma vez só.

Precisa ter os quatro modelos que hoje estão no topo do `aula11_memoriaDB.py`:

- `llm_gemini` — `gemini-2.5-flash`, temperatura 0.7;
- `llm_groq` — `openai/gpt-oss-120b`, temperatura 0.7;
- `llm_especialista` — `llm_gemini.with_fallbacks([llm_groq])`, usado pelos agentes que
precisam raciocinar melhor;
- `llm_rapido` — `llama-3.3-70b-versatile`, temperatura 0.0, usado onde a resposta
precisa ser determinística (roteador, orquestrador, FAQ).

As chaves vêm de `app.config`, não de `os.getenv()` direto.

Por que um arquivo só para isso: os modelos são criados **uma vez** quando o servidor
sobe e reaproveitados em todas as requisições. Se cada arquivo criasse o seu, você
teria conexões duplicadas e configurações divergentes.

### `app/prompts.py`

**Responsabilidade:** guardar os textos que definem o comportamento de cada agente.

É cópia direta do `prompts.py` atual. Precisa continuar exportando as cinco
constantes usadas pelo grafo: `ROUTER_PROMPT_COMPLETO`, `FINANCEIRO_PROMPT_COMPLETO`,
`AGENDA_PROMPT_COMPLETO`, `ORQUESTRADOR_PROMPT_COMPLETO` e `FAQ_PROMPT_COMPLETO`.

Fica isolado porque prompt é a parte que mais muda durante os testes, e ninguém
deveria precisar entender o grafo para ajustar uma frase de instrução.

### `app/guardrail.py`

**Responsabilidade:** proteger a entrada e a saída do sistema.

É cópia direta do `guardrail.py` atual. Precisa continuar oferecendo:

- `anonimizar_entrada(texto)` → devolve o texto com CPF, e-mail etc. substituídos por
tokens, mais o mapa de tokens. **O LLM nunca vê o dado real**;
- `guardrail_entrada(texto)` → decide se a mensagem deve ser bloqueada;
- `guardrail_saida(resposta, mapa_pii)` → revisa a resposta antes de devolvê-la.

Único ajuste: passar a importar a chave do Groq de `app.config`.

### `app/memory.py`

**Responsabilidade:** persistir as conversas no MongoDB.

É cópia direta do `memory_mongodb.py` atual. Precisa continuar oferecendo
`iniciar_sessao`, `salvar_mensagem`, `encerrar_sessao`, `recuperar_historico` e
`recuperar_mensagens`.

**Ponto de atenção conceitual.** O arquivo atual guarda as sessões abertas num
dicionário em memória (`_sessoes_ativas`). Num script isso funciona, porque só existe
um usuário. Num servidor web, esse dicionário é o mesmo para todo mundo e **se perde
quando o servidor reinicia** — uma sessão iniciada antes do restart não consegue mais
salvar mensagens. Reflita sobre isso ao migrar: a solução é buscar a sessão ativa
direto no Mongo em vez de confiar no dicionário.

### `app/tools/db.py`

**Responsabilidade:** abrir conexões com o Postgres.

Hoje a mesma função de conexão está duplicada em `pg_tools_all.py` e `event_tools.py`.
Duplicação é o tipo de coisa que só dá problema depois: você corrige um e esquece o
outro. Este arquivo precisa ter uma única função `get_conn()`, que lê a `DATABASE_URL`
de `app.config` e devolve a conexão. Os outros dois arquivos de tools passam a importá-la.

### `app/tools/financeiro.py`

**Responsabilidade:** as ferramentas de dinheiro.

Vem do `pg_tools_all.py`. Precisa ter as cinco tools — `add_transaction`,
`query_transactions`, `total_balance`, `daily_balance`, `update_transaction` — e a
lista `TOOLS` que as agrupa. A função de conexão local sai, dando lugar ao
`get_conn()` de `db.py`.

### `app/tools/agenda.py`

**Responsabilidade:** as ferramentas de calendário.

Vem do `event_tools.py`. Precisa ter a tool `add_event` e a lista `TOOLS_AGENDA`.
Mesma troca da conexão pelo `get_conn()`.

### `app/tools/faq.py`

**Responsabilidade:** buscar trechos relevantes no PDF do FAQ.

Vem do `faq_tools.py`, mas é o arquivo que mais precisa de ajuste. No código atual, a
tool `faq_retriever` faz **tudo** a cada pergunta: divide o PDF em pedaços, gera os
embeddings e constrói o índice FAISS do zero. Num script isso custava alguns segundos
por resposta. Num servidor, com várias pessoas perguntando ao mesmo tempo, vira um
gargalo sério — e uma conta cara de API de embeddings.

O que este arquivo precisa ter:

- o carregamento do PDF e a construção do índice **separados** da tool, em uma função
própria (por exemplo `_get_retriever()`), executada uma vez só;
- a tool `faq_retriever(question)` fazendo apenas a busca por similaridade sobre o
índice já pronto;
- o caminho do PDF vindo de `app.config`, não de um caminho relativo.

Essa separação tem um segundo motivo: o plano é trocar o FAISS pelo **Qdrant** mais
adiante. Se a criação do índice estiver isolada numa função, essa migração mexe em um
bloco de código; se estiver espalhada dentro da tool, mexe no arquivo inteiro. As
variáveis `QDRANT_URL` e `QDRANT_API_KEY` já estão previstas no `.env`.

### `app/agents.py`

**Responsabilidade:** montar os cinco agentes.

Um agente é a combinação de três coisas: **um modelo + um conjunto de tools + um
prompt de sistema**. Este arquivo faz essas combinações e nada mais:


| Agente             | Modelo             | Tools             | Prompt                         |
| ------------------ | ------------------ | ----------------- | ------------------------------ |
| `router_app`       | `llm_rapido`       | —                 | `ROUTER_PROMPT_COMPLETO`       |
| `financeiro_app`   | `llm_especialista` | `TOOLS`           | `FINANCEIRO_PROMPT_COMPLETO`   |
| `agenda_app`       | `llm_especialista` | `TOOLS_AGENDA`    | `AGENDA_PROMPT_COMPLETO`       |
| `orquestrador_app` | `llm_rapido`       | —                 | `ORQUESTRADOR_PROMPT_COMPLETO` |
| `faq_app`          | `llm_rapido`       | `[faq_retriever]` | `FAQ_PROMPT_COMPLETO`          |


Separar isto de `graph.py` permite trocar o modelo de um agente, ou dar uma tool nova
a ele, sem abrir o arquivo do fluxo.

### `app/graph.py`

**Responsabilidade:** o fluxo. É o coração do projeto.

Precisa ter, na ordem:

- a classe `Estado` (herda de `MessagesState`), com `agentes_chamados`, `rota` e
`mapa_pii`;
- os **nós** que são funções Python: `no_guardrail_entrada`, `no_roteador`,
`no_orquestrador`, `no_guardrail_saida`;
- as **funções de decisão**: `decidir_especialista` e `decidir_pos_guardrail_entrada`;
- a montagem do `StateGraph`: `add_node`, `set_entry_point`, `add_conditional_edges`,
`add_edge`;
- o `compile(checkpointer=...)` produzindo o `fluxo_agentes`;
- uma função de alto nível, tipo `executar_fluxo(pergunta, session_id)`, que é o que a
rota vai chamar.

O que **não** pode estar aqui: o `while True`, o `input()`, o `print()` e o
`session_id` fixo do final do `aula11_memoriaDB.py`. Toda essa parte é substituída
pelo HTTP.

**Ponto de atenção conceitual.** O `MemorySaver()` guarda o histórico do LangGraph na
memória RAM do processo. Ele funciona, mas some inteiro quando o servidor reinicia.
Como agora existem vários usuários, vale entender bem o papel do `thread_id`: é ele
que separa a conversa de um usuário da do outro. Cada requisição precisa passar o
`session_id` correto no `config={"configurable": {"thread_id": ...}}`, senão as
conversas se misturam.

### `app/schemas.py`

**Responsabilidade:** definir o **contrato** da API — o formato exato do que entra e
do que sai.

São classes Pydantic. O FastAPI as usa para três coisas de uma vez: validar o que
chega (rejeitando automaticamente um pedido malformado), converter a resposta em JSON
e gerar a documentação interativa em `/docs`.

Precisa ter, no mínimo:

- `ChatRequest` — o que o navegador envia: `session_id: str` e `pergunta: str`;
- `ChatResponse` — o que a API devolve: `resposta: str` (e, se quiser, os
`agentes_chamados` para depurar);
- `SessionResponse` — retorno ao criar ou encerrar uma sessão (`session_id`, `resumo`).

Sem esse arquivo, você aceitaria qualquer JSON e só descobriria o problema quando o
código quebrasse lá dentro.

### `app/routes/chat.py`

**Responsabilidade:** o endpoint da conversa.

Precisa ter um `APIRouter` e o endpoint `POST /chat`, que:

1. recebe um `ChatRequest`;
2. chama a função do `graph.py` passando pergunta e `session_id`;
3. devolve um `ChatResponse`.

É praticamente a função `executar_fluxo_assessor` do script atual, só que recebendo os
dados por HTTP em vez de por `input()`. Se este arquivo passar de umas poucas dezenas
de linhas, algo que pertence ao domínio vazou para a camada de API.

### `app/routes/sessions.py`

**Responsabilidade:** o ciclo de vida das sessões.

No script, `iniciar_sessao()` era chamada uma vez antes do loop e `encerrar_sessao()`
quando o usuário digitava "sair". Na web, esses dois momentos viram endpoints:

- `POST /sessions` — cria a sessão e devolve o `session_id`;
- `DELETE /sessions/{session_id}` — encerra, gera o resumo via LLM e o devolve;
- `GET /sessions/{session_id}/historico` — opcional, expõe o `recuperar_historico`.



### `app/main.py`

**Responsabilidade:** ser o ponto de entrada — o arquivo que o `uvicorn` executa.

Precisa ter:

- a criação da aplicação: `app = FastAPI(title=..., version=...)`;
- o **CORS**, liberando o navegador a chamar a API;
- o registro dos routers: `app.include_router(chat.router)` e o de `sessions`;
- a montagem do frontend como arquivos estáticos, para que abrir a raiz do servidor já
mostre a tela;
- opcionalmente, um endpoint `/health` que só responde "ok" — útil para verificar
rapidamente se o servidor subiu.

Precisa ser **curto**. `main.py` monta e conecta as peças; ele não implementa nenhuma.

### `frontend/index.html`, `style.css`, `app.js`

**Responsabilidade:** a tela de conversa.

- `index.html` — a estrutura: área do histórico, campo de texto, botão de enviar e
um botão de encerrar a conversa.
- `style.css` — a aparência. Separado do HTML pelo mesmo motivo de sempre: mudar
cor não deveria exigir mexer na estrutura.
- `app.js` — o comportamento: guardar o `session_id` que veio do `POST /sessions`,
enviar cada mensagem para o `POST /chat` via `fetch`, exibir a resposta na tela e
chamar o `DELETE` ao encerrar.

O JavaScript aqui ocupa exatamente o lugar que o `while True` ocupava no script: é ele
que mantém a conversa viva agora.

---



## 6. Regras que valem para o projeto inteiro

1. **Um** `load_dotenv()` **só**, em `config.py`. Nenhum outro arquivo lê o `.env` direto.
2. **Imports com caminho completo**, sempre a partir de `app`:
  `from app.tools.financeiro import TOOLS`. Como não usamos `__init__.py`, não há
   atalhos de reexportação.
3. **O servidor sobe da raiz** do projeto: estando em `migracao_fastAPI/`, rode
  `uvicorn app.main:app --reload`. Rodar de dentro de `app/` quebra os imports.
4. **Caminhos de arquivo são absolutos**, montados a partir de `BASE_DIR` em
  `config.py`. Caminho relativo depende de onde você rodou o comando.
5. **As dependências apontam para dentro.** `routes` importa `graph`; `graph` importa
  `agents`; `agents` importa `tools`, `llms` e `prompts`. Nunca o contrário. Se você
   se pegar importando uma rota dentro de `graph.py`, alguma responsabilidade está no
   lugar errado.
6. **O** `.env` **nunca vai para o Git.** Se você versionar o projeto, crie um `.gitignore`
  com `.env` e `__pycache__/`.

---



## 7. Como saber que a migração funcionou

Verifique, nesta ordem:

1. `uvicorn app.main:app --reload` sobe sem erro de import.
2. `http://localhost:8000/docs` abre e mostra os endpoints `/chat` e `/sessions`.
3. Um `POST /sessions` devolve um `session_id`, e o documento aparece no MongoDB.
4. Um `POST /chat` com uma pergunta de gasto ("gastei 50 reais no mercado") registra a
  transação no Postgres e devolve resposta coerente.
5. Uma pergunta de agenda cai no agente de agenda; uma pergunta sobre o sistema cai no
  FAQ. Ou seja: o roteador continua roteando.
6. Enviar um CPF na mensagem: a resposta **não** pode exibi-lo de volta — sinal de que
  o guardrail sobreviveu à migração.
7. Duas sessões diferentes, abertas ao mesmo tempo, não enxergam o histórico uma da
  outra.
8. `DELETE /sessions/{id}` devolve o resumo gerado pelo LLM.

Se os oito passos funcionam, o comportamento do script foi preservado — e agora ele
roda como serviço.