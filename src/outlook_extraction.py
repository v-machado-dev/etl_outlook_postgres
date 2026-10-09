# Extração: baixa os anexos da pasta Base_3352 do Outlook para a landing zone.
import re
from pathlib import Path
import win32com.client

from config.config import FORMATO_DATA_NOME, LANDING_ZONE, PROCESSADOS

PASTA_OUTLOOK = "Base_3352"
EXTENSOES_ACEITAS = {".xls", ".xlsx"}
OL_MAIL_ITEM = 43  


# segurança contra caracteres inválidos
def nome_seguro(nome: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", nome).strip()


# identificador do formato real do arquivo (pelos primeiros bytes)
def formato_real(caminho: Path) -> str | None:
    with open(caminho, "rb") as f:
        assinatura = f.read(8)
    if assinatura.startswith(b"PK\x03\x04"):          
        return ".xlsx"
    if assinatura.startswith(b"\xD0\xCF\x11\xE0"):    
        return ".xls"
    return None

# salva na landing zone os anexos ainda não baixados. Retorna quantos salvou.
def extrair() -> int:

    # chama a API do outlook
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # 6 = Caixa de Entrada e acessa subpasta criada préviamente no outlook "Base_3352"
    pasta = outlook.GetDefaultFolder(6).Folders(PASTA_OUTLOOK)  

    itens = pasta.Items
    itens.Sort("[ReceivedTime]", True)  # mais recentes primeiro

    salvos = 0
    for msg in itens:
        if msg.Class != OL_MAIL_ITEM:    # tipo "e-mail" no Outlook (ignora convites, relatórios de entrega etc.)
            continue

        data_envio = msg.SentOn.strftime(FORMATO_DATA_NOME)

        # separação do nome original em radical e sufixo
        for anexo in msg.Attachments:
            nome_original = anexo.FileName
            stem = Path(nome_original).stem
            ext = Path(nome_original).suffix.lower()

            # ignora formatos indesejados
            if ext not in EXTENSOES_ACEITAS:
                continue  

            # salva primeiro com nome temporário para poder inspecionar o conteúdo
            temp = LANDING_ZONE / f"_tmp_{nome_seguro(nome_original)}"
            anexo.SaveAsFile(str(temp))

            # deleta o arquivo caso extensão não seja xlsx ou xls
            ext_real = formato_real(temp)
            if ext_real is None:
                print(f"[AVISO] Formato não reconhecido: {nome_original} | {msg.Subject}")
                temp.unlink()
                continue
             
            nome_final = f"{data_envio}_{nome_seguro(stem)}{ext_real}"

            #  Deleta se já foi carregado antes - 
            # (aguardando na landing zone / já carregado em processados)
            if (LANDING_ZONE / nome_final).exists() or (PROCESSADOS / nome_final).exists():
                temp.unlink()
                continue
        
            temp.rename(LANDING_ZONE / nome_final)
            salvos += 1
            print(f"[OK] {nome_final}")

    print(f"\nExtração: {salvos} arquivo(s) novo(s) na landing zone")
    return salvos


if __name__ == "__main__":
    extrair()
