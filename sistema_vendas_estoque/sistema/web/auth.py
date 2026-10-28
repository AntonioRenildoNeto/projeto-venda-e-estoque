"""Login e logout."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from ..erros import ErroSistema
from .comum import servicos

bp = Blueprint("auth", __name__)


def _chaves(email):
    return f"email:{email.strip().lower()}", f"ip:{request.remote_addr}"


@bp.route("/login", methods=["GET", "POST"])
def login():
    s = servicos()
    if request.method == "POST":
        email = request.form.get("email") or ""
        chave_email, chave_ip = _chaves(email)
        espera = max(s.limite_email.segundos_restantes(chave_email), s.limite_ip.segundos_restantes(chave_ip))
        if espera:
            minutos = -(-espera // 60)
            flash(f"Muitas tentativas de login. Tente de novo em cerca de {minutos} minuto(s).", "erro")
            return render_template("login.html"), 429
        try:
            token = s.autenticador.login(email, request.form.get("senha"))
        except ErroSistema as erro:
            s.limite_email.registrar_falha(chave_email)
            s.limite_ip.registrar_falha(chave_ip)
            s.auditoria.registrar(None, "login_falhou", email.strip().lower()[:120])
            current_app.logger.warning("Login falhou para %s", email.strip().lower()[:120])
            flash(str(erro), "erro")
            return render_template("login.html")
        s.limite_email.limpar(chave_email)
        session.clear()
        session["token"] = token
        dono = s.banco.consultar_um("SELECT usuario_id FROM tokens WHERE token = ?", (token,))
        s.auditoria.registrar(dono["usuario_id"] if dono else None, "login", "")
        return redirect(url_for("painel.inicio"))
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    s = servicos()
    token = session.pop("token", None)
    if token:
        usuario = s.sessao.validar_token(token)
        s.autenticador.logout(token)
        if usuario:
            s.auditoria.registrar(usuario["id"], "logout", "")
    session.clear()
    flash("Você saiu do sistema.", "ok")
    return redirect(url_for("auth.login"))
