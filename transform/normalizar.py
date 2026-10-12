# Transformação das colunas em seus respectivos tipos de dado
import pandas as pd
from src.schema import COLUNAS, NOME_DESTINO


# Segmentação de cada coluna
COLUNAS_DATA = {
    "dt_etapa": "%d/%m/%Y %H:%M:%S",
    "data_entrada": None, 
    "data_entrega": None,
    "data_titulo":  None, 
    "data_nf": None,
} 
COLUNAS_NUMERICAS = ["vl_conta"]
COLUNAS_TEXTO = []
for c in NOME_DESTINO:
    if c not in [*COLUNAS_DATA, *COLUNAS_NUMERICAS]:
        COLUNAS_TEXTO.append(c)


# retirar o '.0' e converte valores para texto 
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

    # falha se a planilha base mudar de estrutura (coluna nova, removida ou renomeada)
    if faltando or sobrando:
        raise ValueError(f"Estrutura mudou. Faltando: {faltando} | Novas: {sobrando}")

    df = df.rename(columns=COLUNAS)

    for col in COLUNAS_DATA.items():
        df[col] = pd.to_datetime(df[col], errors="raise").dt.date

    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="raise").round(2)

    for col in COLUNAS_TEXTO:
        df[col] = df[col].map(para_texto)

    # Tratamento para vazios - NULL, NaN, NaT e <NA> são convertidos para None
    return df.astype(object).where(df.notna(), None)


if __name__ == "__main__":
    preparar_df()
