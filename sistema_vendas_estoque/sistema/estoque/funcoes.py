"""Funções do módulo Estoque."""
from ..erros import ErroValidacao, EstoqueInsuficiente


def calcular_nova_quantidade(atual, movimento):
    """Soma (movimento > 0) ou subtrai (movimento < 0) unidades do estoque.

    Nunca deixa o estoque ficar negativo.
    """
    if not isinstance(atual, int) or not isinstance(movimento, int) or isinstance(movimento, bool):
        raise ErroValidacao("Quantidades devem ser números inteiros.")
    if movimento == 0:
        raise ErroValidacao("O movimento de estoque não pode ser zero.")
    nova = atual + movimento
    if nova < 0:
        raise EstoqueInsuficiente(f"Estoque insuficiente: há {atual} unidade(s), pedido de {-movimento}.")
    return nova
