"""Configuração central do projeto: lê o .env e expõe pastas e conexões."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()  # carrega as variáveis na memória

"""Lê uma variável do .env e falha com mensagem clara se ela não existir."""
def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável '{nome}' não definida no .env")
    return valor


# Pastas
LANDING_ZONE = Path(_obrigatoria("LANDING_ZONE"))
PROCESSADOS = Path(_obrigatoria("PROCESSADOS"))
LANDING_ZONE.mkdir(parents=True, exist_ok=True)
PROCESSADOS.mkdir(parents=True, exist_ok=True)

# Formato da data no nome dos arquivos da landing zone.
# A extração usa para GRAVAR o nome e a carga usa para LER a data de volta,
# por isso fica aqui, num lugar só. Não mude sem renomear os arquivos existentes.
FORMATO_DATA_NOME = "%d-%m-%Y_%H-%M"

# Banco de dados
PG = {
    "user": _obrigatoria("PG_USER"),
    "password": _obrigatoria("PG_PASSWORD"),
    "host": _obrigatoria("PG_HOST"),
    "port": int(_obrigatoria("PG_PORT")),
    "dbname": _obrigatoria("PG_DB"),
}

# Engine postgres
engine = create_engine(
    URL.create(
        drivername="postgresql+psycopg",
        username=PG["user"],
        password=PG["password"],
        host=PG["host"],
        port=PG["port"],
        database=PG["dbname"],
    )
)

"""autocommit=True faz cada `with conn.transaction():' ser uma transação
independente -> se um arquivo falhar, só ele é desfeito"""
    
def conectar() -> psycopg.Connection:
    return psycopg.connect(**PG, autocommit=True)
