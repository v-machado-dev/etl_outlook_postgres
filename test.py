import win32com.client
from datetime import datetime


OUTLOOK_INBOX = 6
OL_ITEM_EMAIL = 43

PASTA_OUTLOOK = "Base_3352"

# Mostra apenas mensagens recebidas a partir desta data
DATA_INICIAL = datetime(2026, 10, 15)

def analisar_pasta(pasta, nome_pasta):
    print("\n" + "=" * 100)
    print(f"[PASTA] {nome_pasta}")
    print(f"[CAMINHO] {pasta.FolderPath}")
    print(f"[TOTAL] {pasta.Items.Count}")
    print("=" * 100)

    itens = pasta.Items
    itens.Sort("[ReceivedTime]", True)

    encontrados = 0

    for item in itens:
        try:
            if item.Class != OL_ITEM_EMAIL:
                continue

            data_recebida = item.ReceivedTime.replace(tzinfo=None)

            if data_recebida < DATA_INICIAL:
                break

            encontrados += 1

            print(
                f"[EMAIL] recebido={item.ReceivedTime} | "
                f"assunto={item.Subject} | "
                f"anexos={item.Attachments.Count}"
            )

        except Exception as erro:
            print(f"[ERRO] {erro}")
    print(f"[RESULTADO] E-mails encontrados desde {DATA_INICIAL}: {encontrados}")


def testar_localizacao():

    outlook = win32com.client.Dispatch("Outlook.Application").GetNameSpace("MAPI")

    inbox = outlook.GetDefaultFolder(OUTLOOK_INBOX)
    pasta_base = inbox.Folders(PASTA_OUTLOOK)

    analisar_pasta(inbox, "Caixa de Entrada")

    analisar_pasta(pasta_base, PASTA_OUTLOOK)

if __name__ == "__main__":
    testar_localizacao()


