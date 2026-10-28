"""Compras (entrada) e vendas (saída)."""
from flask import Blueprint, render_template, request

from .comum import itens_do_formulario, paginar, requer, servicos, tentar

bp = Blueprint("operacoes", __name__)


@bp.route("/compras")
@requer("comprar")
def compras():
    s = servicos()
    pag = paginar(s.compras.contar())
    return render_template(
        "compras.html", compras=s.compras.listar(pag["limite"], pag["deslocamento"]),
        produtos=s.produtos.listar(), pag=pag,
    )


@bp.route("/compras", methods=["POST"])
@requer("comprar")
def registrar_compra():
    itens = itens_do_formulario(["produto_id", "quantidade", "preco_unitario"])
    return tentar(
        lambda: servicos().compras.registrar(itens, request.usuario["id"]),
        "Compra registrada e estoque atualizado.", "operacoes.compras",
        auditar=("compra_registrada", f"{len(itens)} item(ns)"),
    )


@bp.route("/vendas")
@requer("vender")
def vendas():
    s = servicos()
    selecionado = request.args.get("produto", type=int)  # vem do botão "Vender" do catálogo
    pag = paginar(s.vendas.contar())
    return render_template(
        "vendas.html", vendas=s.vendas.listar(pag["limite"], pag["deslocamento"]),
        estoque=s.estoque.listar(), selecionado=selecionado, pag=pag,
    )


@bp.route("/vendas", methods=["POST"])
@requer("vender")
def registrar_venda():
    itens = itens_do_formulario(["produto_id", "quantidade"])
    return tentar(
        lambda: servicos().vendas.registrar(itens, request.usuario["id"]),
        "Venda registrada e estoque atualizado.", "operacoes.vendas",
        auditar=("venda_registrada", f"{len(itens)} item(ns)"),
    )


@bp.route("/vendas/<int:venda_id>/cancelar", methods=["POST"])
@requer("vender")
def cancelar_venda(venda_id):
    return tentar(
        lambda: servicos().vendas.cancelar(venda_id), "Venda cancelada e estoque devolvido.", "operacoes.vendas",
        auditar=("venda_cancelada", f"#{venda_id}"),
    )
