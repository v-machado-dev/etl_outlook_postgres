
import pandas as pd
import hashlib
import time
from datetime import datetime 

from config import FORMATO_DATA_ARQUIVO, LANDING_ZONE, PROCESSADOS, conectar
from normalizar import preparar_df

# tamanho da data no nome do arquivo
TAMANHO_DATA = len(datetime(2000, 1, 1). strftime(FORMATO_DATA_ARQUIVO))

# hashing das colunas
def calcular_hash(caminho):
    conteudo = caminho.read_bytes()
    h = hashlib.sha256(conteudo)
    return h.hexdigest()

# retorna a data de envio do email do nome do arquivo
def extrair_data_envio(caminho):
    texto_data = caminho.name[:TAMANHO_DATA]
    return datetime.strptime(texto_data, FORMATO_DATA_ARQUIVO)

# ingestão do arquivo no bd -> False se já foi carregado antes
def ingest(caminho, conn):
    hash_arquivo = calcular_hash(caminho)

    # verifica se o arquivo já existe no BD
    exist = conn.execute(
        "SELECT 1 FROM etl.controle_cargas WHERE hash_arquivo = %s", (hash_arquivo,)
    ).fetchone()
    if exist:
        print(f"[PULADO] arquivo já importado anteriormente: {caminho.name}")
        return False

    inicio  = time.time()
    df = pd.read_excel(caminho, engine="calamine")
    tempo_leitura = time.time() - inicio

    inicio = time.time()
    df = preparar_df(df)
    tempo_transformacao = time.time() - inicio

    inicio = time.time()

    with conn.transaction():
        linha = conn.execute(
        """
        INSERT INTO etl.controle_cargas(nome_arquivo, hash_arquivo, data_envio, qtd_linhas)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (hash_arquivo) DO NOTHING
        RETURNING load_id
        """,
        (caminho.name, hash_arquivo, extrair_data_envio(caminho), len(df)),
        ).fetchone()

        if linha is None:
            print(f"[PULADO] arquivo já importado anteriormente: {caminho.name}")
            return False

        load_id = linha[0]

        # insere o load_id nos dados
        df.insert(0, "load_id", load_id)
        colunas_sql = ", ".join(df.columns)

        with conn.cursor() as cur:
            comando_copy = (f"COPY raw.base_tasy ({colunas_sql}) FROM STDIN")

            with cur.copy(comando_copy) as copy:
                for registro in df.itertuples(index=False, name=None):
                    copy.write_row(registro)

        tempo_gravacao = time.time() - inicio

        print(f"[OK] {caminho.name} -> load_id {load_id} ({len(df)} linhas)")
        print(f"      leitura: {tempo_leitura:.1f}s | transformacao: {tempo_transformacao:.1f}s | gravacao: {tempo_gravacao:.1f}s")
        return True

def carregar_todos():
    arquivos =[]
    for arq in LANDING_ZONE.iterdir():
        if not arq.is_file():
            continue
        if arq.suffix.lower() not in [".xlsx", ".xls"]:
            continue
        
        try:
            extrair_data_envio(arq)
        except ValueError:
            print(f"[AVISO] Nome fora do padrão: '{FORMATO_DATA_ARQUIVO}_...', ignorado: {arq.name}")
            continue

        arquivos.append(arq)

    if len(arquivos) == 0:
        print("Carga: nenhum arquivo na landing zone")
        return

    # ordena pela data de envio
    arquivos.sort(key=extrair_data_envio)

    carregados = 0
    pulados = 0
    erros = 0

    with conectar() as conn:
        for arq in arquivos:
            try:
                if ingest(arq,conn):
                    carregados += 1
                else:
                    pulados += 1

                # se já constar no banco move para a pasta de processados
                arq.replace(PROCESSADOS / arq.name)
            # deixa o arquivo que não foi carregado na landing_zone 
            except Exception as erro:
                erros += 1
                print(f"[ERRO] {arq.name} : {erro}")

    print(f"\nCarga: {carregados} carregado(s), {pulados} pulado(s), {erros} com erro")

if __name__ == "__main__":
    carregar_todos()





