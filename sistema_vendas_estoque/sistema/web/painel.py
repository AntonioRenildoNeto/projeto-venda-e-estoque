"""Página inicial (painel) e conta do usuário."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..erros import ErroSistema
from .comum import requer, servicos

bp = Blueprint("painel", __name__)
conta = Blueprint("conta", __name__, url_prefix="/conta")


@bp.route("/")
@requer()
def inicio():
    return render_template("inicio.html", resumo=servicos().relatorios.painel())


@conta.route("/senha", methods=["GET", "POST"])
@requer()
def senha():
    s = servicos()
    if request.method == "POST":
        f = request.form
        if f.get("senha_nova") != f.get("senha_confirmacao"):
            flash("A confirmação não é igual à nova senha.", "erro")
        else:
            try:
                s.usuarios.alterar_senha(request.usuario["id"], f.get("senha_atual"), f.get("senha_nova"))
            except ErroSistema as erro:
                flash(str(erro), "erro")
            else:
                s.auditoria.registrar(request.usuario["id"], "senha_alterada", "")
                session.clear()  # primeiro limpa; a mensagem vem depois para não ser apagada
                flash("Senha alterada. Entre novamente com a nova senha.", "ok")
                return redirect(url_for("auth.login"))
    return render_template("senha.html")
