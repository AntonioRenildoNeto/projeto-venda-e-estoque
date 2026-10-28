"""Classe Perfil: define o que cada tipo de usuário pode fazer."""
from ..erros import ErroValidacao

PERMISSOES = {
    "admin": [
        "cadastrar_usuario",
        "remover_usuario",
        "cadastrar_produto",
        "editar_produto",
        "remover_produto",
        "ver_relatorios",
        "ver_auditoria",
        "comprar",
        "vender",
        "consultar_estoque",
    ],
    "comum": ["comprar", "vender", "consultar_estoque"],
}

PERFIS = tuple(PERMISSOES)


class Perfil:
    def __init__(self, nome):
        if nome not in PERMISSOES:
            raise ErroValidacao(f"Perfil inválido: {nome!r}. Use {' ou '.join(PERFIS)}.")
        self.nome = nome

    def eh_admin(self):
        """Informa se o perfil é de administrador."""
        return self.nome == "admin"

    def listar_permissoes(self):
        """Mostra as ações liberadas para o perfil."""
        return list(PERMISSOES[self.nome])

    def tem_permissao(self, acao):
        return acao in PERMISSOES[self.nome]
