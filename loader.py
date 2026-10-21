
import pandas as pd
import hashlib
import time
from datetime import datetime 

from config import FORMATO_DATA_ARQUIVO, STAGING, PROCESSADOS, conectar
from normalizar import preparar_df

# tamanho da data no nome do arquivo
TAMANHO_DATA = len(datetime(2000, 1, 1). strftime(FORMATO_DATA_ARQUIVO))

# hashing do arquivo
def calcular_hash(caminho):
    conteudo = caminho.read_bytes()
    h = hashlib.sha256(conteudo)
    return h.hexdigest()

# retorna a data de envio do email do nome do arquivo
def extrair_data_envio(caminho):
    texto_data = caminho.name[:TAMANHO_DATA]
    return datetime.strptime(texto_data, FORMATO_DATA_ARQUIVO)

# Ingestão do arquivo no BD. Retorna False se já foi carregado antes
def ingest(caminho, conn):
    hash_arquivo = calcular_hash(caminho)

    # verifica se o arquivo já existe no BD pelo hash
    exist = conn.execute(
        "SELECT 1 FROM etl.controle_cargas WHERE hash_arquivo = %s", (hash_arquivo,)
    ).fetchone()
    if exist:
        print(f"[PULADO] arquivo já importado anteriormente: {caminho.name}")
        return False

    # cronometragem dos processos
    inicio  = time.time()
    df = pd.read_excel(caminho, engine="calamine")
    tempo_leitura = time.time() - inicio

    inicio = time.time()
    df = preparar_df(df)
    tempo_transformacao = time.time() - inicio

    inicio = time.time()
    
    # load da tabela de controle do BD
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

        # se já houver um arquivo com o mesmo {hash_arquivo}
        if linha is None:
            print(f"[PULADO] arquivo já importado anteriormente: {caminho.name}")
            return False

        # criacao e insercao da PK(load_id) no DataFrame
        # ------rever esse trecho - sql injec  ------ #
        load_id = linha[0]
        df.insert(0, "load_id", load_id)
        
        colunas_sql = ", ".join(df.columns)
    
        # comando para copiar todas as linhas de uma vez
        comando_copy = f"COPY raw.base_3352 ({colunas_sql}) FROM STDIN"
        registros = df.itertuples(index=False, name=None)
        
        # Transação: se uma linha falha nada na carga fica gravado 
        with conn.cursor() as cur, cur.copy(comando_copy) as copy:
            for registro in registros:
                copy.write_row(registro)

        tempo_gravacao = time.time() - inicio

        print(f"[OK] {caminho.name} -> load_id {load_id} ({len(df)} linhas)")
        print(f"      leitura: {tempo_leitura:.1f}s | transformacao: {tempo_transformacao:.1f}s | gravacao: {tempo_gravacao:.1f}s")
        return True
    
# Load dos arquivos na Staging -> BD -> Processados
def carregar_todos():
    arquivos =[]
    for arq in STAGING.iterdir():      
        if not arq.is_file():
            continue
        if arq.suffix.lower() not in [".xlsx", ".xls"]:
            continue
        if arq.name.startswith("_temp_"):
            continue

        # extrai a data do arquivo 
        try:
            extrair_data_envio(arq)
        except ValueError:
            print(f"[AVISO] Nome fora do padrão: '{FORMATO_DATA_ARQUIVO}_...', ignorado: {arq.name}")
            continue

        arquivos.append(arq)

    if len(arquivos) == 0:
        print("Carga: nenhum arquivo na pasta Staging")
        return

    # ordena pela data de envio
    arquivos.sort(key=extrair_data_envio)

    carregados = 0
    pulados = 0
    erros = 0

    # ingestao e contabilizacao   
    with conectar() as conn:
        for arq in arquivos:
            # chama a função de ingestão
            try:
                if ingest(arq, conn):
                    carregados += 1
                else:
                    pulados += 1

                # move arquivo para pasta Processados
                arq.replace(PROCESSADOS / arq.name)

            # printa erros e >>deixa arquivos com erro na >>STAGING<<< 
            except Exception as erro:
                erros += 1
                print(f"[ERRO] {arq.name} : {erro}")

    print(f"\nCarga: {carregados} carregado(s), {pulados} pulado(s), {erros} com erro")

if __name__ == "__main__":
    carregar_todos()
