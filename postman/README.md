# Coleção Postman

Para instalar o aplicativo e preparar os serviços, siga o [guia completo de instalação](../docs/instalacao.md).

Importe `treinamento.postman_collection.json` e o ambiente gerado `.local/postman.local.json`. Selecione **Treinamento local** e personalize `customer_id`. A variável `base_url` não inclui `/orders`.

| Pasta | Conteúdo |
|---|---|
| 01 — Sucesso | Saúde, criação, consulta, reenvio e nova consulta |
| 02 — Falhas HTTP esperadas | Casos independentes de 400, 404 e 413 |
| 03 — Processamento assíncrono | Falha temporária com recuperação e falha permanente |

Os nomes indicam o status esperado: um caso `[400]` aprova quando recebe o erro correto. Há descrições, exemplos e asserts em cada requisição.

## Execução

Use o **Collection Runner com delay de 1000 ms**. Nos cenários assíncronos, execute a subpasta inteira, começando pelo POST. Com **Send** manual, reenvie o GET após aguardar; não há repetição automática.

| Variável da coleção | Cenário |
|---|---|
| `success_order_id` | Pedido válido e seu reenvio |
| `retry_order_id` | Falha temporária |
| `dlq_order_id` | Falha permanente |

Os POSTs iniciais geram novos UUIDs. Só o reenvio reutiliza ID e dados. Não crie variáveis de ambiente com esses nomes, pois elas substituiriam as da coleção.

O polling tem prazo de 90 s para sucesso, 150 s para retry e limite de 180 consultas. Ajustes: `poll_timeout_ms`, `retry_timeout_ms` e `max_poll_attempts`.

## Interpretação

- 202 confirma publicação; 200 no GET confirma pedido consultável.
- O reenvio HTTP sozinho não comprova idempotência: verificar SQL e recibos.
- O GET 404 do cenário permanente é anterior à recuperação e não comprova DLQ.
- Cada execução do cenário permanente cria uma mensagem para o exercício.

Para conferir filas, consultar SQL e recuperar um pedido: [guia de operação](../docs/acompanhar-fluxo.md).
