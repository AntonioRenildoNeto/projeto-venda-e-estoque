"""Funções do módulo Produtos (usadas dentro dos métodos Produto.cadastrar e Produto.editar)."""
from ..erros import ErroValidacao
from .tipo_produto import TipoProduto

PRECO_MAXIMO = 1_000_000
ESTOQUE_MINIMO_MAXIMO = 1_000_000


def validar_dados(produto):
    """Verifica se os dados do produto estão corretos.

    Confere se o nome foi preenchido, se o tipo é um dos três aceitos, se o
    preço é maior que zero e se o estoque mínimo (opcional) é um inteiro >= 0.
    Devolve o produto já "limpo" (sem espaços sobrando).
    """
    nome = " ".join(str(produto.get("nome") or "").split())
    tipo = produto.get("tipo")
    preco = produto.get("preco")
    minimo = produto.get("estoque_minimo")

    if not nome:
        raise ErroValidacao("Informe o nome do produto.")
    if len(nome) > 80:
        raise ErroValidacao("O nome do produto deve ter até 80 caracteres.")
    if not TipoProduto().validar_tipo(tipo):
        raise ErroValidacao("Tipo de produto inválido. Use Alimento, Eletrônico ou Vestuário.")
    try:
        preco = float(str(preco).replace(",", "."))
    except (TypeError, ValueError):
        raise ErroValidacao("Preço inválido.")
    if not preco > 0:
        raise ErroValidacao("O preço deve ser maior que zero.")
    if preco > PRECO_MAXIMO:
        raise ErroValidacao("O preço máximo é R$ 1.000.000,00.")

    if minimo in (None, ""):
        minimo = 0
    else:
        try:
            minimo = int(str(minimo).strip())
        except ValueError:
            raise ErroValidacao("O estoque mínimo deve ser um número inteiro.") from None
        if minimo < 0 or minimo > ESTOQUE_MINIMO_MAXIMO:
            raise ErroValidacao("O estoque mínimo deve estar entre 0 e 1.000.000.")
    limpo = {"nome": nome, "tipo": tipo, "preco": round(preco, 2)}
    if "estoque_minimo" in produto:
        limpo["estoque_minimo"] = minimo
    return limpo


def salvar_no_banco(banco, produto):
    """Grava o produto no banco de dados e devolve o id gerado."""
    cursor = banco.executar(
        "INSERT INTO produtos (nome, tipo, preco, estoque_minimo) VALUES (?, ?, ?, ?)",
        (produto["nome"], produto["tipo"], produto["preco"], produto.get("estoque_minimo", 0)),
    )
    return cursor.lastrowid
