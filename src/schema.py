# configuração e seccionamento das colunas do schema 
import json
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((RAIZ_PROJETO / "config" / "schema.json").read_text(encoding="utf-8"))

DEFINICOES_COLUNAS = SCHEMA["colunas"]

DE_PARA_COLUNAS = {c["origem"]: c["destino"] for c in DEFINICOES_COLUNAS}

# Formato da data no nome dos arquivos da landing zone.
# A extração usa para GRAVAR o nome e a carga usa para LER a data de volta
FORMATO_DATA_ARQUIVO = "%d-%m-%Y_%H-%M"

