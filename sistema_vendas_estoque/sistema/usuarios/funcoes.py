"""Funções do módulo Usuários."""
import re

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_email(email):
    """True se o e-mail tem formato válido (algo@dominio.com)."""
    return bool(email) and bool(_PADRAO_EMAIL.match(email.strip()))


def validar_telefone(telefone):
    """True se o telefone tem 10 ou 11 dígitos (com DDD), com ou sem máscara."""
    if not telefone:
        return False
    if re.search(r"[^\d\s()+-]", telefone):
        return False
    digitos = re.sub(r"\D", "", telefone)
    return len(digitos) in (10, 11)
