INSERT INTO transactions
    (amount, type, category_id, description, payment_method, occurred_at, source_text)
VALUES
    (5000.00, 1, 10, 'Salário', 'transferência', '2026-09-01T09:00:00-03:00', 'recebi meu salário de 5000 reais'),
    (180.50, 2, 1, 'Compras do mercado', 'cartão de débito', '2026-09-02T18:30:00-03:00', 'gastei 180,50 reais no mercado'),
    (45.00, 2, 5, 'Transporte', 'cartão de crédito', '2026-09-03T08:10:00-03:00', 'gastei 45 reais com transporte'),
    (120.00, 2, 3, 'Curso online', 'pix', '2026-09-04T20:00:00-03:00', 'paguei 120 reais em um curso');
