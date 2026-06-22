CREATE OR REPLACE FUNCTION get_s+aldo_total()
RETURNS TABLE(total_income NUMERIC, total_expenses NUMERIC, saldo NUMERIC)
LANGUAGE sql AS $$
    SELECT
        COALESCE(SUM(CASE WHEN tt.type = 'INCOME' THEN t.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tt.type = 'EXPENSES' THEN t.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tt.type = 'INCOME' THEN t.amount ELSE -t.amount END), 0)
    FROM transactions t
    JOIN transaction_types tt ON tt.id = t.type;
$$;


CREATE OR REPLACE FUNCTION get_saldo_diario(p_date DATE DEFAULT CURRENT_DATE)
RETURNS TABLE(total_income NUMERIC, total_expenses NUMERIC, saldo NUMERIC)
LANGUAGE sql AS $$
    SELECT
        COALESCE(SUM(CASE WHEN tt.type = 'INCOME' THEN t.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tt.type = 'EXPENSES' THEN t.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN tt.type = 'INCOME' THEN t.amount ELSE -t.amount END), 0)
    FROM transactions t
    JOIN transaction_types tt ON tt.id = t.type
    WHERE t.occurred_at::date = p_date;
$$;