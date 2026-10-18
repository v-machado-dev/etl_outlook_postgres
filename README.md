# ETL Outlook → PostgreSQL

Baixa os relatórios .xlsx/.xls recebidos no Outlook (pasta `Base_3352`),
guarda o original numa pasta Staging e carrega no PostgreSQL, mantendo
o histórico de cada versão diária do relatório.

```
Outlook → landing zone → transformação → PostgreSQL → pasta processados
```

- **Idempotente:** rodar duas vezes não duplica dados (nome do arquivo + SHA-256).
- **Falha visível:** coluna faltando/nova ou tipo inválido aborta só aquele arquivo, que fica na landing zone para nova tentativa.
- **Originais preservados:** os arquivos nunca são alterados, só movidos para `PROCESSADOS` após a carga.

## Requisitos

- Windows com Outlook clássico configurado
- Python 3.13
- PostgreSQL

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
├── config/schema.json        de-para das colunas (Excel → tabela)
├── sql/001_estrutura.sql     criação de schemas, tabelas e view
├── src/
│   ├── config.py             .env, pastas, conexão
│   ├── outlook_extraction.py Outlook → landing zone
│   ├── normalizar.py         nomes e tipos das colunas
│   ├── loader.py             landing zone → Postgres
│   └── main.py               orquestrador
├── .env.example
└── requirements.txt
```

## Modelo de dados

- `etl.controle_cargas` — uma linha por arquivo carregado (hash único, data de envio).
- `raw.base_tasy` — dados de todas as cargas, ligados por `load_id`.
- `raw.vw_base_tasy_atual` — retrato mais recente (último e-mail enviado).

## Problemas comuns

- **Erro COM com o Outlook:** script e Outlook precisam rodar no mesmo nível de privilégio (ambos sem admin).
- **"Estrutura mudou":** o relatório de origem mudou. Compare com `config/schema.json` e, se preciso, ajuste o SQL.

## Privacidade

A base contém dados sensíveis de pacientes e colaboradores. Landing zone e banco
devem ter acesso restrito. Nunca versionar dados reais nem o `.env`.
