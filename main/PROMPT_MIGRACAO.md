Você é um agente de IA trabalhando dentro do projeto de um aluno. Sua tarefa é
**exclusivamente reorganizar arquivos que já existem** para dentro de uma nova
estrutura de pastas. Você **não vai escrever código novo**, não vai corrigir nada e
não vai completar nada que esteja faltando. Isso é trabalho do aluno, em uma etapa
posterior.

Leia todas as regras antes de começar.

---

## O projeto

É um assistente de IA construído com LangChain e LangGraph. Ele tem um arquivo
principal, que monta um fluxo de agentes, e vários módulos auxiliares: ferramentas de
banco de dados financeiro, ferramentas de agenda, busca em um PDF de FAQ, prompts,
guardrails de segurança e memória em MongoDB. Hoje está tudo solto numa pasta só, e o
objetivo é migrar para uma organização em camadas, preparando o projeto para virar uma
API com FastAPI.

**Atenção: os nomes dos arquivos são diferentes em cada projeto.** Um aluno pode ter
`pdf_ferramentas.py` onde outro tem `faq_tools.py`; `bd_financeiro.py` onde outro tem
`pg_tools_all.py`. **Nunca decida pelo nome do arquivo.** Abra cada arquivo, leia o
conteúdo e classifique pelo que ele faz.

---

## Regras invioláveis

1. **Não crie nenhum arquivo novo.** Nem `.py`, nem `__init__.py`, nem
   `requirements.txt`, nem `README.md`, nem `.gitignore`, nem arquivo de exemplo, nem
   placeholder, nem arquivo vazio. Pastas você cria; arquivos, não.
2. **Não altere o conteúdo de nenhum arquivo.** Nenhuma linha. Em especial: **não
   conserte os imports**. Depois da migração eles vão estar quebrados, e isso é
   esperado — o aluno vai ajustá-los.
3. **Não mova e não apague nada. Copie.** O arquivo original permanece onde está.
4. **Não refatore, não renomeie funções, não reorganize código, não adicione
   comentários, não formate.** Nenhuma melhoria, por menor que pareça.
5. **Não divida arquivos** em partes menores, mesmo que o arquivo pareça grande demais
   para o destino.
6. **Não junte arquivos.** Cada arquivo de origem vira um arquivo de destino.
7. Você **pode e deve renomear o arquivo ao copiar**, para o nome canônico do destino.
   Renomear o arquivo é permitido; alterar o conteúdo dele não.
8. **Não instale pacotes, não crie ambiente virtual, não rode o projeto.**
9. Se algo estiver ambíguo, **pergunte ao aluno** em vez de adivinhar.

O projeto **não vai funcionar** ao final desta tarefa. Isso está correto e é
intencional. Não tente fazê-lo funcionar.

---

## Estrutura de destino

Crie esta estrutura dentro da pasta `migracao_fastAPI/` (se ela não existir, crie).

```
migracao_fastAPI/
├── .env                     ← copiar o existente
│
├── app/
│   ├── graph.py             ← o arquivo principal, copiado inteiro
│   ├── prompts.py
│   ├── guardrail.py
│   ├── memory.py
│   │
│   ├── routes/              ← pasta vazia nesta etapa
│   │
│   └── tools/
│       ├── financeiro.py
│       ├── agenda.py
│       └── faq.py
│
├── data/
│   └── (o PDF do FAQ)
│
└── frontend/                ← pasta vazia nesta etapa
```

As pastas `routes/` e `frontend/` ficam **vazias**. Não coloque nada nelas e não crie
arquivos para preenchê-las.

Estes destinos fazem parte da estrutura final do projeto, mas **não existem ainda e
não devem ser criados por você**: `app/main.py`, `app/config.py`, `app/schemas.py`,
`app/llms.py`, `app/agents.py`, `app/tools/db.py`, `app/routes/chat.py`,
`app/routes/sessions.py`, `frontend/index.html`, `frontend/style.css`,
`frontend/app.js`, `requirements.txt`, `README.md`.

---

## Passo 1 — Encontre o arquivo principal

O arquivo principal é aquele que:
- importa `StateGraph` (de `langgraph.graph`) e monta o grafo com `add_node`,
  `add_edge` e `compile()`;
- define uma classe de estado (herda de `MessagesState` ou similar);
- importa os outros módulos do projeto;
- normalmente termina com um loop de terminal (`while True` com `input()`);
- **não é importado por nenhum outro arquivo**.

Pode haver várias versões antigas dele na pasta (arquivos de aulas anteriores, por
exemplo). O principal é o mais completo — o que tem guardrail, memória e o grafo
montado. Na dúvida, pergunte ao aluno qual arquivo ele executa para rodar o projeto.

## Passo 2 — Descubra quais módulos estão realmente em uso

Leia os imports do arquivo principal. Eles listam exatamente quais módulos locais
fazem parte do projeto. **Só esses serão migrados.**

Essa é também a regra que resolve duplicatas. É comum existirem várias versões do
mesmo módulo (`memory.py`, `memory_old.py`, `memory_mongodb.py`, por exemplo). O
arquivo correto é **o que aparece no import do arquivo principal**. Todos os outros
ficam onde estão e não são copiados.

## Passo 3 — Classifique cada módulo pelo conteúdo

Abra cada módulo importado e identifique o destino pela tabela abaixo.

| Destino | Como reconhecer o conteúdo |
|---|---|
| `app/graph.py` | O arquivo principal do Passo 1: estado, nós, arestas, `compile()`. Copie **inteiro, sem remover nada** — inclusive o loop de terminal do final. |
| `app/tools/financeiro.py` | Funções decoradas com `@tool` que fazem `INSERT`/`SELECT`/`UPDATE` de transações financeiras: valor, categoria, forma de pagamento, saldo, extrato. Conecta em PostgreSQL (`psycopg2`). Termina exportando uma lista de tools. |
| `app/tools/agenda.py` | Funções `@tool` que criam ou consultam eventos de calendário: data, horário, duração, participante, conflito de agenda. Também usa `psycopg2`. Exporta a própria lista de tools. |
| `app/tools/faq.py` | Carrega um PDF (`PyPDFLoader` ou equivalente), divide em pedaços (`TextSplitter`), gera embeddings e faz busca por similaridade (FAISS, Chroma, Qdrant…). Exporta uma tool de busca. |
| `app/prompts.py` | Apenas constantes de texto: instruções de comportamento dos agentes, exemplos, personas. Não chama LLM, não acessa banco. |
| `app/guardrail.py` | Detecção e mascaramento de dados pessoais (regex de CPF, e-mail, telefone), bloqueio de mensagens de entrada, revisão da resposta de saída. |
| `app/memory.py` | Usa `pymongo` / `MongoClient`. Cria documentos de sessão, salva mensagens, gera resumo ao encerrar a conversa. |
| `data/` | O arquivo PDF que o módulo de FAQ carrega. Mantenha o nome original do PDF. |
| `.env` | O arquivo de variáveis de ambiente, na raiz de `migracao_fastAPI/`. Copie exatamente como está, sem acrescentar nem remover variáveis. |

Se um módulo importado pelo arquivo principal **não se encaixar em nenhuma linha**
dessa tabela, não invente um lugar para ele: liste-o no relatório final e pergunte ao
aluno.

## Passo 4 — O que não migrar

Deixe onde está, sem copiar e sem apagar:

- versões antigas e duplicadas dos módulos (o Passo 2 já identificou as corretas);
- arquivos de aulas ou exercícios anteriores que o arquivo principal não importa;
- arquivos `.txt`, `.md`, `.zip`, `.ipynb`, rascunhos e anotações;
- pastas `__pycache__`, `.venv`, `venv`, `.git`;
- qualquer módulo que exista na pasta mas que ninguém importe.

## Passo 5 — Casos em que você deve parar e perguntar

Não adivinhe nestas situações:

- dois ou mais arquivos parecem servir ao mesmo destino e os imports do arquivo
  principal não resolvem a dúvida;
- um destino da tabela não tem nenhum arquivo correspondente no projeto;
- um arquivo mistura responsabilidades de dois destinos diferentes (por exemplo,
  prompts e tools no mesmo arquivo) — **não divida**, apenas pergunte;
- existem vários PDFs e não está claro qual é o do FAQ;
- não há arquivo `.env`.

Em qualquer desses casos, faça o resto da migração normalmente e liste a pendência no
relatório.

## Passo 6 — Relatório final

Ao terminar, apresente exatamente três coisas:

**1. Tabela do que foi copiado**

| Arquivo de origem | Destino | Por que foi classificado assim |
|---|---|---|
| (nome real no projeto do aluno) | (caminho novo) | (uma frase sobre o conteúdo) |

**2. Arquivos deixados para trás**, com o motivo em uma frase cada.

**3. O que ainda falta**, listando os destinos da estrutura que continuam vazios e que
o aluno vai precisar criar por conta própria: `app/main.py`, `app/config.py`,
`app/schemas.py`, `app/llms.py`, `app/agents.py`, `app/tools/db.py`,
`app/routes/chat.py`, `app/routes/sessions.py`, os três arquivos de `frontend/`,
`requirements.txt` e `README.md`.

Termine lembrando ao aluno que os imports estão quebrados de propósito e que o próximo
passo, feito por ele, é seguir o `GUIA_MIGRACAO.md`.
