CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL CHECK (currency = 'BRL'),
    status VARCHAR(20) NOT NULL DEFAULT 'PROCESSED' CHECK (status = 'PROCESSED'),
    payload JSONB NOT NULL,
    receive_count INTEGER NOT NULL CHECK (receive_count > 0),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auditoria na mesma transacao do pedido: evidencia por mensagem, sem inferir
-- processamento pela ordem de entrega de uma fila Standard.
CREATE TABLE IF NOT EXISTS order_receipts (
    message_id VARCHAR(100) PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(order_id),
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('created', 'duplicate')),
    receive_count INTEGER NOT NULL CHECK (receive_count > 0),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS order_receipts_order_id_idx ON order_receipts(order_id);

