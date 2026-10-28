"""Classe Autenticador: login e logout."""
from ..erros import ErroValidacao
from .funcoes import comparar_senha, gerar_hash_senha, precisa_atualizar_hash

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."


class Autenticador:
    def __init__(self, banco, sessao):
        self.banco = banco
        self.sessao = sessao

    def validar_senha(self, senha, hash_guardado):
        """Confere se a senha digitada está correta."""
        return comparar_senha(senha, hash_guardado)

    def login(self, email, senha):
        """Autentica o usuário e devolve o token da sessão."""
        email = (email or "").strip().lower()
        if not email or not senha:
            raise ErroValidacao("Informe e-mail e senha.")
        usuario = self.banco.consultar_um("SELECT * FROM usuarios WHERE email = ?", (email,))
        if usuario is None:
            # Gasta o mesmo tempo de uma senha errada, para não revelar se o e-mail existe.
            comparar_senha(senha, gerar_hash_senha("x", sal="0" * 32))
            raise ErroValidacao(MENSAGEM_LOGIN_INVALIDO)
        if not self.validar_senha(senha, usuario["senha_hash"]):
            raise ErroValidacao(MENSAGEM_LOGIN_INVALIDO)
        if precisa_atualizar_hash(usuario["senha_hash"]):
            self.banco.executar(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (gerar_hash_senha(senha), usuario["id"]),
            )
        return self.sessao.gerar_token(usuario["id"])

    def logout(self, token):
        """Encerra a sessão, apagando o token."""
        self.banco.executar("DELETE FROM tokens WHERE token = ?", (token,))
