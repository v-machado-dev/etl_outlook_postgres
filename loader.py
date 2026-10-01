"""Carga: lê os arquivos da landing zone e grava no Postgres com controle de versões."""
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg

from config import FORMATO_DATA_NOME, LANDING_ZONE, PROCESSADOS, conectar

# nomeação das colunas do BD
COLUNAS = {
    "Conta": "conta",
    "Setor Atend": "setor_atend",
    "Atendimento": "atendimento",
    "Doc. Convênio": "doc_convenio",
    "Médico": "medico",
    "Etapa": "etapa",
    "Dt Etapa": "dt_etapa",
    "Observação Etapa": "observacao_etapa",
    "Tipo Obs Conta": "tipo_obs_conta",
    "Observação Conta": "observacao_conta",
    "Convenio": "convenio",
    "Classificacao": "classificacao",
    "Status": "status",
    "Conta Enviada": "conta_enviada",
    "Data Entrada": "data_entrada",
    "Prontuario": "prontuario",
    "Paciente": "paciente",
    "Estab atend": "estab_atend",
    "Data Entrega": "data_entrega",
    "Status protocolo": "status_protocolo",
    "Vl conta": "vl_conta",
    "Data Titulo": "data_titulo",
    "Nr Titulo": "nr_titulo",
    "Nr Protocolo": "nr_protocolo",
    "Desc Protocolo": "desc_protocolo",
    "Nr Guia": "nr_guia",
    "Senha": "senha",
    "Usuario Convenio": "usuario_convenio",
    "Plano": "plano",
    "Categoria": "categoria",
    "Estab conta": "estab_conta",
    "Status.1": "status_2",
    "Data NF": "data_nf",
    "Usuário Etapa": "usuario_etapa",
    "Nº Protocolo Documento": "nr_protocolo_documento",
}

# Tipos de cada coluna (precisam bater com o CREATE TABLE em sql/001_estrutura.sql)
COLUNAS_INTEIRAS = [
    "conta", "atendimento", "prontuario",
    "nr_titulo", "nr_protocolo", "nr_protocolo_documento",
]
COLUNAS_DATA = ["data_entrada", "data_entrega", "data_titulo", "data_nf"]  # já vêm como data do Excel
FORMATO_dt_etapa = "%d/%m/%Y %H:%M:%S"                          
COLUNAS_TEXTO = [
    c for c in COLUNAS.values()
    if c not in COLUNAS_INTEIRAS + COLUNAS_DATA + ["dt_etapa", "vl_conta"]
]


# Hashing do arquivo (impressão digital para evitar carga duplicada)
def calcular_hash(caminho: Path) -> str:
    h = hashlib.sha256()

    with open(caminho, "rb") as f:
        def ler_proximo_bloco():
            return f.read(65536)     # 64 KB por vez

        for bloco in iter(ler_proximo_bloco, b""):
            h.update(bloco)

    return h.hexdigest()


# Data de envio do e-mail, lida de volta do nome do arquivo
def extrair_data_envio(caminho: Path) -> datetime:
    tamanho = len(datetime(2000, 1, 1).strftime(FORMATO_DATA_NOME))  # formato "dd-mm-aaaa_HH-MM"
    return datetime.strptime(caminho.name[:tamanho], FORMATO_DATA_NOME)

"""Converte para texto sem o '.0' que números lidos do Excel costumam trazer."""
def _para_texto(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    texto = str(valor).strip()
    return texto or None


# Transformação: nomes e tipos no formato da tabela
def preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    # falha logo se a planilha mudar de estrutura (coluna nova, removida ou renomeada)
    faltando = set(COLUNAS) - set(df.columns)
    sobrando = set(df.columns) - set(COLUNAS)
    if faltando or sobrando:
        raise ValueError(f"Estrutura mudou. Faltando: {faltando} | Novas: {sobrando}")

    df = df.rename(columns=COLUNAS)[list(COLUNAS.values())].copy()

    df["dt_etapa"] = pd.to_datetime(df["dt_etapa"], format=FORMATO_dt_etapa, errors="raise")
    for col in COLUNAS_DATA:
        df[col] = pd.to_datetime(df[col], errors="raise")

    # "Int64" (I maiúsculo) = inteiro que aceita vazio; falha se houver valor não inteiro
    for col in COLUNAS_INTEIRAS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("Int64")

    df["vl_conta"] = pd.to_numeric(df["vl_conta"], errors="raise").round(2)

    for col in COLUNAS_TEXTO:
        df[col] = df[col].map(_para_texto)

    # o banco entende None como NULL; NaN, NaT e <NA> precisam ser convertidos
    return df.astype(object).where(df.notna(), None)


# Carregamento de um arquivo
def ingest(caminho: Path, conn: psycopg.Connection) -> bool:
    """Carrega um arquivo. Retorna True se carregou, False se já tinha sido carregado."""
    hash_arquivo = calcular_hash(caminho)

    # checagem rápida antes de gastar tempo lendo o Excel
    # (a proteção definitiva é o UNIQUE + ON CONFLICT logo abaixo)
    if conn.execute(
        "SELECT 1 FROM etl.controle_cargas WHERE hash_arquivo = %s", (hash_arquivo,)
    ).fetchone():
        print(f"[PULADO] Já importado anteriormente: {caminho.name}")
        return False

    data_envio = extrair_data_envio(caminho)
    df = preparar_df(pd.read_excel(caminho, engine="calamine"))

    # registro de controle + dados numa transação só: tudo ou nada
    with conn.transaction():
        linha = conn.execute(
            """
            INSERT INTO etl.controle_cargas
                (nome_arquivo, hash_arquivo, data_envio, qtd_linhas)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (hash_arquivo) DO NOTHING
            RETURNING load_id
            """,
            (caminho.name, hash_arquivo, data_envio, len(df)),
        ).fetchone()

        if linha is None:
            print(f"[PULADO] Já importado anteriormente: {caminho.name}")
            return False

        load_id = linha[0]

        colunas_sql = ", ".join(["load_id", *df.columns])
        with conn.cursor() as cur:
            with cur.copy(f"COPY raw.base_tasy ({colunas_sql}) FROM STDIN") as copy:
                for registro in df.itertuples(index=False, name=None):
                    copy.write_row((load_id, *registro))

    print(f"[OK] {caminho.name} → load_id {load_id} ({len(df)} linhas)")
    return True


# Carregamento de tudo o que está na landing zone
def carregar_todos() -> None:
    arquivos = []
    for arq in LANDING_ZONE.iterdir():
        if not arq.is_file() or arq.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        if arq.name.startswith("_tmp_"):
            continue  # sobra de uma extração interrompida
        try:
            extrair_data_envio(arq)
        except ValueError:
            print(f"[AVISO] Nome fora do padrão '{FORMATO_DATA_NOME}_...', ignorado: {arq.name}")
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
                # já está no banco (agora ou antes): sai da landing zone
                arq.replace(PROCESSADOS / arq.name)
            except Exception as erro:
                # o arquivo fica na landing zone para nova tentativa na próxima execução
                erros += 1
                print(f"[ERRO] {arq.name}: {erro}")

    print(f"\nCarga: {carregados} carregado(s), {pulados} já existente(s), {erros} com erro")


if __name__ == "__main__":
    carregar_todos()
