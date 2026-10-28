"""Classe Venda: saída de produtos para o cliente (sai do estoque)."""
from collections import defaultdict
from datetime import datetime

from ..erros import ErroNaoEncontrado, ErroValidacao, EstoqueInsuficiente
from ..estoque.estoque import Estoque
from ..produtos.produto import Produto
from .funcoes import anexar_itens, calcular_subtotal, validar_itens


class Venda:
    def __init__(self, banco):
        self.banco = banco
        self.produtos = Produto(banco)
        self.estoque = Estoque(banco)

    def calcular_total(self, itens):
        """Soma o valor dos itens da venda."""
        return round(sum(calcular_subtotal(i) for i in itens), 2)

    def registrar(self, itens, usuario_id):
        """Grava a venda e diminui o estoque.

        Cada item é um dict: {"produto_id", "quantidade"}; o preço é o do cadastro.
        A venda é bloqueada se não houver unidades suficientes.
        """
        itens = validar_itens(itens)
        completos = []
        pedido_por_produto = defaultdict(int)
        for item in itens:
            produto = self.produtos.buscar_por_id(item["produto_id"])
            if produto is None:
                raise ErroNaoEncontrado("Só é possível vender produtos cadastrados.")
            pedido_por_produto[produto["id"]] += item["quantidade"]
            completos.append({
                "produto_id": produto["id"],
                "produto_nome": produto["nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": produto["preco"],
            })

        total = self.calcular_total(completos)
        with self.banco.transacao():
            # A conferência do estoque fica DENTRO da transação (que já reserva o banco):
            # duas vendas ao mesmo tempo não conseguem passar pela checagem juntas.
            for produto_id, quantidade in pedido_por_produto.items():
                if not self.estoque.verificar_disponibilidade(produto_id, quantidade):
                    nome = self.produtos.buscar_por_id(produto_id)["nome"]
                    disponivel = self.estoque.consultar_quantidade(produto_id)
                    raise EstoqueInsuficiente(
                        f"Estoque insuficiente de {nome}: há {disponivel} unidade(s), pedido de {quantidade}."
                    )
            venda_id = self.banco.executar(
                "INSERT INTO vendas (usuario_id, total, status, data) VALUES (?, ?, 'concluida', ?)",
                (usuario_id, total, datetime.now().isoformat(timespec="seconds")),
            ).lastrowid
            for item in completos:
                self.banco.executar(
                    "INSERT INTO itens_venda (venda_id, produto_id, produto_nome, quantidade, preco_unitario) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (venda_id, item["produto_id"], item["produto_nome"], item["quantidade"], item["preco_unitario"]),
                )
                self.estoque.atualizar(item["produto_id"], -item["quantidade"], f"venda #{venda_id}")
        return self.buscar_por_id(venda_id)

    def cancelar(self, venda_id):
        """Desfaz uma venda já registrada e devolve as unidades ao estoque."""
        venda = self.buscar_por_id(venda_id)
        if venda is None:
            raise ErroNaoEncontrado("Venda não encontrada.")
        if venda["status"] == "cancelada":
            raise ErroValidacao("Essa venda já foi cancelada.")
        with self.banco.transacao():
            self.banco.executar("UPDATE vendas SET status = 'cancelada' WHERE id = ?", (venda_id,))
            for item in venda["itens"]:
                try:
                    self.estoque.atualizar(item["produto_id"], item["quantidade"], f"cancelamento da venda #{venda_id}")
                except ErroNaoEncontrado:
                    # O produto foi removido depois da venda: não há estoque para devolver.
                    pass
        return self.buscar_por_id(venda_id)

    def buscar_por_id(self, venda_id):
        venda = self.banco.consultar_um("SELECT * FROM vendas WHERE id = ?", (venda_id,))
        if venda:
            venda["itens"] = self.banco.consultar(
                "SELECT * FROM itens_venda WHERE venda_id = ?", (venda_id,)
            )
        return venda

    def listar(self, limite=None, deslocamento=0):
        """Vendas da mais recente para a mais antiga, com paginação opcional."""
        sql, parametros = "SELECT * FROM vendas ORDER BY id DESC", ()
        if limite is not None:
            sql, parametros = sql + " LIMIT ? OFFSET ?", (limite, deslocamento)
        return anexar_itens(self.banco, self.banco.consultar(sql, parametros), "itens_venda", "venda_id")

    def contar(self, status=None):
        if status:
            return self.banco.consultar_um("SELECT COUNT(*) AS n FROM vendas WHERE status = ?", (status,))["n"]
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM vendas")["n"]
