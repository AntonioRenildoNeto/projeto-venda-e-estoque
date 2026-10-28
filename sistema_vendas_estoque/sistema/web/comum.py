"""Ferramentas compartilhadas pelas rotas: acesso aos serviços, proteção de rotas e paginação."""
from functools import wraps
from itertools import zip_longest
from math import ceil

from flask import current_app, flash, redirect, render_template, request, session, url_for

from ..erros import ErroSistema
from ..usuarios.perfil import Perfil

POR_PAGINA = 15
# Páginas que o usuário pode abrir mesmo estando obrigado a trocar a senha.
ENDPOINTS_LIVRES_NA_TROCA = {"conta.senha", "auth.logout"}


def servicos():
    return current_app.extensions["sistema"]


def requer(acao=None):
    """Exige login válido e, se informada, a permissão ``acao`` do perfil."""
    def decorador(funcao):
        @wraps(funcao)
        def interna(*args, **kwargs):
            s = servicos()
            usuario = s.sessao.validar_token(session.get("token"))
            if usuario is None:
                session.clear()
                flash("Faça login para continuar.", "erro")
                return redirect(url_for("auth.login"))
            if usuario["trocar_senha"] and request.endpoint not in ENDPOINTS_LIVRES_NA_TROCA:
                flash("Por segurança, defina uma nova senha antes de continuar.", "erro")
                return redirect(url_for("conta.senha"))
            if acao and not Perfil(usuario["perfil"]).tem_permissao(acao):
                return render_template(
                    "acesso_negado.html", usuario=usuario,
                    mensagem="Acesso negado: essa ação é permitida apenas para o Admin.",
                ), 403
            request.usuario = usuario
            return funcao(*args, **kwargs)
        return interna
    return decorador


def tentar(operacao, sucesso, destino, auditar=None, **args_destino):
    """Executa a operação; mostra a mensagem de sucesso ou de erro e redireciona.

    ``auditar`` = (ação, detalhe) é gravado na auditoria só se a operação der certo.
    """
    try:
        operacao()
        flash(sucesso, "ok")
        if auditar:
            servicos().auditoria.registrar(request.usuario["id"], *auditar)
        return redirect(url_for(destino, **args_destino))
    except ErroSistema as erro:
        flash(str(erro), "erro")
        return redirect(url_for(destino, **args_destino))


def paginar(total, por_pagina=POR_PAGINA):
    """Calcula a página pedida em ?pagina=N, sem deixar passar do limite."""
    paginas = max(1, ceil(total / por_pagina))
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), paginas)
    return {"pagina": pagina, "paginas": paginas, "limite": por_pagina,
            "deslocamento": (pagina - 1) * por_pagina, "total": total}


def itens_do_formulario(campos):
    """Lê as linhas de itens do formulário (campos repetidos) e ignora linhas totalmente em branco."""
    colunas = [request.form.getlist(c) for c in campos]
    itens = []
    for valores in zip_longest(*colunas, fillvalue=""):
        item = dict(zip(campos, valores, strict=True))
        if any(str(v).strip() for v in valores):
            itens.append(item)
    # Nada preenchido: devolve uma linha vazia, para a validação mostrar a mensagem certa.
    return itens or [{c: "" for c in campos}]
