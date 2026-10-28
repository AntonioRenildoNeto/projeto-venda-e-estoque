"""Cópia de segurança do banco: python scripts/backup.py [pasta_destino]

Usa a API de backup do SQLite, então a cópia é consistente mesmo com o sistema rodando.
Mantém as 14 cópias mais recentes.
"""
import os
import sqlite3
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.environ.get("DADOS_DIR") or os.path.join(RAIZ, "dados")
MANTER = 14


def main(destino=None):
    origem = os.path.join(DADOS, "sistema.db")
    if not os.path.exists(origem):
        print(f"Banco não encontrado: {origem}")
        return 1
    destino = destino or os.path.join(DADOS, "backups")
    os.makedirs(destino, exist_ok=True)
    arquivo = os.path.join(destino, f"sistema_{datetime.now():%Y%m%d_%H%M%S}.db")
    fonte, copia = sqlite3.connect(origem), sqlite3.connect(arquivo)
    try:
        fonte.backup(copia)
    finally:
        copia.close()
        fonte.close()
    print(f"Backup criado: {arquivo}")
    antigos = sorted(f for f in os.listdir(destino) if f.startswith("sistema_") and f.endswith(".db"))[:-MANTER]
    for nome in antigos:
        os.remove(os.path.join(destino, nome))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
