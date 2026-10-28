"""Registro de auditoria: quem fez o quê e quando."""
from datetime import datetime


class Auditoria:
    def __init__(self, banco):
        self.banco = banco

    def registrar(self, usuario_id, acao, detalhe=""):
        self.banco.executar(
            "INSERT INTO auditoria (data, usuario_id, acao, detalhe) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), usuario_id, acao, detalhe),
        )

    def listar(self, limite=100, deslocamento=0):
        return self.banco.consultar(
            "SELECT * FROM auditoria ORDER BY id DESC LIMIT ? OFFSET ?", (limite, deslocamento)
        )

    def contar(self):
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM auditoria")["n"]
