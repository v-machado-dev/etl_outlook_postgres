# Extração: baixa os anexos da pasta Base_Tasy do Outlook para a landing zone.
import re
from pathlib import Path

import win32com.client

from src.config import FORMATO_DATA_NOME, LANDING_ZONE, PROCESSADOS

PASTA_OUTLOOK = "Base_Tasy"
EXTENSOES_ACEITAS = {".xls", ".xlsx"}
OL_MAIL_ITEM = 43  # tipo "e-mail" no Outlook (ignora convites, relatórios de entrega etc.)


# Segurança contra nomes inválidos
def nome_seguro(nome: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", nome).strip()


# Identificador do formato real do arquivo (pelos primeiros bytes, não pela extensão)
def formato_real(caminho: Path) -> str | None:
    with open(caminho, "rb") as f:
        assinatura = f.read(8)
    if assinatura.startswith(b"PK\x03\x04"):          # ZIP → .xlsx
        return ".xlsx"
    if assinatura.startswith(b"\xD0\xCF\x11\xE0"):    # OLE → .xls antigo
        return ".xls"
    return None


def extrair() -> int:
    """Salva na landing zone os anexos ainda não baixados. Retorna quantos salvou."""
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    pasta = outlook.GetDefaultFolder(6).Folders(PASTA_OUTLOOK)  # 6 = Caixa de Entrada

    itens = pasta.Items
    itens.Sort("[ReceivedTime]", True)  # mais recentes primeiro

    salvos = 0
    for msg in itens:
        if msg.Class != OL_MAIL_ITEM:
            continue

        data_envio = msg.SentOn.strftime(FORMATO_DATA_NOME)

        for anexo in msg.Attachments:
            nome_original = anexo.FileName
            stem = Path(nome_original).stem
            ext = Path(nome_original).suffix.lower()

            if ext not in EXTENSOES_ACEITAS:
                continue  # ignora formatos indesejados

            # salva primeiro com nome temporário para poder inspecionar o conteúdo
            temp = LANDING_ZONE / f"_tmp_{nome_seguro(nome_original)}"
            anexo.SaveAsFile(str(temp))

            ext_real = formato_real(temp)
            if ext_real is None:
                print(f"[AVISO] Formato não reconhecido: {nome_original} | {msg.Subject}")
                temp.unlink()
                continue

            nome_final = f"{data_envio}_{nome_seguro(stem)}{ext_real}"

            # já baixado antes? (aguardando carga na landing zone ou já carregado em processados)
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
