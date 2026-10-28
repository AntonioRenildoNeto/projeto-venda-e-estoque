"""Cadastro e remoção de usuários (apenas Admin)."""
from flask import Blueprint, render_template, request

from .comum import requer, servicos, tentar

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("", methods=["GET"])
@requer("cadastrar_usuario")
def listar():
    return render_template("usuarios.html", usuarios=servicos().usuarios.listar())


@bp.route("", methods=["POST"])
@requer("cadastrar_usuario")
def cadastrar():
    f = request.form
    return tentar(
        lambda: servicos().usuarios.cadastrar(
            f.get("id"), f.get("nome_completo"), f.get("email"),
            f.get("telefone"), f.get("senha"), f.get("perfil", "comum"),
        ),
        "Usuário cadastrado com sucesso.", "usuarios.listar",
        auditar=("usuario_cadastrado", f"{(f.get('id') or '').strip()} ({f.get('perfil', 'comum')})"),
    )


@bp.route("/<id>/remover", methods=["POST"])
@requer("remover_usuario")
def remover(id):
    return tentar(
        lambda: servicos().usuarios.remover(id, executado_por=request.usuario["id"]),
        "Usuário removido com sucesso.", "usuarios.listar",
        auditar=("usuario_removido", id),
    )
