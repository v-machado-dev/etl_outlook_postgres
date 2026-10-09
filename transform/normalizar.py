# Transformação das colunas em seus respectivos tipos de dado

import pandas as pd
from src.schema import COLUNAS, FORMATO_DATA_NOME, NOME_DESTINO, NOME_ORIGEM

 
FORMATO_data_nf = "%d/%m/%Y %H:%M:%S"
# tratar data_nf (remover %Hora%Min%Seg)
def tratar_data_nf(df: pd.DataFrame) -> pd.DataFrame:
    df['data_nf'] = pd.to_datetime(df['data_nf'], format=FORMATO_data_nf).dt.date
    return df


# Segmentação de cada coluna em grupos
COLUNAS_DATA = ["dt_etapa", "data_entrada", "data_entrega", "data_titulo", "data_nf"]  
COLUNAS_NUMERICAS = ["vl_conta"]
COLUNAS_TEXTO = []
for c in COLUNAS.values():
    if c not in COLUNAS_DATA + COLUNAS_NUMERICAS:
        COLUNAS_TEXTO.append(c)

 
# retira o '.0' e converte valores para texto 
def para_texto(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    texto = str(valor).strip()
    return texto or None


# Transformação: nomes e tipos no formato da tabela
def preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    faltando = set(COLUNAS) - set(df.columns)   
    sobrando = set(df.columns) - set(COLUNAS)

    # falha se a planilha mudar de estrutura (coluna nova, removida ou renomeada)
    if faltando or sobrando:
        raise ValueError(f"Estrutura mudou. Faltando: {faltando} | Novas: {sobrando}")

    for col in COLUNAS_DATA:
        df[col] = pd.to_datetime(df[col], errors="raise")

    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="raise").round(2)

    for col in COLUNAS_TEXTO:
        df[col] = df[col].map(para_texto)

    # Tratamento para vazios 
    # NULL, NaN, NaT e <NA> são convertidos para None
    return df.astype(object).where(df.notna(), None)
