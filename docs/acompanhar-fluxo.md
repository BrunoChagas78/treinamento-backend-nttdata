# Operar e acompanhar o fluxo

Execute os comandos na raiz do projeto, em uma instalação individual. Para cada experimento, use um pedido novo e acompanhe o mesmo `order_id`.

## Recursos e logs

```powershell
$labConfig = Get-Content .local/manifest.json | ConvertFrom-Json
docker compose ps -a
docker compose --profile tools run --rm lab status
docker compose --profile tools run --rm lab logs --function api
docker compose --profile tools run --rm lab logs --function worker
```

O manifesto contém as URLs e os nomes das funções. `lab status` consulta atributos sem consumir mensagens. `lab logs` mostra até 100 eventos; para buscar o histórico paginado de uma função:

```powershell
docker compose exec localstack awslocal logs filter-log-events --log-group-name /aws/lambda/training-orders-worker --output json
```

A API registra `accepted` com `order_id`. O Worker registra `created` ou `duplicate` com `order_id`, `message_id` e tentativa. As linhas `processing_failed` usam `message_id`.

## Acompanhar um pedido

1. Pause o consumidor: `docker compose --profile tools run --rm lab pause`. Aguarde `Disabled`; invocações anteriores podem terminar.
2. No Postman, execute **01.02 Criar pedido válido** e copie o UUID da resposta. O POST deve retornar 202.
3. Consulte o pedido manualmente por GET e por SQL. Enquanto aguarda o Worker, o resultado esperado é 404 e nenhuma linha no banco. Não execute o Runner completo durante a pausa.
4. Retome: `docker compose --profile tools run --rm lab resume`.
5. Aguarde GET 200, uma linha `PROCESSED` em `orders` e um recibo `created` em `order_receipts`.

Ao interromper o experimento, retome o Worker antes de executar testes.

Para consultar os componentes diretamente:

```powershell
docker compose exec localstack awslocal apigateway get-resources --rest-api-id $labConfig.api_id
docker compose exec localstack awslocal lambda get-event-source-mapping --uuid $labConfig.mapping_id --query '{State:State,BatchSize:BatchSize,FunctionResponseTypes:FunctionResponseTypes}'
docker compose exec localstack awslocal sqs get-queue-attributes --queue-url $labConfig.queue_url --attribute-names All
```

Contadores da SQS são aproximados e não identificam um pedido. Um recebimento manual com `receive-message` aumenta a contagem de recebimentos e altera o experimento, inclusive o modo `once`. Para apenas observar, use atributos e logs.

## Consultar o PostgreSQL

```powershell
docker compose exec postgres psql -U training -d orders
```

Em um cliente SQL no Windows: host `localhost`, porta `5433`, banco `orders`, usuário e senha `training`. Se configurar `POSTGRES_PORT` no `.env`, use essa porta.

Substitua o UUID nas consultas:

```sql
SELECT order_id, customer_id, amount, status, receive_count, processed_at
FROM orders
WHERE order_id = '835be78d-86ba-4bc1-8310-08c7e2c22294';

SELECT message_id, outcome, receive_count, recorded_at
FROM order_receipts
WHERE order_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY recorded_at;
```

Outros exemplos: [sql/laboratorio.sql](../sql/laboratorio.sql). No psql, `\dt` lista tabelas e `\q` encerra.

`order_receipts` registra mensagens processadas com sucesso, não todas as tentativas que falharam. Ao reenviar o mesmo pedido, aguarde o novo recibo `duplicate` e confirme que `orders` continua com uma linha. Mesmo ID com dados diferentes falha no Worker e pode chegar à DLQ; o POST continua respondendo 202.

## Falhas e recuperação

Use as subpastas da coleção ou publique diretamente na fila:

```powershell
docker compose --profile tools run --rm lab send --failure once
docker compose --profile tools run --rm lab send --failure permanent
```

| Modo | Evidência esperada |
|---|---|
| `once` | Nova entrega conclui e o banco registra `receive_count >= 2` |
| `permanent` | Pedido ausente no banco e mensagem específica na DLQ |

O projeto usa visibility timeout de **60 s**, Lambda de **10 s**, lote de até **5** e `maxReceiveCount=3`. Retry costuma exigir cerca de um minuto; DLQ, cerca de três, com variação.

Para conferir o conteúdo da DLQ, sem excluir mensagens:

```powershell
docker compose exec localstack awslocal sqs receive-message --queue-url $labConfig.dlq_url --max-number-of-messages 10 --wait-time-seconds 1 --visibility-timeout 0 --message-system-attribute-names All
```

Identifique o UUID no `Body`. Um GET 404 isolado não comprova DLQ. O lote pode não conter a mensagem procurada.

Depois de localizar o pedido na DLQ:

```powershell
docker compose --profile tools run --rm lab redrive UUID-DO-PEDIDO
```

A ferramenta corrige `failure_mode`, envia à fila principal e só depois remove a original da DLQ. JSON inválido ou outros conflitos exigem correção da causa. Confirme a recuperação por GET e SQL.

## Atualizar, parar e diagnosticar

```powershell
docker compose build
docker compose run --rm provision
docker compose down
```

Reprovisionar atualiza as funções e reabilita o mapping. O LocalStack é efêmero nesta configuração: após recriá-lo, provisione novamente e reimporte o ambiente Postman. O volume PostgreSQL persiste; o schema inicial só roda na criação do volume. `docker compose down --volumes` apaga os dados deste projeto.

| Problema | Verificação |
|---|---|
| Docker não responde | Iniciar o engine Linux do Docker Desktop |
| LocalStack não inicia | `docker compose logs localstack`; conferir token e licença |
| Provisionamento falha | `docker compose logs provision` |
| API id não corresponde a uma API implantada | Confira se o provisionamento terminou com código 0; se falhou, corrija a causa e execute `docker compose run --rm provision`. Depois, reimporte `.local/postman.local.json` no Postman |
| GET permanece 404 | Mapping ativo, logs do Worker, UUID correto e DLQ |
| Conexão ao banco falha | Windows: `localhost:5433`; contêiner: `postgres:5432` |
| API do Postman não existe | Reimportar `.local/postman.local.json` |
