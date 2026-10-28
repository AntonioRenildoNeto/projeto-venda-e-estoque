"""Consulta de estoque e histórico de movimentos."""
from flask import Blueprint, flash, redirect, render_template, url_for

from .comum import requer, servicos

bp = Blueprint("estoque", __name__, url_prefix="/estoque")


@bp.route("")
@requer("consultar_estoque")
def listar():
    return render_template("estoque.html", itens=servicos().estoque.listar())


@bp.route("/<int:produto_id>/movimentos")
@requer("consultar_estoque")
def movimentos(produto_id):
    s = servicos()
    produto = s.produtos.buscar_por_id(produto_id)
    if produto is None:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("estoque.listar"))
    historico = list(reversed(s.estoque.movimentos.listar_por_produto(produto_id)))
    return render_template(
        "movimentos.html", produto=produto, movimentos=historico,
        quantidade=s.estoque.consultar_quantidade(produto_id),
    )
