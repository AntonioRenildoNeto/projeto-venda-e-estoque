"""Produtos e catálogo."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..erros import ErroSistema
from .comum import requer, servicos, tentar

bp = Blueprint("produtos", __name__)


@bp.route("/produtos")
@requer("consultar_estoque")
def listar():
    s = servicos()
    busca = request.args.get("busca", "").strip()
    lista = s.produtos.buscar_por_nome(busca) if busca else s.produtos.listar()
    return render_template("produtos.html", produtos=lista, tipos=s.tipos.listar(), busca=busca)


@bp.route("/produtos", methods=["POST"])
@requer("cadastrar_produto")
def cadastrar():
    f = request.form
    return tentar(
        lambda: servicos().produtos.cadastrar(f.get("nome"), f.get("tipo"), f.get("preco"), f.get("estoque_minimo")),
        "Produto cadastrado com sucesso.", "produtos.listar",
        auditar=("produto_cadastrado", (f.get("nome") or "").strip()[:80]),
    )


@bp.route("/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
@requer("editar_produto")
def editar(produto_id):
    s = servicos()
    produto = s.produtos.buscar_por_id(produto_id)
    if produto is None:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("produtos.listar"))
    if request.method == "POST":
        f = request.form
        try:
            s.produtos.editar(produto_id, f.get("nome"), f.get("tipo"), f.get("preco"), f.get("estoque_minimo"))
        except ErroSistema as erro:
            flash(str(erro), "erro")
            produto = {**produto, "nome": f.get("nome"), "tipo": f.get("tipo"),
                       "preco": f.get("preco"), "estoque_minimo": f.get("estoque_minimo")}
        else:
            s.auditoria.registrar(request.usuario["id"], "produto_editado", f"#{produto_id}")
            flash("Produto atualizado com sucesso.", "ok")
            return redirect(url_for("produtos.listar"))
    return render_template("produto_editar.html", produto=produto, tipos=s.tipos.listar())


@bp.route("/produtos/<int:produto_id>/remover", methods=["POST"])
@requer("remover_produto")
def remover(produto_id):
    return tentar(
        lambda: servicos().produtos.remover(produto_id), "Produto removido com sucesso.", "produtos.listar",
        auditar=("produto_removido", f"#{produto_id}"),
    )


@bp.route("/catalogo")
@requer("consultar_estoque")
def catalogo():
    s = servicos()
    todos = s.estoque.listar()
    tipos = s.tipos.listar()
    tipo = request.args.get("tipo", "").strip()
    if tipo not in tipos:
        tipo = ""
    disponiveis = [e for e in todos if e["quantidade"] > 0 and (not tipo or e["tipo"] == tipo)]
    sem_estoque = len([e for e in todos if e["quantidade"] == 0])
    return render_template("catalogo.html", produtos=disponiveis, tipos=tipos, tipo=tipo, sem_estoque=sem_estoque)
