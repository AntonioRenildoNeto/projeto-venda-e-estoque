"""Funções do módulo Autenticação."""
import hashlib
import hmac
import os
import time

PREFIXO = "pbkdf2_sha256"
ITERACOES_PADRAO = 600_000   # recomendação atual da OWASP para PBKDF2-HMAC-SHA256
_ITERACOES_ANTIGAS = 60_000  # formato antigo "sal$hash", ainda aceito no login


def iteracoes_atuais():
    """Quantas voltas o hash dá. Pode ser reduzida só nos testes (SENHA_ITERACOES)."""
    try:
        return max(1, int(os.environ.get("SENHA_ITERACOES", ITERACOES_PADRAO)))
    except ValueError:
        return ITERACOES_PADRAO


def _derivar(senha, sal, iteracoes):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), iteracoes).hex()


def gerar_hash_senha(senha, sal=None, iteracoes=None):
    """Transforma a senha em texto seguro para guardar ('pbkdf2_sha256$voltas$sal$hash')."""
    sal = sal or os.urandom(16).hex()
    iteracoes = iteracoes or iteracoes_atuais()
    return f"{PREFIXO}${iteracoes}${sal}${_derivar(senha, sal, iteracoes)}"


def _separar(hash_guardado):
    """Devolve (iterações, sal, hash) aceitando o formato novo e o antigo."""
    partes = hash_guardado.split("$")
    if len(partes) == 4 and partes[0] == PREFIXO:
        return int(partes[1]), partes[2], partes[3]
    if len(partes) == 2:
        return _ITERACOES_ANTIGAS, partes[0], partes[1]
    raise ValueError("formato de hash desconhecido")


def comparar_senha(senha, hash_guardado):
    """Confere se a senha digitada corresponde ao hash guardado no banco."""
    if not senha or not hash_guardado or "$" not in hash_guardado:
        return False
    try:
        iteracoes, sal, esperado = _separar(hash_guardado)
    except ValueError:
        return False
    return hmac.compare_digest(_derivar(senha, sal, iteracoes), esperado)


def precisa_atualizar_hash(hash_guardado):
    """True se o hash foi gerado com um formato ou número de voltas mais fraco."""
    try:
        iteracoes, _, _ = _separar(hash_guardado)
    except ValueError:
        return True
    return not hash_guardado.startswith(PREFIXO) or iteracoes < iteracoes_atuais()


def token_expirado(expira_em, agora=None):
    """Diz se o prazo de validade do token já passou."""
    agora = time.time() if agora is None else agora
    return agora >= expira_em
