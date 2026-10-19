# ETL Outlook → PostgreSQL

Baixa os relatórios .xlsx/.xls recebidos no Outlook >>Clássico<< (pasta `Base_3352`),
salva o original numa pasta Staging, carrega no PostgreSQL, mantendo
o histórico de cada versão diária do relatório. Caso o arquivo seja carregado com sucesso,
o salva na pasta Processados, se não, fica na Staging.

```
Outlook → landing zone → transformação → PostgreSQL → pasta processados
```

- **Idempotente:** rodar duas vezes não duplica dados (nome do arquivo + SHA-256).
- **Falha visível:** coluna faltando/nova ou tipo inválido aborta só aquele arquivo, que fica na Staging para a próxima extração.
- **Originais preservados:** os arquivos nunca são alterados, só movidos para `PROCESSADOS` após a carga.

## Requisitos

- Windows com Outlook Clássico configurado
- Python 3.13
- PostgreSQL 
- Criar e configurar pasta no Outlook que receberá os arquivos que irão ser baixados

## Instalação

```bash
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # e preencha os valores
```

Crie o banco rodando `sql/001_estrutura.sql` no pgAdmin (instruções no próprio arquivo).

## Execução

Sempre a partir da raiz do projeto:

```bash
python -m src.main                  # extração + carga
python -m src.outlook_extraction    # só extração
python -m src.loader                # só carga
```

## Estrutura

```
├── config/schema.json           de-para das colunas (Excel → BD)
├── sql/001_estrutura.sql        criação de schemas, tabelas e view
├── src/
│   ├── __init__.py
│   ├── config.py                dotenv, de-para, pastas, conexão
│   ├── outlook_extraction.py    Outlook → Staging
│   ├── normalizar.py            trata nomes e tipos das colunas
│   ├── loader.py                Staging → Postgres
│   └── main.py                  orquestrador
├── .env.example
└── requirements.txt
```

## Modelo de dados

- `etl.controle_cargas` — uma linha por arquivo carregado (hash único, data de envio).
- `raw.base_3352` — dados de todas as cargas, ligados por `load_id`.
- `raw.vw_base_3352_atual` — retrato mais recente (último e-mail enviado).

## Problemas comuns

- **Bases Ignoradas** Verifique quais bases constam na pasta que o programa irá checar. Tenha certeza de que ela esteja atualizada. 
- **"Estrutura mudou":** o relatório de origem mudou. Compare com `config/schema.json` e, se preciso, ajuste o SQL.

