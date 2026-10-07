# ETL Tasy — Totais de Contas

Pipeline ETL que extrai bases de dados .xlsx do Outlook (clássico),
preserva o arquivo original em uma landing zone local e
carrega os dados em um banco PostgreSQL, com controle de versionamento.

O relatório é um retrato diário da movimentação e atualização
das contas, no caso, do Faturamento da OncologiaD'or: a mesma conta reaparece nos arquivos dos dias
seguintes com informações: etapas, status, dentre outros, possivelmente diferentes. O histórico existe para
permitir a análise dessa evolução ao longo do tempo.

---

## Visão geral

```
Outlook → validação do anexo → landing zone → controle de duplicidade
→ leitura e transformação → PostgreSQL → log e auditoria
```

Características principais:

- **Idempotente.** Executar duas vezes seguidas não gera dado duplicado.
- **Janela dinâmica.** Se a máquina ficar dias desligada, a busca se estica
  sozinha e recupera o atraso, sem furo no histórico.
- **Falha alta e visível.** Qualquer inconsistência aborta a execução com
  código de saída diferente de zero, em vez de carregar dado errado em
  silêncio.
- **Arquivos originais preservados.** A landing zone nunca é alterada.

---

## Requisitos

- Windows com Outlook clássico instalado e perfil configurado
- Python 3.13
- PostgreSQL local

---

## Instalação

```bash
git clone <url-do-repositorio>
cd etl_tasy

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Dependências: `pywin32`, `openpyxl`, `pandas`, `psycopg[binary]`,
`python-dotenv`.

---

## Estrutura do projeto

```
etl_tasy/
├── config/
│   └── colunas_referencia.json   cabeçalho esperado do arquivo
├── sql/
│   └── ddl.sql                   criação das tabelas
├── src/                          módulos do pipeline
├── landing/AAAA/MM/              anexos originais (não versionado)
├── logs/                         log rotativo (não versionado)
├── .env                          configuração local (não versionado)
├── .env.example
└── requirements.txt

---

## Modelo de dados

Schema: `tasy`

| Tabela | Papel |
|---|---|
| `stg_totais_contas` | Espelho do arquivo em texto, truncada a cada carga |
| `fato_totais_contas` | Histórico tipado e acumulativo |
| `ctrl_arquivo_processado` | Auditoria e trava de duplicidade |
| `ctrl_excecao_mensagem` | Válvula de escape manual |

---

## Controle de duplicidade

São duas travas feitas em momentos distintos:

1. **`InternetMessageID`** — consultado antes de baixar o anexo. Evita
   reprocessar os mesmos e-mails diariamente por causa da sobreposição da
   janela de busca.
2. **SHA-256 do anexo** — calculado apenas para e-mails novos. Cobre o reenvio
   do mesmo relatório em mensagem diferente.

---

## Códigos de saída

| Código | Significado |
|---|---|
| `0` | Sucesso (inclusive quando não há e-mail novo) |
| `1` | Falha de ambiente ou configuração |
| `2` | Falha de validação (anexo, cabeçalho, unicidade, conversão) |
| `3` | Falha de banco de dados |

---

## Solução de problemas

**Erro de conexão COM com o Outlook**
Verifique se o script e o Outlook rodam no mesmo nível de privilégio. Script
como administrador + Outlook como usuário comum sempre falha.

**`pywin32` não instala**
Confirme que o ambiente virtual usa Python 3.13. Versões muito recentes do
Python podem não ter wheel disponível.

**Nenhum e-mail encontrado**
Verifique `OUTLOOK_FOLDER_PATH`. Se houver regra do Outlook movendo a mensagem
para uma subpasta, a Caixa de Entrada estará vazia do alvo.

**Pipeline abortando sempre no mesmo e-mail**
Registre o `InternetMessageID` da mensagem em `ctrl_excecao_mensagem` com o
motivo. A próxima execução passa por cima dela.

**Erro de cabeçalho divergente**
O relatório de origem mudou de estrutura. Compare o cabeçalho recebido com
`config/colunas_referencia.json` antes de atualizar a referência — a mudança
pode exigir alteração no modelo de dados.

---

## Privacidade

A base contém informações sensíveis de pacientes, colaboradores da rede, médicos e etc.
Portanto, a pasta da landing zone e o banco devem ter acesso restrito ao
usuário do pipeline.

Este repositório não deve conter dados reais, arquivos da landing zone, dumps
do banco nem o arquivo `.env`.
