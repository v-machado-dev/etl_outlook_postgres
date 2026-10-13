# Transformação: renomeia as colunas e converte cada uma para o tipo da tabela.
import pandas as pd

from config import DE_PARA_COLUNAS

COLUNAS_DATA = ["dt_etapa", "data_entrada", "data_entrega", "data_titulo", "data_nf"]
COLUNAS_NUMERICAS = ["vl_conta"]
COLUNAS_TEXTO = [c for c in DE_PARA_COLUNAS.values() if c not in COLUNAS_DATA + COLUNAS_NUMERICAS]


# Converte para texto, tirando o '.0' de números inteiros lidos como float
def para_texto(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    texto = str(valor).strip()
    return texto or None


def preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    faltando = set(DE_PARA_COLUNAS) - set(df.columns)
    sobrando = set(df.columns) - set(DE_PARA_COLUNAS)

    # falha se a planilha mudar de estrutura (coluna nova, removida ou renomeada)
    if faltando or sobrando:
        raise ValueError(f"Estrutura mudou. Faltando: {faltando} | Novas: {sobrando}")

    df = df.rename(columns=DE_PARA_COLUNAS)

    for col in COLUNAS_DATA:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="raise").dt.date

    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="raise").round(2)

    for col in COLUNAS_TEXTO:
        df[col] = df[col].map(para_texto)

    # NaN, NaT e <NA> viram None (NULL no banco)
    return df.astype(object).where(df.notna(), None)
