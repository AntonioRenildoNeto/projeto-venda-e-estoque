"""Classe Compra: reposição de produtos (entra no estoque)."""
from datetime import datetime

from ..erros import ErroNaoEncontrado, ErroValidacao
from ..estoque.estoque import Estoque
from ..produtos.funcoes import PRECO_MAXIMO
from ..produtos.produto import Produto
from .funcoes import anexar_itens, calcular_subtotal, validar_itens


class Compra:
    def __init__(self, banco):
        self.banco = banco
        self.produtos = Produto(banco)
        self.estoque = Estoque(banco)

    def calcular_total(self, itens):
        """Soma o valor de todos os itens comprados."""
        return round(sum(calcular_subtotal(i) for i in itens), 2)

    def registrar(self, itens, usuario_id):
        """Grava uma nova compra e aumenta o estoque.

        Cada item é um dict: {"produto_id", "quantidade", "preco_unitario"}.
        """
        itens = validar_itens(itens)
        completos = []
        for item in itens:
            produto = self.produtos.buscar_por_id(item["produto_id"])
            if produto is None:
                raise ErroNaoEncontrado("Só é possível comprar produtos cadastrados.")
            try:
                preco = float(str(item.get("preco_unitario")).replace(",", "."))
            except (TypeError, ValueError):
                raise ErroValidacao("Preço unitário inválido.")
            if not preco > 0:
                raise ErroValidacao("O preço unitário deve ser maior que zero.")
            if preco > PRECO_MAXIMO:
                raise ErroValidacao("O preço unitário máximo é R$ 1.000.000,00.")
            completos.append({**item, "preco_unitario": round(preco, 2), "produto_nome": produto["nome"]})

        total = self.calcular_total(completos)
        with self.banco.transacao():
            compra_id = self.banco.executar(
                "INSERT INTO compras (usuario_id, total, data) VALUES (?, ?, ?)",
                (usuario_id, total, datetime.now().isoformat(timespec="seconds")),
            ).lastrowid
            for item in completos:
                self.banco.executar(
                    "INSERT INTO itens_compra (compra_id, produto_id, produto_nome, quantidade, preco_unitario) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (compra_id, item["produto_id"], item["produto_nome"], item["quantidade"], item["preco_unitario"]),
                )
                self.estoque.atualizar(item["produto_id"], item["quantidade"], f"compra #{compra_id}")
        return self.buscar_por_id(compra_id)

    def buscar_por_id(self, compra_id):
        compra = self.banco.consultar_um("SELECT * FROM compras WHERE id = ?", (compra_id,))
        if compra:
            compra["itens"] = self.banco.consultar(
                "SELECT * FROM itens_compra WHERE compra_id = ?", (compra_id,)
            )
        return compra

    def listar(self, limite=None, deslocamento=0):
        """Consulta as compras feitas (da mais recente para a mais antiga), com paginação opcional."""
        sql, parametros = "SELECT * FROM compras ORDER BY id DESC", ()
        if limite is not None:
            sql, parametros = sql + " LIMIT ? OFFSET ?", (limite, deslocamento)
        return anexar_itens(self.banco, self.banco.consultar(sql, parametros), "itens_compra", "compra_id")

    def contar(self):
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM compras")["n"]
