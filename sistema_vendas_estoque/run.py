"""Inicia o sistema: python run.py  ->  http://127.0.0.1:5000

Configuração por variáveis de ambiente (veja .env.example):
    SECRET_KEY    chave das sessões (se faltar, é criada e guardada em dados/chave_secreta)
    HOST, PORT    onde escutar (padrão 127.0.0.1:5000)
    COOKIE_SEGURO 1 quando o sistema estiver atrás de HTTPS
    ADMIN_SENHA   senha inicial do Admin (padrão admin123; o sistema pede para trocar)
    DADOS_DIR     pasta do banco, dos logs e da chave (padrão ./dados)
"""
import logging
import os
import secrets
from logging.handlers import RotatingFileHandler

from sistema.app import criar_app

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.environ.get("DADOS_DIR") or os.path.join(RAIZ, "dados")


def chave_secreta():
    """Usa SECRET_KEY, ou cria uma chave aleatória e a guarda para sobreviver a reinícios."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    caminho = os.path.join(PASTA_DADOS, "chave_secreta")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            return f.read().strip()
    chave = secrets.token_hex(32)
    descritor = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descritor, "w", encoding="utf-8") as f:
        f.write(chave)
    return chave


def configurar_logs():
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    for destino in (logging.StreamHandler(),
                    RotatingFileHandler(os.path.join(PASTA_DADOS, "sistema.log"), maxBytes=1_000_000,
                                        backupCount=3, encoding="utf-8")):
        destino.setFormatter(formato)
        raiz.addHandler(destino)


def main():
    os.makedirs(PASTA_DADOS, exist_ok=True)
    configurar_logs()
    app = criar_app(
        os.path.join(PASTA_DADOS, "sistema.db"),
        secret_key=chave_secreta(),
        exigir_troca_senha=True,
    )
    host = os.environ.get("HOST", "127.0.0.1")
    porta = int(os.environ.get("PORT", "5000"))
    try:
        from waitress import serve  # servidor de produção (pip install waitress)
    except ImportError:
        logging.getLogger("run").warning("waitress não instalado: usando o servidor de desenvolvimento do Flask.")
        app.run(host=host, port=porta, debug=False, threaded=False)
    else:
        logging.getLogger("run").info("Sistema em http://%s:%s", host, porta)
        serve(app, host=host, port=porta, threads=4)


if __name__ == "__main__":
    main()
