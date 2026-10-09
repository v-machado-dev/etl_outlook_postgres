# configuração e seccionamento das colunas do schema 
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((BASE_DIR / "config" / "schema.json").read_text(encoding="utf-8"))

DICTIONARIES = SCHEMA["colunas"]
NOME_ORIGEM = [c["origem"] for c in DICTIONARIES]
NOME_DESTINO = [c["destino"] for c in DICTIONARIES]


# Formato da data no nome dos arquivos da landing zone.
# A extração usa para GRAVAR o nome e a carga usa para LER a data de volta
FORMATO_DATA_NOME = "%d-%m-%Y_%H-%M"

