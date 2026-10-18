# Ordem de execução do ETL: Outlook -> landing zone -> Postgres.
from loader import carregar_todos
from outlook_extraction import extract

if __name__ == "__main__":
    extract()
    carregar_todos()
