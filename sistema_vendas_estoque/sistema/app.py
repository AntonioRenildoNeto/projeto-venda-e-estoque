"""Aplicação web (Flask) do Sistema de Vendas e Estoque."""
import hmac
import logging
import os
import secrets
from types import SimpleNamespace

from flask import Flask, render_template, request, session

from .auditoria import Auditoria
from .autenticacao.autenticador import Autenticador
from .autenticacao.sessao import Sessao
from .banco import Banco
from .compra_venda.compra import Compra
from .compra_venda.venda import Venda
from .estoque.estoque import Estoque
from .inicializacao import criar_admin_padrao
from .limitador import LimitadorLogin
from .produtos.produto import Produto
from .produtos.tipo_produto import TipoProduto
from .relatorios import Relatorios
from .usuarios.perfil import Perfil
from .usuarios.usuario import Usuario
from .web import auth, estoque, operacoes, painel, produtos, relatorios, usuarios

ROTULOS_STATUS = {"concluida": "Concluída", "cancelada": "Cancelada"}
ROTULOS_ACAO = {
    "login": "Login", "logout": "Logout", "login_falhou": "Login recusado",
    "senha_alterada": "Senha alterada",
    "usuario_cadastrado": "Usuário cadastrado", "usuario_removido": "Usuário removido",
    "produto_cadastrado": "Produto cadastrado", "produto_editado": "Produto editado",
    "produto_removido": "Produto removido",
    "compra_registrada": "Compra registrada", "venda_registrada": "Venda registrada",
    "venda_cancelada": "Venda cancelada",
}
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
)


def _formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def criar_app(caminho_banco=":memory:", duracao_sessao=60 * 60, secret_key=None,
              exigir_troca_senha=False, csrf=True):
    """Monta a aplicação.

    - ``secret_key``: se não vier por parâmetro nem pela variável SECRET_KEY, uma chave
      aleatória é criada (as sessões então deixam de valer quando o programa reinicia).
    - ``exigir_troca_senha``: obriga o Admin criado automaticamente a trocar a senha no 1º login.
    - ``csrf``: proteção contra requisições forjadas; nos testes automáticos (TESTING) ela só
      vale se ``app.config["CSRF_NOS_TESTES"]`` for True.
    """
    app = Flask(__name__)
    chave = os.environ.get("SECRET_KEY") or secret_key
    if not chave:
        chave = secrets.token_hex(32)
        if caminho_banco != ":memory:":
            app.logger.warning("SECRET_KEY não definida: usando uma chave temporária (sessões caem ao reiniciar).")
    app.secret_key = chave
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURO") == "1",
        MAX_CONTENT_LENGTH=1024 * 1024,
        CSRF_ATIVO=csrf,
    )

    app.jinja_env.filters["moeda"] = _formatar_moeda
    app.jinja_env.filters["data"] = lambda v: (v or "").replace("T", " ")
    app.jinja_env.filters["status"] = lambda v: ROTULOS_STATUS.get(v, v)
    app.jinja_env.filters["acao"] = lambda v: ROTULOS_ACAO.get(v, v)

    banco = Banco(caminho_banco)
    criar_admin_padrao(banco, exigir_troca_senha=exigir_troca_senha)
    sessao = Sessao(banco, duracao=duracao_sessao)
    estoque_svc = Estoque(banco)
    app.extensions["sistema"] = servicos = SimpleNamespace(
        banco=banco,
        sessao=sessao,
        autenticador=Autenticador(banco, sessao),
        usuarios=Usuario(banco),
        produtos=Produto(banco),
        tipos=TipoProduto(),
        estoque=estoque_svc,
        compras=Compra(banco),
        vendas=Venda(banco),
        auditoria=Auditoria(banco),
        relatorios=Relatorios(banco, estoque_svc),
        limite_email=LimitadorLogin(maximo=5, janela=300),
        limite_ip=LimitadorLogin(maximo=30, janela=300),
    )

    for modulo in (auth, painel, usuarios, produtos, operacoes, estoque, relatorios):
        app.register_blueprint(modulo.bp)
    app.register_blueprint(painel.conta)

    # ------------------------------------------------------------------
    # Segurança: CSRF e cabeçalhos
    # ------------------------------------------------------------------
    def csrf_ligado():
        if not app.config["CSRF_ATIVO"]:
            return False
        return not app.config.get("TESTING") or app.config.get("CSRF_NOS_TESTES", False)

    def token_csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    @app.before_request
    def verificar_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and csrf_ligado():
            enviado = request.form.get("csrf_token") or request.headers.get("X-CSRFToken") or ""
            esperado = session.get("csrf", "")
            if not esperado or not hmac.compare_digest(enviado, esperado):
                return render_template(
                    "erro.html", titulo="Requisição recusada",
                    mensagem="Não foi possível confirmar que o pedido veio desta página. "
                             "Volte, recarregue a página e tente de novo.",
                ), 400

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        resposta.headers.setdefault("Content-Security-Policy", CSP)
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        if not request.path.startswith("/static/"):
            resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta

    @app.context_processor
    def contexto():
        usuario = servicos.sessao.validar_token(session.get("token"))
        eh_admin = bool(usuario) and Perfil(usuario["perfil"]).eh_admin()
        return {"usuario_logado": usuario, "eh_admin": eh_admin, "csrf_token": token_csrf}

    # ------------------------------------------------------------------
    # Páginas de erro
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template("erro.html", titulo="Página não encontrada",
                               mensagem="O endereço que você abriu não existe."), 404

    @app.errorhandler(405)
    def metodo_nao_permitido(_erro):
        return render_template("erro.html", titulo="Ação não permitida",
                               mensagem="Essa página não aceita esse tipo de acesso."), 405

    @app.errorhandler(413)
    def grande_demais(_erro):
        return render_template("erro.html", titulo="Pedido grande demais",
                               mensagem="Os dados enviados são grandes demais."), 413

    @app.errorhandler(500)
    def erro_interno(erro):
        app.logger.exception("Erro inesperado: %s", erro)
        return render_template("erro.html", titulo="Algo deu errado",
                               mensagem="Ocorreu um erro inesperado. Nada foi perdido; tente de novo."), 500

    if not app.logger.handlers and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return app
