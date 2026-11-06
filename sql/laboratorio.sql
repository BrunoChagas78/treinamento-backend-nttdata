-- Substitua pelo UUID retornado no POST. Uma linha = processamento confirmado.
SELECT order_id, customer_id, amount, currency, status, receive_count, processed_at
FROM orders WHERE order_id = '00000000-0000-0000-0000-000000000001';

-- Deve permanecer 1 mesmo apos publicar varias vezes o mesmo pedido.
SELECT order_id, count(*) FROM orders GROUP BY order_id HAVING count(*) > 1;

-- Evidencia de sucesso apos retry induzido.
SELECT order_id, receive_count FROM orders WHERE receive_count > 1;

-- Resumo da turma, sem depender da ordem de conclusao dos pedidos.
SELECT customer_id, count(*) AS pedidos, sum(amount) AS total
FROM orders GROUP BY customer_id ORDER BY customer_id;

-- Provar redelivery sem pressupor ordem da fila nem contar mensagens aproximadas.
SELECT message_id, outcome, receive_count, recorded_at
FROM order_receipts WHERE order_id = '00000000-0000-0000-0000-000000000001'
ORDER BY recorded_at;

