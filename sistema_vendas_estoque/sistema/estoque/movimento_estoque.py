"""Classe MovimentoEstoque: histórico de entradas e saídas."""
from datetime import datetime


class MovimentoEstoque:
    def __init__(self, banco):
        self.banco = banco

    def registrar(self, produto_id, quantidade, motivo=""):
        """Anota uma movimentação (positiva = entrada, negativa = saída)."""
        tipo = "entrada" if quantidade > 0 else "saida"
        self.banco.executar(
            "INSERT INTO movimentos_estoque (produto_id, quantidade, tipo, motivo, data) VALUES (?, ?, ?, ?, ?)",
            (produto_id, quantidade, tipo, motivo, datetime.now().isoformat(timespec="seconds")),
        )

    def listar_por_produto(self, produto_id):
        """Mostra o histórico de movimentações de um produto."""
        return self.banco.consultar(
            "SELECT * FROM movimentos_estoque WHERE produto_id = ? ORDER BY id", (produto_id,)
        )
