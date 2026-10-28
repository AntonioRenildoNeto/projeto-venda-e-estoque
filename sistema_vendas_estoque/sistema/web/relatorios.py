"""Relatórios, exportação em CSV e auditoria (apenas Admin)."""
from datetime import date

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from ..erros import ErroValidacao
from ..relatorios import converter_data
from .comum import paginar, requer, servicos

bp = Blueprint("relatorios", __name__)


def _periodo():
    """Lê ?inicio= e ?fim= (padrão: do dia 1 do mês até hoje)."""
    hoje = date.today()
    inicio = converter_data(request.args.get("inicio"), hoje.replace(day=1))
    fim = converter_data(request.args.get("fim"), hoje)
    return inicio, fim


@bp.route("/relatorios")
@requer("ver_relatorios")
def vendas():
    try:
        inicio, fim = _periodo()
        dados = servicos().relatorios.vendas_do_periodo(inicio, fim)
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        hoje = date.today()
        inicio, fim, dados = hoje.replace(day=1), hoje, None
    return render_template("relatorios.html", inicio=inicio, fim=fim, dados=dados)


def _csv(conteudo, nome):
    return Response(conteudo, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@bp.route("/relatorios/vendas.csv")
@requer("ver_relatorios")
def vendas_csv():
    try:
        inicio, fim = _periodo()
        return _csv(servicos().relatorios.csv_vendas(inicio, fim), f"vendas_{inicio}_{fim}.csv")
    except ErroValidacao as erro:
        flash(str(erro), "erro")
        return redirect(url_for("relatorios.vendas"))


@bp.route("/relatorios/estoque.csv")
@requer("ver_relatorios")
def estoque_csv():
    return _csv(servicos().relatorios.csv_estoque(), f"estoque_{date.today()}.csv")


@bp.route("/auditoria")
@requer("ver_auditoria")
def auditoria():
    s = servicos()
    pag = paginar(s.auditoria.contar(), por_pagina=30)
    return render_template("auditoria.html", registros=s.auditoria.listar(pag["limite"], pag["deslocamento"]), pag=pag)
