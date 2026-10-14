# Carga: lê os arquivos da landing zone e grava no Postgres com controle de versões.
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg

from src.config import FORMATO_DATA_ARQUIVO, LANDING_ZONE, PROCESSADOS, conectar
from src.normalizar import preparar_df

TAMANHO_DATA = len(datetime(2000, 1, 1).strftime(FORMATO_DATA_ARQUIVO))  # "dd-mm-aaaa_HH-MM"


# Hash do arquivo, para evitar carga duplicada
def calcular_hash(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# Data de envio do e-mail, lida de volta do nome do arquivo
def extrair_data_envio(caminho: Path) -> datetime:
    return datetime.strptime(caminho.name[:TAMANHO_DATA], FORMATO_DATA_ARQUIVO)


# Carrega um arquivo. Retorna False se ele já tinha sido carregado.
def ingest(caminho: Path, conn: psycopg.Connection) -> bool:
    hash_arquivo = calcular_hash(caminho)

    # checagem rápida antes de ler o Excel (a proteção definitiva é o UNIQUE + ON CONFLICT)
    if conn.execute("SELECT 1 FROM etl.controle_cargas WHERE hash_arquivo = %s", (hash_arquivo,)).fetchone():
        print(f"[PULADO] Já importado anteriormente: {caminho.name}")
        return False

    df = preparar_df(pd.read_excel(caminho, engine="calamine"))

    # registro de controle + dados numa transação só
    with conn.transaction():
        linha = conn.execute(
            """
            INSERT INTO etl.controle_cargas (nome_arquivo, hash_arquivo, data_envio, qtd_linhas)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (hash_arquivo) DO NOTHING
            RETURNING load_id
            """,
            (caminho.name, hash_arquivo, extrair_data_envio(caminho), len(df)),
        ).fetchone()

        if linha is None:
            print(f"[PULADO] Já importado anteriormente: {caminho.name}")
            return False

        #  ------ rever esse bloco  ------ #
        load_id = linha[0]
        colunas_sql = ", ".join(["load_id", *df.columns])
        with conn.cursor() as cur, cur.copy(f"COPY raw.base_tasy ({colunas_sql}) FROM STDIN") as copy:
            for registro in df.itertuples(index=False, name=None):
                copy.write_row((load_id, *registro))

    print(f"[OK] {caminho.name} → load_id {load_id} ({len(df)} linhas)")
    return True


# Carrega tudo o que está na landing zone
def carregar_todos() -> None:
    arquivos = []
    for arq in LANDING_ZONE.iterdir():
        if not arq.is_file() or arq.suffix.lower() not in {".xlsx", ".xls"} or arq.name.startswith("_tmp_"):
            continue
        try:
            extrair_data_envio(arq)
        except ValueError:
            print(f"[AVISO] Nome fora do padrão '{FORMATO_DATA_ARQUIVO}_...', ignorado: {arq.name}")
            continue
        arquivos.append(arq)

    if not arquivos:
        print("Carga: nenhum arquivo na landing zone")
        return

    # ordem cronológica de envio, para os load_id seguirem a ordem das versões
    arquivos.sort(key=extrair_data_envio)

    carregados = pulados = erros = 0
    with conectar() as conn:
        for arq in arquivos:
            try:
                if ingest(arq, conn):
                    carregados += 1
                else:
                    pulados += 1
                arq.replace(PROCESSADOS / arq.name)   # já está no banco: sai da landing zone
            except Exception as erro:
                # fica na landing zone para nova tentativa na próxima execução
                erros += 1
                print(f"[ERRO] {arq.name}: {erro}")

    print(f"\nCarga: {carregados} carregado(s), {pulados} já existente(s), {erros} com erro")


if __name__ == "__main__":
    carregar_todos()
