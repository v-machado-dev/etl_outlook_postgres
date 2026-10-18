# Transformação dos dados: troca o nome das colunas e acerta o tipo de cada uma
import pandas as pd

from config import DE_PARA_COLUNAS

COLUNAS_DATA = ["dt_etapa", "data_entrada", "data_entrega", "data_titulo", "data_nf"]
COLUNAS_NUMERICAS = ["vl_conta"]

COLUNAS_TEXTO = []
for coluna in DE_PARA_COLUNAS.values():
    if coluna not in COLUNAS_DATA and coluna not in COLUNAS_NUMERICAS:
        COLUNAS_TEXTO.append(coluna)

# transforma colunas em texto,
# quando a coluna tem vazios o pandas pode passar numeros
#  para float então tiro o '.0'

def colunas_para_texto(coluna):
    texto = coluna.astype("string")

    if pd.api.types.is_float_dtype(coluna):
        inteiro = coluna.notna() & (coluna % 1 == 0)
        texto[inteiro] = coluna[inteiro].astype("Int64").astype("string")

    texto = texto.str.strip()
    texto = texto.mask(texto == "")
    return texto

# trata a tabela a ser carregada conforme cada um de seus tipos de dado
def preparar_df(df):
    # verifica se há diferença entre
    colunas_esperadas = set(DE_PARA_COLUNAS.keys())
    colunas_planilha = set(df.columns)

    faltando = colunas_esperadas - colunas_planilha
    sobrando = colunas_planilha - colunas_esperadas

    if len(faltando) > 0 or len(sobrando) > 0:
        raise ValueError(f"Estrutura mudou. Faltando: {faltando} | Novas: {sobrando} ")

    df = df.rename(columns=DE_PARA_COLUNAS)

    # trata linhas totalmente vazias
    df = df.dropna(how="all")

    for col in COLUNAS_DATA:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="raise")
        df[col] = df[col].dt.date

    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="raise")
        df[col] = df[col].round(2)

    for col in COLUNAS_TEXTO:
        df[col] = colunas_para_texto(df[col])

    # troca NAN / NAT / NA por None
    df = df.astype(object)
    df = df.where(df.notna(), None)
    return df
      