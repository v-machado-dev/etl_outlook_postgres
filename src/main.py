# Ordem de exeução do o ETL  Outlook -> landing zone -> Postgres.
from src.loader import carregar_todos
from src.outlook_extraction import extrair

if __name__ == "__main__":
    extrair()
    carregar_todos()
