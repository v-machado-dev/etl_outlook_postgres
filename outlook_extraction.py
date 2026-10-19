# Extracao: baixa os anexos da pasta Base_3352 do Outlook para a Staging

import os
import re
from pathlib import Path
from datetime import datetime, timedelta

import win32com.client

from config import FORMATO_DATA_ARQUIVO, STAGING, PROCESSADOS

# nome da pasta criada no outlook para receber somente a base
PASTA_OUTLOOK = "Base_3352"
EXTENSOES_ACEITAS = [".xls", ".xlsx"]

# variaveis do Outlook
OL_ITEM_EMAIL = 43
OUTLOOK_INBOX = 6

# # so olha os emails dos ultimos X dias;  None -> olha a pasta inteira
DIAS_BUSCA = None

# proteção para caracteres inválidos
def nome_seguro(nome_base):
    return re.sub(r'[<>:/\\|?*]', "-", nome_base).strip()


# descobre a extensão real do arquivo pelos primeiros bytes
def formato_real(caminho):
    with open(caminho, "rb") as f:
        formato = f.read(8) 
        if formato.startswith(b"PK\x03\x04"):
            return ".xlsx"
        if formato.startswith(b"\xD0\xCF\x11\xE0"):
            return ".xls"
        else:
            return None

# verifica se o arquivo ja foi baixado antes
def arquivo_ja_baixado(nome_base, arquivos_existentes):
    for ext in EXTENSOES_ACEITAS:
        if  nome_base + ext in arquivos_existentes:
            return True
    return False 

# conecta ao outlook, baixa e salva o arquivo na pasta staging
def extract():
    # api Outlook
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    
    # conecta a subpasta criada >>>préviamente<<<
    pasta = outlook.GetDefaultFolder(OUTLOOK_INBOX).Folders(PASTA_OUTLOOK)

    # mais recentes primeiro
    itens = pasta.Items
    itens.Sort("[ReceivedTime]", True)

    # lista todos os arquivos existentes 
    arquivos_existentes = set(os.listdir(STAGING)).union(set(os.listdir(PROCESSADOS)))

    # variaveis para "quantos dias olhar no retrovisor"
    data_limite = None
    if DIAS_BUSCA is not None:
        data_limite = datetime.now() - timedelta(days=DIAS_BUSCA)

    # ignora objetos cuja classe não é o "tipo email"
    salvos = 0
    for email in itens:
        try:
            if email.Class != OL_ITEM_EMAIL:   
                continue

            # analisa apenas os arquivos que estão dentro do intervalo de dias estabelecido 
            if data_limite is not None:
                data_recebida = email.ReceivedTime.replace(tzinfo=None)
                if data_recebida < data_limite:
                    continue     

            # salva a data e o nome originais
            data_envio = email.SentOn.strftime(FORMATO_DATA_ARQUIVO)
            for anexo in email.Attachments:
                nome_original = anexo.Filename

                # pula arquivos não xls ou xlsx
                if Path(nome_original).suffix.lower() not in EXTENSOES_ACEITAS:
                    continue

                # recorta apenas o "prefixo"(caule) do nome do anexo
                nome_base = f"{data_envio}_{nome_seguro(Path(nome_original).stem)}"
                
                # confere se já existe
                if arquivo_ja_baixado(nome_base, arquivos_existentes):
                    continue

                # salva temporariamente para conferir o formato pelos primeiros bytes         
                temp = STAGING / f"_temp_{nome_seguro(nome_original)}"
                anexo.SaveAsFile(str(temp))

                # cancela o download se a extensão for inválida
                ext_real = formato_real(temp)
                if ext_real is None:
                    print(f"[AVISO] formato não recohecido: {nome_original} | {email.Subject}")
                    temp.unlink()
                    continue

                nome_final = nome_base + ext_real

                # salva arquivo validado na staging
                temp.replace(STAGING / nome_final)

                # contabiliza no conjunto(set)
                arquivos_existentes.add(nome_final)
                salvos += 1
                print(f"[OK] {nome_final}")
        
        except Exception as erro:
            print(f"[ERRO] Não foi possível ler o email {erro}")

    print(f"\n Extração: {salvos} arquivos(s) novo(s) na Staging")
    return salvos


if __name__ == "__main__":
    extract() 
