# type: ignore
import os
from dotenv import load_dotenv
import psycopg2
from typing import Optional, List
from langchain.tools import tool
from pydantic import BaseModel, Field

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  

def get_conn():
    return psycopg2.connect(DATABASE_URL)


# Essa classe garante que o objeto de Python passe todos esses campos
class AddTransactionArgs(BaseModel):
    amount: float = Field(..., description="Valor da transação (use positivo).")
    source_text: str = Field(..., description="Texto original do usuario.")
    occurred_at: Optional[str] = Field(
        default=None,
        description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )
    type_id: Optional[int] = Field(default=None, description="ID em transaction_types (1=INCOME, 2=EXPENSES, 3=TRANSFER).")
    type_name: Optional[str] = Field(default=None, description="Nome do tipo: INCOME | EXPENSES | TRANSFER.")
    category_id: Optional[int] = Field(default=None, description="FK de categories (opcional).")
    category_name: Optional[str] = Field(default=None, description="Nome da categoria (opcional).")
    description: Optional[str] = Field(default=None, description="procure nessa frase uma dessas categoria: (comida, besteira, estudo, férias, transporte, moradia, saúde, lazer, contas, investimento, presente, outros)")
    payment_method: Optional[str] = Field(default=None, description="Forma de pagamento (opcional).")


class QueryTransactionArgs(BaseModel):
    source_text: str = Field(..., description="Texto original do usuário.")
    occurred_at: Optional[str] = Field(
        default=None,
        description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )
    tipo: str = Field(..., description="Tipo da transação: INCOME | EXPENSES | TRANSFER.")


class SaldoTotalArgs(BaseModel):
    source_text: str = Field(..., description="Texto original do usuario.")


class SaldoDiarioArgs(BaseModel):
    source_text: str = Field(..., description="Texto original do usuario.")
    occurred_at: Optional[str] = Field(
        default=None,
        description="Data ISO 8601 do dia a consultar; se ausente, usa o dia atual."
    )





@tool("saldo_total", args_schema=SaldoTotalArgs)
def saldo_total(source_text: str) -> dict:
    """Retorna o saldo total consolidado: soma de entradas menos soma de despesas."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        #FIZ UMA FUNÇÃO NO BANCO PARA ISSO, ENTÃO É SÓ CHAMAR E PEGAR O RESULTADO, O ARQUIVO COM A FUNÇÃO SE CHAMA "functions.sql" E ESTÁ NA PASTA ]
        cur.execute("SELECT total_income, total_expenses, saldo FROM get_saldo_total();")
        row = cur.fetchone()
        total_income = float(row[0])
        total_expenses = float(row[1])
        saldo = float(row[2])
        return {
        "status": "ok","total_income": total_income,"total_expenses": total_expenses,"saldo": saldo,}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            print("Erro ao fechar conexão.")


@tool("saldo_diario", args_schema=SaldoDiarioArgs)
def saldo_diario(source_text: str, occurred_at: Optional[str] = None) -> dict:
    """Retorna entradas, despesas e saldo liquido de um dia especifico."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        #MESMA COISA DO SALDO TOTAL, SÓ QUE CHAMANDO A FUNÇÃO get_saldo_diario, QUE RECEBE UM PARAMETRO DE DATA PARA CALCULAR O SALDO DO DIA, SE O PARAMETRO OCURRED_AT FOR NULO, ELE CALCULA O SALDO DO DIA ATUAL
        if occurred_at:
            cur.execute("SELECT total_income, total_expenses, saldo FROM get_saldo_diario(%s::date);", (occurred_at,))
        else:
            cur.execute("SELECT total_income, total_expenses, saldo FROM get_saldo_diario();")
        row = cur.fetchone()
        total_income = float(row[0])
        total_expenses = float(row[1])
        saldo = float(row[2])
        return {"status": "ok", "total_income": total_income, "total_expenses": total_expenses, "saldo": saldo}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass




    

TYPES_ALIASES = {
    "ENTRADA": "INCOME", "GANHO": "INCOME", "RECEITA": "INCOME",
    "RECEITAS": "INCOME", "GANHOS": "INCOME", "SALARIO": "INCOME",
    "DESPESA": "EXPENSES", "GASTO": "EXPENSES", "GASTOS": "EXPENSES",
    "DESPESAS": "EXPENSES",
    "TRANSFERENCIA": "TRANSFER", "TRANSFERÊNCIA": "TRANSFER",
}

#Garante que o campo type da tabela transactions receba um id vÃ¡lido (1=INCOME, 2=EXPENSES, 3=TRANSFER
def _resolve_type_id(cur, type_id: Optional[int], type_name: Optional[str]) -> Optional[int]:
    if type_name:
        t = type_name.strip().upper()
        if t == "EXPENSE":
            t = "EXPENSES"
        cur.execute("SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else None
    if type_id:
        return int(type_id)
    return None


#Garante que o campo category da tabela transactions receba um id valido
def _resolve_categorie_id(cur, category_id: Optional[int], category_name: Optional[str]) -> Optional[int]:
    if category_name:
        t = category_name.strip().upper()
        cur.execute("SELECT id FROM categories WHERE UPPER(name)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else 12  # fallback para "Outros" se não achar
    if category_id:
        return int(category_id)
    return 12  # Categoria "Outros" como default



#Tool: saldo_total
@tool("search_transactions", args_schema=QueryTransactionArgs)
def search_transactions(
    source_text: str,
    tipo: str,
    occurred_at: Optional[str] = None,
) -> dict:
    """Retorna transações filtradas por tipo e período."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        resolved_type_id = _resolve_type_id(cur, None, tipo)
        if not resolved_type_id:
            return {"status": "error", "message": "Tipo inválido (INCOME/EXPENSES/TRANSFER)."}
        if occurred_at:
            cur.execute(
                """
                SELECT id, amount, type, category_id, description, payment_method, occurred_at
                FROM transactions
                WHERE type = %s AND occurred_at >= %s::timestamptz
                ORDER BY occurred_at DESC
                LIMIT 20;
                """,
                (resolved_type_id, occurred_at)
            )
        else:
            cur.execute(
                """
             SELECT id, amount, type, category_id, description, payment_method, occurred_at
                FROM transactions
                WHERE type = %s
                ORDER BY occurred_at DESC
                LIMIT 20;
                """,
                (resolved_type_id,)
            )

        rows = cur.fetchall()
        transactions = [
            {
            "id": row[0],
                "amount": float(row[1]),
                "type": row[2],
                "category_id": row[3],
                 "description": row[4],
                "payment_method": row[5],
                "occurred_at": str(row[6])
            }
            for row in rows
        ]
        return {"status": "ok", "transactions": transactions}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

# Tool: add_transaction
@tool("add_transaction", args_schema=AddTransactionArgs)
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """Insere uma transação financeira no banco de dados Postgres.""" # docstring obrigatÃ³rio da @tools do langchain (estranho, mas legal nÃ©?)
    conn = get_conn()
    cur = conn.cursor()
    try:
        resolved_type_id = _resolve_type_id(cur, type_id, type_name)
        resolve_categorie_id = _resolve_categorie_id(cur, category_id, category_name)
        if not resolved_type_id:
            return {"status": "error", "message": "Tipo invalido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER)."}

        if occurred_at:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, %s::timestamptz, %s)
                RETURNING id, occurred_at;
                """,
                (amount, resolved_type_id, resolve_categorie_id, description, payment_method, occurred_at, source_text),
            )
        else:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id, occurred_at;
                """,
                (amount, resolved_type_id, resolve_categorie_id, description, payment_method, source_text)
            )

        new_id, occurred = cur.fetchone()
        conn.commit()
        return {"status": "ok", "id": new_id, "occurred_at": str(occurred)}

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass



class UpdateTransactionArgs(BaseModel):
    id: Optional[int] = Field(
        default=None,
        description="ID da transação a atualizar. Se ausente, será feita uma busca por (match_text + date_local)."
    )
    match_text: Optional[str] = Field(
        default=None,
        description="Texto para localizar transação quando id não for informado (busca em source_text/description)."
    )
    date_local: Optional[str] = Field(
        default=None,
        description="Data local (YYYY-MM-DD) em America/Sao_Paulo; usado em conjunto com match_text quando id ausente."
    )
    amount: Optional[float] = Field(default=None, description="Novo valor.")
    type_id: Optional[int] = Field(default=None, description="Novo type_id (1/2/3).")
    type_name: Optional[str] = Field(default=None, description="Novo type_name: INCOME | EXPENSES | TRANSFER.")
    category_id: Optional[int] = Field(default=None, description="Nova categoria (id).")
    category_name: Optional[str] = Field(default=None, description="Nova categoria (nome).")
    description: Optional[str] = Field(default=None, description="Nova descrição.")
    payment_method: Optional[str] = Field(default=None, description="Novo meio de pagamento.")
    occurred_at: Optional[str] = Field(default=None, description="Novo timestamp ISO 8601.")



def _local_date_filter_sql(field: str = "occurred_at") -> str:
    """
    Retorna um trecho SQL para filtragem por dia local em America/Sao_Paulo.
    Ex.: (occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date
    """
    return f"(({field} AT TIME ZONE 'America/Sao_Paulo')::date = %s::date)"

@tool("update_transaction", args_schema=UpdateTransactionArgs)
def update_transaction(
    id: Optional[int] = None,
    match_text: Optional[str] = None,
    date_local: Optional[str] = None,
    amount: Optional[float] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict:
    """
    Atualiza uma transação existente.
    Estratégias:
      - Se 'id' for informado: atualiza diretamente por ID.
      - Caso contrário: localiza a transação mais recente que combine (match_text em source_text/description)
        E (date_local em America/Sao_Paulo), então atualiza.
    Retorna: status, rows_affected, id, e o registro atualizado.
    """
    if not any([amount, type_id, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return {"status": "error", "message": "Nada para atualizar: forneça pelo menos um campo (amount, type, category, description, payment_method, occurred_at)."}

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Resolve target_id
        target_id = id
        if target_id is None:
            if not match_text or not date_local:
                return {"status": "error", "message": "Sem 'id': informe match_text E date_local para localizar o registro."}

            # Buscar o mais recente no dia local informado que combine o texto
            cur.execute(
                f"""
                SELECT t.id
                FROM transactions t
                WHERE (t.source_text ILIKE %s OR t.description ILIKE %s)
                  AND {_local_date_filter_sql("t.occurred_at")}
                ORDER BY t.occurred_at DESC
                LIMIT 1;
                """,
                (f"%{match_text}%", f"%{match_text}%", date_local)
            )
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "Nenhuma transação encontrada para os filtros fornecidos."}
            target_id = row[0]

        # Resolver type_id / category_id a partir de nomes, se fornecidos
        resolved_type_id = _resolve_type_id(cur, type_id, type_name) if (type_id or type_name) else None
        resolved_category_id = category_id
        if category_name and not category_id:
            resolved_category_id = _resolve_categorie_id(cur, category_id, category_name)

        # Montar SET dinâmico
        sets = []
        params: List[object] = []
        if amount is not None:
            sets.append("amount = %s")
            params.append(amount)
        if resolved_type_id is not None:
            sets.append("type = %s")
            params.append(resolved_type_id)
        if resolved_category_id is not None:
            sets.append("category_id = %s")
            params.append(resolved_category_id)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if payment_method is not None:
            sets.append("payment_method = %s")
            params.append(payment_method)
        if occurred_at is not None:
            sets.append("occurred_at = %s::timestamptz")
            params.append(occurred_at)

        if not sets:
            return {"status": "error", "message": "Nenhum campo válido para atualizar."}

        params.append(target_id)

        cur.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = %s;",
            params
        )
        rows_affected = cur.rowcount
        conn.commit()

        # Retornar o registro atualizado
        cur.execute(
            """
            SELECT
              t.id, t.occurred_at, t.amount, tt.type AS type_name,
              c.name AS category_name, t.description, t.payment_method, t.source_text
            FROM transactions t
            JOIN transaction_types tt ON tt.id = t.type
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.id = %s;
            """,
            (target_id,)
        )
        r = cur.fetchone()
        updated = None
        if r:
            updated = {
                "id": r[0],
                "occurred_at": str(r[1]),
                "amount": float(r[2]),
                "type": r[3],
                "category": r[4],
                "description": r[5],
                "payment_method": r[6],
                "source_text": r[7],
            }

        return {
            "status": "ok",
            "rows_affected": rows_affected,
            "id": target_id,
            "updated": updated
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass





# Exporta a lista de tools
TOOLS = [add_transaction, search_transactions, saldo_total, saldo_diario, update_transaction]
