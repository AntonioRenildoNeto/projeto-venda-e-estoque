"""Classe Sessao: a credencial temporária (token) de quem está logado."""
import secrets
import time

from .funcoes import token_expirado

DURACAO_PADRAO = 60 * 60  # 1 hora


class Sessao:
    def __init__(self, banco, duracao=DURACAO_PADRAO, relogio=time.time):
        self.banco = banco
        self.duracao = duracao
        self.relogio = relogio

    def gerar_token(self, usuario_id):
        """Cria um token depois de um login bem-sucedido (e limpa os tokens vencidos)."""
        self.limpar_expirados()
        token = secrets.token_urlsafe(32)
        self.banco.executar(
            "INSERT INTO tokens (token, usuario_id, expira_em) VALUES (?, ?, ?)",
            (token, usuario_id, self.relogio() + self.duracao),
        )
        return token

    def limpar_expirados(self):
        """Apaga do banco os tokens cujo prazo já passou."""
        self.banco.executar("DELETE FROM tokens WHERE expira_em <= ?", (self.relogio(),))

    def encerrar_todas(self, usuario_id):
        """Derruba todas as sessões abertas de um usuário."""
        self.banco.executar("DELETE FROM tokens WHERE usuario_id = ?", (usuario_id,))

    def validar_token(self, token):
        """Devolve o usuário dono do token, ou None se for inválido ou expirado."""
        if not token:
            return None
        registro = self.banco.consultar_um("SELECT * FROM tokens WHERE token = ?", (token,))
        if registro is None:
            return None
        if token_expirado(registro["expira_em"], self.relogio()):
            self.banco.executar("DELETE FROM tokens WHERE token = ?", (token,))
            return None
        usuario = self.banco.consultar_um(
            "SELECT id, nome_completo, email, telefone, perfil, trocar_senha FROM usuarios WHERE id = ?",
            (registro["usuario_id"],),
        )
        return usuario
