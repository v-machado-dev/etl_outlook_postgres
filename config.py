# Configuração central do projeto: lê o .env, cria as pastas e conecta ao banco.
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ_PROJETO / ".env")


# Lê uma variável do .env e falha se ela não existir.
def obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável '{nome}' não definida no .env")
    return valor

# Pastas
STAGING = RAIZ_PROJETO / obrigatoria("STAGING")
PROCESSADOS = RAIZ_PROJETO / obrigatoria("PROCESSADOS")
STAGING.mkdir(parents=True, exist_ok=True)
PROCESSADOS.mkdir(parents=True, exist_ok=True)


# Formato da data no nome dos arquivos
FORMATO_DATA_ARQUIVO = "%d-%m-%Y_%H-%M"

# De para das colunas: nome no Excel -> nome na tabela
SCHEMA = json.loads((RAIZ_PROJETO / "config" / "schema.json").read_text(encoding="utf-8"))
DE_PARA_COLUNAS = {c["origem"]: c["destino"] for c in SCHEMA["colunas"]}

# Banco de dados
PG = {
    "user": obrigatoria("PG_USER"),
    "password": obrigatoria("PG_PASSWORD"),
    "host": obrigatoria("PG_HOST"),
    "port": int(obrigatoria("PG_PORT")),
    "dbname": obrigatoria("PG_DB"),
}

# autocommit=True: cada `with conn.transaction()` é independente,
# então um arquivo com erro não derruba os demais.
def conectar() -> psycopg.Connection:
    return psycopg.connect(**PG, autocommit=True)
