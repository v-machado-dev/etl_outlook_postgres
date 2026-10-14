# Extração: baixa os anexos da pasta Base_3352 do Outlook para a landing zone.
import re
from pathlib import Path

import win32com.client

from src.config import FORMATO_DATA_ARQUIVO, LANDING_ZONE, PROCESSADOS

PASTA_OUTLOOK = "Base_3352"
EXTENSOES_ACEITAS = {".xls", ".xlsx"}
OL_MAIL_ITEM = 43      # tipo "e-mail" no Outlook
OL_CAIXA_ENTRADA = 6


# Troca caracteres inválidos em nome de arquivo
def nome_seguro(nome: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", nome).strip()


# Formato real do arquivo, pelos primeiros bytes
def formato_real(caminho: Path) -> str | None:
    with open(caminho, "rb") as f:
        assinatura = f.read(8)
    if assinatura.startswith(b"PK\x03\x04"):
        return ".xlsx"
    if assinatura.startswith(b"\xD0\xCF\x11\xE0"):
        return ".xls"
    return None


# Salva na landing zone os anexos ainda não baixados. Retorna quantos salvou.
def extrair() -> int:
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    pasta = outlook.GetDefaultFolder(OL_CAIXA_ENTRADA).Folders(PASTA_OUTLOOK)

    itens = pasta.Items
    itens.Sort("[ReceivedTime]", True)  # mais recentes primeiro

    salvos = 0
    for msg in itens:
        if msg.Class != OL_MAIL_ITEM:   # ignora convites, relatórios de entrega etc.
            continue

        data_envio = msg.SentOn.strftime(FORMATO_DATA_ARQUIVO)

        for anexo in msg.Attachments:
            nome_original = anexo.FileName
            if Path(nome_original).suffix.lower() not in EXTENSOES_ACEITAS:
                continue

            # salva com nome temporário para inspecionar o conteúdo
            temp = LANDING_ZONE / f"_tmp_{nome_seguro(nome_original)}"
            anexo.SaveAsFile(str(temp))

            ext_real = formato_real(temp)
            if ext_real is None:
                print(f"[AVISO] Formato não reconhecido: {nome_original} | {msg.Subject}")
                temp.unlink()
                continue

            nome_final = f"{data_envio}_{nome_seguro(Path(nome_original).stem)}{ext_real}"

            # já baixado antes (aguardando carga ou já processado)
            if (LANDING_ZONE / nome_final).exists() or (PROCESSADOS / nome_final).exists():
                temp.unlink()
                continue

            temp.replace(LANDING_ZONE / nome_final)
            salvos += 1
            print(f"[OK] {nome_final}")

    print(f"\nExtração: {salvos} arquivo(s) novo(s) na landing zone")
    return salvos


if __name__ == "__main__":
    extrair()
