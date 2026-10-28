"""Erros do sistema. Cada módulo levanta um deles quando algo não é permitido."""


class ErroSistema(Exception):
    """Erro base do sistema."""


class ErroValidacao(ErroSistema):
    """Dados inválidos (campo vazio, e-mail errado, quantidade negativa...)."""


class ErroPermissao(ErroSistema):
    """O usuário não tem permissão para a ação."""


class ErroNaoEncontrado(ErroSistema):
    """O registro procurado não existe."""


class EstoqueInsuficiente(ErroValidacao):
    """Não há unidades suficientes em estoque."""
