"""Executa as suítes de teste.

Uso:
    python executar_testes.py                 (roda tudo)
    python executar_testes.py unitarios
    python executar_testes.py integracao
    python executar_testes.py sistema
    python executar_testes.py aceitacao
    python executar_testes.py regressao       (unitários + integração + regressão)
    python executar_testes.py unitarios integracao   (pode combinar)
"""
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.abspath(__file__))
SUITES = {
    "unitarios": ["unitarios"],
    "integracao": ["integracao"],
    "sistema": ["sistema"],
    "aceitacao": ["aceitacao"],
    # O teste de regressão reexecuta o que já existia, além dos casos próprios.
    "regressao": ["unitarios", "integracao", "regressao"],
    "todos": ["unitarios", "integracao", "sistema", "aceitacao", "regressao"],
}


def main(argumentos):
    nomes = argumentos or ["todos"]
    pastas = []
    for nome in nomes:
        if nome not in SUITES:
            print(f"Suíte desconhecida: {nome}. Opções: {', '.join(SUITES)}")
            return 2
        pastas += [p for p in SUITES[nome] if p not in pastas]

    suite = unittest.TestSuite()
    for pasta in pastas:
        suite.addTests(unittest.TestLoader().discover(os.path.join(RAIZ, "tests", pasta), top_level_dir=RAIZ))
    resultado = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.path.insert(0, RAIZ)
    sys.exit(main(sys.argv[1:]))
