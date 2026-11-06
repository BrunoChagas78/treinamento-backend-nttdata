# Instalação completa do ambiente de treinamento

Este guia prepara uma máquina para executar o projeto, enviar pedidos pelo Postman, consultar o PostgreSQL e executar os testes. O passo a passo principal usa **Windows com PowerShell, Docker Desktop e contêineres Linux**.

As versões da aplicação abaixo foram conferidas no código do projeto. Os procedimentos externos foram consultados em **6 de novembro de 2026**; nomes de telas e condições comerciais podem mudar.

## 1. O que será instalado

| Ferramenta ou dependência | Onde fica | Necessidade e finalidade |
|---|---|---|
| PowerShell | Windows | Terminal para os comandos deste guia |
| WSL 2 | Windows | Backend Linux do Docker Desktop neste passo a passo |
| Docker Desktop, Docker Engine e Docker Compose | Windows | Obrigatórios para executar e provisionar o laboratório |
| Git | Windows | Para clonar e atualizar o projeto; dispensável se recebeu um ZIP |
| LocalStack e sua conta/token | Conta no portal e contêiner Docker | Emular os serviços AWS usados no treinamento |
| PostgreSQL | Contêiner Docker | Armazenar pedidos e recibos de processamento |
| Python e bibliotecas | Imagem Docker do projeto | Provisionamento, Lambdas e testes; instalação automática no build |
| Postman Desktop | Windows | Executar as atividades com a coleção de requisições |
| Python 3.13, pip e venv no Windows | Windows, opcional | Desenvolvimento, testes unitários e scripts fora do Docker |
| Visual Studio Code | Windows, opcional | Editar código e documentação |
| DBeaver Community ou outro cliente PostgreSQL | Windows, opcional | Consultar o banco por interface gráfica; o `psql` já vem no contêiner |

Para executar pelo Docker, não é necessário instalar Python, PostgreSQL, AWS CLI ou LocalStack CLI no Windows. Também não é necessário instalar Node.js, Java, Terraform ou criar uma conta AWS. O provisionamento usa os scripts Python do repositório; os comandos AWS de diagnóstico usam `awslocal` dentro do contêiner LocalStack.

### Versões definidas no projeto

| Componente | Versão/configuração | Arquivo de referência |
|---|---|---|
| Imagem LocalStack | `localstack/localstack:2026.10.0` | [compose.yaml](../compose.yaml) |
| Imagem PostgreSQL | `postgres:17-alpine` | [compose.yaml](../compose.yaml) |
| Python da imagem de ferramentas | `python:3.13-slim` | [Dockerfile](../Dockerfile) |
| Runtime e arquitetura das Lambdas | `python3.13`, `x86_64` | [scripts/provision.py](../scripts/provision.py) |
| boto3 | `1.40.61` | [requirements.txt](../requirements.txt) |
| psycopg com distribuição binária | `3.2.10` | [requirements.txt](../requirements.txt) |
| pydantic | `2.13.4` | [requirements.txt](../requirements.txt) |
| pytest | `8.4.2` | [requirements-dev.txt](../requirements-dev.txt) e [Dockerfile](../Dockerfile) |

`boto3` acessa as APIs AWS emuladas; `psycopg` conecta ao PostgreSQL; `pydantic` valida os pedidos; `pytest` executa os testes. O `pip` resolve as dependências transitivas automaticamente, como `botocore`, `s3transfer` e `pydantic-core`. Não instale essas bibliotecas uma a uma.

As imagens Python e PostgreSQL fixam a linha de versão, mas podem receber novos patches. As bibliotecas diretas estão fixadas nos arquivos de requisitos; o projeto não possui um lock de todas as dependências transitivas. Preserve essas definições ao preparar o ambiente da turma.

## 2. Preparar o Windows e o WSL 2

Use uma versão de Windows 64 bits suportada pelo Docker Desktop e confirme os requisitos na [documentação de instalação para Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Para o backend WSL 2, a documentação consultada informa WSL **2.1.5 ou superior**, virtualização de hardware e pelo menos **8 GB de RAM**.

Como recomendação prática para este laboratório, prefira 16 GB de RAM e reserve cerca de 15 GB livres para imagens, builds e dados. Esses valores são uma margem de trabalho sugerida, não uma medição de consumo do projeto. O ambiente de ferramentas está configurado para `linux/amd64`; este guia prioriza máquinas Intel/AMD de 64 bits. Máquinas ARM precisam validar a emulação dessa arquitetura.

1. Abra **Gerenciador de Tarefas → Desempenho → CPU** e confira se a virtualização está habilitada. Se estiver desabilitada, ative-a na BIOS/UEFI conforme a orientação do fabricante.
2. Abra o PowerShell **como administrador** para instalar o WSL, se ainda não estiver instalado:

```powershell
wsl --install --no-distribution
```

3. Reinicie o computador se solicitado. Em seguida, execute:

```powershell
wsl --update
wsl --set-default-version 2
wsl --version
wsl --status
```

A opção `--no-distribution` instala o WSL sem uma distribuição pessoal como Ubuntu. O Docker Desktop administra seu próprio ambiente; os comandos do projeto serão executados no PowerShell. Se você também quiser um terminal Ubuntu, pode usar `wsl --install -d Ubuntu`, mas isso é opcional para este guia. Referência: [comandos oficiais do WSL](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).

## 3. Instalar e validar o Docker Desktop

1. Baixe o instalador pela [página oficial do Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/), escolhendo a arquitetura da sua máquina.
2. Execute o instalador e escolha o backend **WSL 2** quando essa opção aparecer.
3. Conclua a instalação, reinicie se solicitado e abra o **Docker Desktop**.
4. Aguarde o engine iniciar e confirme o uso de **contêineres Linux**.
5. Abra uma nova janela normal do PowerShell e valide:

```powershell
docker --version
docker compose version
docker version
docker info --format '{{.OSType}}'
```

O comando `docker version` deve mostrar **Client** e **Server**, sem erro de conexão. O último comando deve responder `linux`. Apenas `docker --version` não comprova que o engine está disponível.

O Docker Desktop já inclui Engine, CLI e Compose; não é necessário instalar Compose separadamente. Use a sintaxe **`docker compose`**, com espaço, presente neste projeto. Referência: [instalação do Compose](https://docs.docker.com/compose/install/).

Se o Docker estiver em modo Windows containers, abra seu menu e selecione a opção de alternar para Linux containers, quando disponível. Mantenha o Docker Desktop aberto durante as atividades.

## 4. Instalar o Git e obter o projeto

1. Baixe e execute o [instalador oficial do Git para Windows](https://git-scm.com/install/windows).
2. Durante a instalação, mantenha o Git disponível na linha de comando e conclua o assistente.
3. Abra um novo PowerShell e confira:

```powershell
git --version
```

Se recebeu o projeto por repositório, substitua a URL abaixo pela informada pelo responsável pelo treinamento:

```powershell
$repositoryUrl = 'COLE_AQUI_A_URL_DO_REPOSITORIO'
git clone $repositoryUrl TreinamentoBackend
Set-Location .\TreinamentoBackend
```

Se recebeu um ZIP, extraia todo o conteúdo e abra o PowerShell na pasta que contém `compose.yaml`. Se o projeto já estiver na sua máquina, entre nessa pasta. Na instalação usada para preparar este guia, o caminho é:

```powershell
Set-Location 'C:\Users\bruno\Documents\ChatGPT\TreinamentoBackend'
```

Adapte o caminho ao seu usuário. Confirme a pasta antes de continuar:

```powershell
Test-Path .\compose.yaml
Test-Path .\Dockerfile
Test-Path .\requirements.txt
```

Os três resultados devem ser `True`. Todos os comandos seguintes partem dessa raiz, salvo indicação contrária.

## 5. Criar a conta do LocalStack e obter o token

O Compose usa a imagem autenticada do LocalStack. A conta deve ter uma licença válida que permita os serviços do laboratório: **IAM, STS, Lambda, SQS, API Gateway e Logs**.

### Cadastro e licença

1. Acesse a [página de planos do LocalStack](https://www.localstack.cloud/pricing) e selecione **Get Started for Free**, ou a opção de cadastro apresentada.
2. Preencha os dados solicitados usando um dos métodos de autenticação disponíveis.
3. Confirme seu e-mail, se solicitado, e entre no [portal LocalStack](https://app.localstack.cloud/).
4. Se sua empresa forneceu acesso, entre no workspace indicado e confira se a licença foi atribuída ao seu usuário. Caso contrário, selecione a modalidade adequada ao treinamento.
5. Confira a validade e os serviços disponíveis na área de licença. As condições de avaliação e dos planos devem ser verificadas no portal; o cadastro sozinho não garante acesso permanente.

Referência: [criação e acesso a contas LocalStack](https://docs.localstack.cloud/aws/organizations-admin/accounts/).

### Token de desenvolvimento

No portal, abra **Auth Tokens**, obtenha seu **Developer Token** e copie-o para o `.env` descrito na próxima seção. Esse token ativa a licença; não corresponde às credenciais AWS simuladas `test/test` do projeto. Referência: [Auth Token](https://docs.localstack.cloud/aws/getting-started/auth-token/).

## 6. Configurar o arquivo `.env`

O projeto inclui [.env.example](../.env.example), sem credenciais. Crie o arquivo local somente se ele ainda não existir:

```powershell
if (-not (Test-Path .\.env)) {
    Copy-Item .\.env.example .\.env
}
notepad .\.env
```

Preencha a variável com o token copiado do portal e salve:

```dotenv
LOCALSTACK_AUTH_TOKEN=COLE_AQUI_SEU_TOKEN
```

Use o nome exato **`.env`**, na mesma pasta de `compose.yaml`, sem a extensão `.txt`. O `.gitignore` e o `.dockerignore` já excluem `.env`. Não coloque o token em `.env.example`, no código, em prints ou em arquivos versionados.

O Compose lê esse arquivo e injeta `LOCALSTACK_AUTH_TOKEN` no contêiner. Configurar o token apenas com `localstack auth set-token` em uma CLI não substitui o `.env` deste fluxo. O Python executado diretamente no Windows também não carrega esse `.env` automaticamente.

### Configurações opcionais

| Variável no `.env` | Padrão do Compose | Quando alterar |
|---|---|---|
| `LOCALSTACK_AUTH_TOKEN` | Vazio | Preenchimento obrigatório com seu token |
| `LOCALSTACK_PORT` | `4566` | Outra aplicação ocupa a porta local do LocalStack |
| `POSTGRES_PORT` | `5433` | Outra aplicação ocupa a porta local do banco |
| `COMPOSE_PROJECT_NAME` | `treinamento-backend` | Alterar o nome do projeto/rede/volume Docker |
| `LOCALSTACK_IMAGE` | `localstack/localstack:2026.10.0` | Apenas ao validar uma mudança de versão do laboratório |

Exemplo de alteração de portas, acrescentando ao `.env`:

```dotenv
LOCALSTACK_PORT=4567
POSTGRES_PORT=5434
```

Isso altera as portas no Windows; dentro da rede Docker continuam valendo `localstack:4566` e `postgres:5432`. O provisionamento gera a URL pública conforme `LOCALSTACK_PORT`. Após mudar portas, recrie os serviços, reprovisione e reimporte o ambiente Postman. Mudar `COMPOSE_PROJECT_NAME` seleciona outra rede e outro volume de banco; para uma instalação individual, mantenha o padrão.

Se já houver uma variável com o mesmo nome na sessão PowerShell, ela pode prevalecer na interpolação do Compose. Abra uma sessão limpa ou remova somente a variável conflitante, por exemplo `Remove-Item Env:LOCALSTACK_AUTH_TOKEN -ErrorAction SilentlyContinue`, para usar o valor do `.env`. Referência: [precedência de variáveis do Compose](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/).

## 7. Baixar imagens, instalar dependências e iniciar

Com o Docker Desktop iniciado e o `.env` preenchido:

```powershell
docker compose config --quiet
docker compose pull localstack postgres
docker compose up --build -d
docker compose logs -f provision
```

`config --quiet` valida a configuração sem imprimir o token; ele não valida a licença nem a disponibilidade dos serviços. O primeiro início pode demorar por causa dos downloads, da instalação das bibliotecas e da preparação das Lambdas. É necessário acesso à internet para baixar imagens/pacotes e ativar a licença.

O build instala as bibliotecas de `requirements.txt` em `/opt/function`, junto ao código das Lambdas, e instala `pytest` na imagem de ferramentas. O provisionador empacota as dependências **Linux**, cria os recursos e gera os arquivos locais. Não execute `python -m scripts.provision` no Windows: o empacotamento depende dessa estrutura interna da imagem Docker.

Quando o provisionamento terminar, saia do acompanhamento de logs com `Ctrl+C`, se necessário. Isso encerra o acompanhamento, não os serviços iniciados com `-d`. Confira:

```powershell
docker compose ps -a
```

| Serviço | Resultado esperado |
|---|---|
| `localstack` | Em execução e `healthy` |
| `postgres` | Em execução e `healthy` |
| `provision` | Encerrado com código `0`, normalmente exibido como `Exited (0)` |

`provision` é uma tarefa de execução única; seu encerramento com código 0 representa sucesso. Os serviços `tests` e `lab` usam profiles e só são criados quando chamados. As Lambdas são executadas em contêineres administrados pelo LocalStack, não como serviços adicionais em `compose.yaml`.

### Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `.local/manifest.json` | URLs, nomes das funções, filas e identificador do consumidor |
| `.local/postman.local.json` | Ambiente Postman com a URL da instalação |
| `reports/pytest.xml` | Relatório JUnit, gerado ao executar a suíte completa |

Não crie nem copie o manifesto de outra máquina: os identificadores podem mudar ao recriar o LocalStack.

## 8. Validar LocalStack, API e consumidor

Para verificar a ativação, consulte o endpoint de informações e os logs do LocalStack:

```powershell
# Ajuste a porta se mudou LOCALSTACK_PORT no .env.
Invoke-RestMethod 'http://localhost:4566/_localstack/info'
docker compose logs --tail 100 localstack
```

Confira os dados de licença retornados e a ausência de erros de ativação. O endpoint `/_localstack/health` usado pelo healthcheck verifica a resposta do LocalStack; a conclusão do provisionamento e o `/health` da aplicação verificam outras partes do ambiente. Referência: [verificação de ativação](https://docs.localstack.cloud/aws/getting-started/auth-token/).

Para testar a aplicação e as filas:

```powershell
Test-Path .\.local\manifest.json
Test-Path .\.local\postman.local.json
$labConfig = Get-Content .\.local\manifest.json -Raw | ConvertFrom-Json
Invoke-RestMethod "$($labConfig.base_url)/health"
docker compose --profile tools run --rm lab status
```

Os dois arquivos devem existir, a API deve retornar `status = ok` e o status do Worker deve ser **`Enabled`**. O `/health` da aplicação consulta o banco e a fila; isoladamente, não comprova o processamento de um pedido. Essa validação será feita com Postman e testes.

## 9. Instalar e configurar o Postman

1. Baixe o **Postman Desktop** na [página de downloads](https://www.postman.com/downloads/), execute o instalador do Windows e abra o aplicativo. Consulte a [instalação oficial](https://learning.postman.com/docs/getting-started/installation/install-app/).
2. Conclua o acesso/cadastro se solicitado e abra um workspace para o treinamento.
3. Abra **Import** — em versões que exibem **Use resources or import**, entre nessa opção e selecione a aba de importação.
4. Importe `postman/treinamento.postman_collection.json`.
5. Importe também `.local/postman.local.json`, gerado após o provisionamento.
6. Selecione o ambiente **Treinamento local** no seletor de ambientes e personalize `customer_id` se desejar.

O aplicativo aceita a importação de coleções e ambientes por arquivo ou arrastando-os para a janela de importação. Referência: [importação no Postman](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data/).

### Primeiro pedido

1. Abra a pasta **01 — Sucesso** e execute a requisição de saúde: esperado **200**.
2. Execute **01.02 Criar pedido válido**: esperado **202** e um `order_id` na resposta.
3. Execute a consulta desse pedido. Enquanto o Worker processa, pode retornar **404**; repita até retornar **200**.
4. Confira o mesmo UUID no PostgreSQL, conforme a próxima seção.

Para rodar a pasta inteira, use o **Collection Runner com delay de 1000 ms**, conforme a coleção. Não configure `base_url` manualmente nem acrescente `/orders` ao seu valor. Após recriar o LocalStack, reimporte o ambiente gerado para atualizar a URL.

Mais detalhes dos cenários, variáveis e falhas esperadas: [guia da coleção Postman](../postman/README.md).

## 10. Acessar o PostgreSQL

O Compose instala o servidor e inicializa as tabelas por meio de `sql/001_schema.sql`. Não é necessário instalar um servidor PostgreSQL no Windows.

### Pelo terminal do contêiner

```powershell
docker compose exec postgres psql -U training -d orders
```

Dentro do `psql`:

```sql
\dt
SELECT order_id, customer_id, amount, status, processed_at
FROM orders
ORDER BY processed_at DESC
LIMIT 10;
\q
```

`\dt` lista as tabelas e `\q` encerra. São esperadas as tabelas `orders` e `order_receipts`. Um pedido processado aparece em `orders` com status `PROCESSED`.

### Por interface gráfica, opcional

Se quiser um cliente gráfico, baixe e instale o [DBeaver Community](https://dbeaver.io/download/) para Windows. O instalador padrão inclui o Java necessário; não é preciso instalá-lo separadamente para esse uso.

Abra uma nova conexão PostgreSQL e informe:

| Campo | Valor no Windows |
|---|---|
| Host | `localhost` |
| Porta | `5433`, ou o valor de `POSTGRES_PORT` |
| Database | `orders` |
| Usuário | `training` |
| Senha | `training` |
| JDBC URL, se solicitada | `jdbc:postgresql://localhost:5433/orders` |

Aceite o download do driver PostgreSQL se o cliente solicitar e teste a conexão. Use esses dados somente no laboratório local. Dentro dos contêineres, o banco é acessado por `postgres:5432`, e não por `localhost:5433`.

## 11. Executar os testes pelo Docker

Com o provisionamento concluído, a API saudável e o Worker habilitado:

```powershell
# Suíte completa e relatório JUnit em reports/pytest.xml.
docker compose --profile test run --rm tests
```

Para executar separadamente:

```powershell
docker compose --profile test run --rm tests python -m pytest -m unit -v
docker compose --profile test run --rm tests python -m pytest -m contract -v
docker compose --profile test run --rm tests python -m pytest -m integration -v
docker compose --profile test run --rm tests python -m pytest -m resilience -v
```

| Marcador | O que valida | Infraestrutura necessária |
|---|---|---|
| `unit` | Regras, mocks e tratamento de falhas | Sem LocalStack/banco; pelo Docker, exige engine e imagem construída |
| `contract` | Contrato HTTP da API | Laboratório provisionado |
| `integration` | Fluxo assíncrono e persistência SQL | Laboratório e consumidor ativo |
| `resilience` | Retry, duplicidade, DLQ e recuperação | Laboratório e consumidor ativo |

Os testes devem terminar sem falhas e com código de saída **0**. Os cenários de retry e DLQ podem levar alguns minutos. Os comandos filtrados substituem o comando padrão; para gerar JUnit neles, acrescente `--junitxml=/app/reports/pytest.xml`.

Os testes criam pedidos e mensagens. Use uma instalação individual e evite pausar o Worker durante a execução. Se ele tiver sido pausado em um exercício, retome com:

```powershell
docker compose --profile tools run --rm lab resume
```

## 12. Instalar Python no Windows para desenvolvimento, opcional

Faça esta etapa se quiser executar testes unitários e scripts diretamente no Windows. O Docker continuará necessário para provisionar as Lambdas e para os testes funcionais.

### Python 3.13, pip e ambiente virtual

Instale o **Python 3.13 de 64 bits** pelos [downloads oficiais para Windows](https://www.python.org/downloads/windows/). No instalador tradicional, habilite `pip`, o launcher `py` e a opção de adicionar Python ao `PATH`. Se usar o gerenciador de instalação Python, instale a versão 3.13 por ele. Confira as [orientações do Python para Windows](https://docs.python.org/3.13/using/windows.html).

Abra um novo PowerShell na raiz do projeto:

```powershell
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -m unit -v
```

`requirements-dev.txt` inclui `requirements.txt`, por isso instala todas as dependências diretas da aplicação e o pytest. `pip check` deve informar que não há dependências quebradas. Para ver todas as versões efetivamente instaladas, inclusive as transitivas:

```powershell
.\.venv\Scripts\python.exe -m pip freeze
```

Os exemplos chamam o executável da `.venv` diretamente e funcionam sem ativar scripts do PowerShell. Ativar o ambiente é opcional: `.\.venv\Scripts\Activate.ps1`; após a ativação, use `python` e saia com `deactivate`. Se a política da máquina bloquear scripts, continue usando o caminho explícito, sem alterar a política. Referência: [ambientes virtuais com venv](https://docs.python.org/3.13/library/venv.html).

### Scripts e testes funcionais executados no Windows

O Compose já configura as variáveis dentro dos contêineres. Para executar ferramentas no Windows, defina as variáveis na **sessão atual**, depois de subir e provisionar o laboratório:

```powershell
# Adapte as portas se as alterou no .env.
$env:AWS_ACCESS_KEY_ID = 'test'
$env:AWS_SECRET_ACCESS_KEY = 'test'
$env:AWS_DEFAULT_REGION = 'us-east-1'
$env:AWS_EC2_METADATA_DISABLED = 'true'
$env:AWS_ENDPOINT_URL = 'http://localhost:4566'
$env:DATABASE_URL = 'postgresql://training:training@localhost:5433/orders'
$env:LAB_MANIFEST = (Resolve-Path .\.local\manifest.json).Path
$labConfig = Get-Content $env:LAB_MANIFEST -Raw | ConvertFrom-Json
$env:BASE_URL = $labConfig.base_url
```

`BASE_URL` precisa apontar à URL pública: com `LAB_MANIFEST` definido, a fixture de testes escolheria a URL interna do Docker se `BASE_URL` não fosse informado. As credenciais `test/test` são locais; o token LocalStack continua sendo configurado no `.env` para o contêiner.

```powershell
# Publicar um pedido diretamente na fila.
.\.venv\Scripts\python.exe .\enviar_pedido_sqs.py

# Consultar filas e o consumidor.
.\.venv\Scripts\python.exe -m scripts.lab status

# Executar os testes com infraestrutura e gerar o relatório.
.\.venv\Scripts\python.exe -m pytest -m 'contract or integration or resilience' -v --junitxml=reports/pytest.xml
```

`ORDERS_QUEUE_URL` e `ENABLE_FAULTS` são configuradas pelo provisionador no ambiente das Lambdas. Você não precisa defini-las para usar a API, o script de envio ou os testes acima. Reabra a sessão para descartar as variáveis temporárias ao encerrar.

### Visual Studio Code, opcional

Instale pelo [site oficial do VS Code para Windows](https://code.visualstudio.com/docs/setup/windows), abra a pasta do projeto e instale a extensão **Python**, da Microsoft, se for desenvolver. Execute **Python: Select Interpreter** na paleta de comandos e selecione `.venv\Scripts\python.exe`. O editor é uma conveniência e não é exigido para executar o laboratório.

## 13. Rotina de uso, atualização e parada

Para iniciar novamente e conferir o provisionamento:

```powershell
docker compose up --build -d
docker compose logs -f provision
docker compose ps -a
```

Para atualizar o código empacotado nas Lambdas ou refazer um provisionamento que falhou, depois de corrigir sua causa e com banco/LocalStack saudáveis:

```powershell
docker compose build
docker compose run --rm provision
```

Confira o código de saída e o `/health` novamente. Reprovisionar também reabilita o consumidor. Para parar e remover os serviços e a rede do Compose:

```powershell
docker compose down
```

O volume PostgreSQL permanece, mas o LocalStack **não tem persistência configurada** neste projeto. Depois de remover/recriar seu contêiner, provisione novamente, releia o manifesto e reimporte o ambiente Postman. Os arquivos em `.local` podem continuar no disco mesmo que os recursos aos quais apontam já não existam.

**Somente para reiniciar o laboratório apagando todos os dados do banco deste projeto**, use:

```powershell
docker compose down --volumes
```

Na próxima subida, o PostgreSQL recriará as tabelas pelo script inicial. Não use esse comando para resolver problemas comuns de token ou URL. O SQL de inicialização roda apenas quando o volume de dados está vazio; uma mudança em `sql/001_schema.sql` não é aplicada automaticamente a um banco existente.

## 14. Solução de problemas

| Sintoma | Como verificar e corrigir |
|---|---|
| `docker` ou `git` não reconhecido | Confirme a instalação e abra um terminal novo para recarregar o `PATH` |
| Docker mostra apenas Client, erro no pipe ou acesso negado | Abra o Docker Desktop, aguarde o engine e confirme o contexto com `docker context ls`; valide em um PowerShell da sua sessão de usuário |
| Docker retorna `windows` | Alterne o Docker Desktop para Linux containers |
| WSL ou virtualização indisponível | Confira BIOS/UEFI, `wsl --version` e `wsl --update`; reinicie após instalar os recursos |
| `port is already allocated` / porta ocupada | Identifique o processo com `Get-NetTCPConnection -LocalPort 4566,5433 -State Listen -ErrorAction SilentlyContinue`; configure portas livres no `.env` e reprovisione |
| LocalStack encerra com erro de licença | Confira token, workspace/licença e validade; veja `docker compose logs --tail 100 localstack` e a [orientação de ativação](https://docs.localstack.cloud/aws/getting-started/auth-token/) |
| Token corrigido, mas ainda há falha | Confira se o arquivo é `.env`, sem `.txt`, e se não há variável de sessão conflitante; recrie o serviço conforme o procedimento abaixo |
| Download de imagem ou instalação de pacote falha | Confira internet, espaço em disco, proxy e certificados da rede; repita pull/build após corrigir a causa |
| LocalStack saudável, mas provisionamento falha | Veja `docker compose logs --tail 200 provision`; o healthcheck não comprova que os recursos foram criados |
| `manifest.json` ou ambiente Postman ausente | O provisionamento deve concluir com código 0; corrija a falha e execute `docker compose run --rm provision` |
| Postman recebe erro de API inexistente | Reimporte `.local/postman.local.json` depois do provisionamento e selecione **Treinamento local** |
| Postman mantém `{{base_url}}` na URL | Selecione o ambiente importado e confirme se a variável está habilitada |
| Banco não conecta | No Windows, use `localhost:5433` ou a porta configurada; na rede Docker, `postgres:5432`; confira `docker compose logs postgres` |
| Tabelas ausentes em um volume existente | Confira os logs de inicialização e o schema; recriar o volume apaga dados e só deve ser feito se essa for a intenção |
| `ModuleNotFoundError` no Windows | Instale `requirements-dev.txt` usando `.venv\Scripts\python.exe` e use esse mesmo interpretador para executar |
| `py -3.13` não encontra Python | Instale o runtime 3.13 e confira com `py --list`; evite criar a `.venv` com outra versão por engano |
| Teste no Windows tenta acessar host `localstack` | Defina `BASE_URL` pública e `AWS_ENDPOINT_URL=http://localhost:4566`, conforme a seção 12 |
| POST retorna 202, mas GET permanece 404 | Confira Worker `Enabled`, logs, UUID e DLQ; 202 confirma publicação, não persistência |
| Retry/DLQ demora | O visibility timeout é 60 s e `maxReceiveCount=3`; aguarde alguns minutos com o consumidor ativo |

### Aplicar um token novo

Depois de atualizar o `.env`, com o PostgreSQL ativo:

```powershell
docker compose up -d --force-recreate localstack
docker compose ps -a
```

Aguarde `localstack` ficar `healthy`, então execute:

```powershell
docker compose run --rm provision
$labConfig = Get-Content .\.local\manifest.json -Raw | ConvertFrom-Json
Invoke-RestMethod "$($labConfig.base_url)/health"
```

A recriação remove os recursos efêmeros anteriores do LocalStack; por isso é necessário reprovisionar e reimportar o ambiente Postman. Se um token for exposto, substitua-o no portal e atualize o `.env`.

Para investigar falhas de processamento:

```powershell
docker compose --profile tools run --rm lab status
docker compose --profile tools run --rm lab logs --function api
docker compose --profile tools run --rm lab logs --function worker
```

O [guia de operação](acompanhar-fluxo.md) detalha filas, SQL, pausa/retomada, falhas e recuperação de mensagens.

## 15. Checklist de ambiente pronto

- [ ] WSL 2 disponível e virtualização habilitada no Windows.
- [ ] Docker Desktop em execução; `docker version` mostra Server e o engine usa Linux.
- [ ] `docker compose version` funciona.
- [ ] Arquivos do projeto presentes e terminal na raiz correta.
- [ ] Conta LocalStack criada, licença conferida e Developer Token salvo somente no `.env` local.
- [ ] LocalStack e PostgreSQL `healthy`.
- [ ] Provisionamento concluído com código 0.
- [ ] `.local/manifest.json` e `.local/postman.local.json` gerados.
- [ ] `/health` da aplicação retorna 200 com `status = ok` e o Worker está `Enabled`.
- [ ] Postman com coleção importada e ambiente **Treinamento local** selecionado.
- [ ] Pedido criado com 202, consultável com 200 e localizado no PostgreSQL pelo UUID.
- [ ] Suíte completa passa e `reports/pytest.xml` foi gerado.
- [ ] Se usar desenvolvimento no Windows: Python 3.13, `.venv`, dependências instaladas e unitários aprovados.
