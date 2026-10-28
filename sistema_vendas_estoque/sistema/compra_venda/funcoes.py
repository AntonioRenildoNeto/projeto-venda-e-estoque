"""Funções do módulo Compra e Venda."""
from ..erros import ErroValidacao

QUANTIDADE_MAXIMA = 1_000_000


def _inteiro_positivo(valor):
    if isinstance(valor, bool):
        return None
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def validar_itens(itens):
    """Confere se a lista de itens não está vazia e se produto e quantidade são válidos.

    Devolve a lista com produto_id e quantidade já convertidos para inteiros.
    """
    if not itens:
        raise ErroValidacao("Informe pelo menos um item.")
    validos = []
    for item in itens:
        produto_id = _inteiro_positivo(item.get("produto_id"))
        quantidade = _inteiro_positivo(item.get("quantidade"))
        if produto_id is None:
            raise ErroValidacao("Selecione um produto.")
        if quantidade is None:
            raise ErroValidacao("A quantidade deve ser um número inteiro maior que zero.")
        if quantidade > QUANTIDADE_MAXIMA:
            raise ErroValidacao(f"A quantidade máxima por item é {QUANTIDADE_MAXIMA:,}.".replace(",", "."))
        novo = dict(item)
        novo["produto_id"] = produto_id
        novo["quantidade"] = quantidade
        validos.append(novo)
    return validos


def calcular_subtotal(item):
    """Multiplica o preço unitário pela quantidade de um item."""
    return round(float(item["preco_unitario"]) * int(item["quantidade"]), 2)


def anexar_itens(banco, registros, tabela, coluna):
    """Coloca em cada compra/venda a lista de itens, com UMA consulta só (evita N consultas)."""
    if not registros:
        return registros
    ids = [r["id"] for r in registros]
    por_registro = {i: [] for i in ids}
    marcas = ",".join("?" * len(ids))
    for item in banco.consultar(f"SELECT * FROM {tabela} WHERE {coluna} IN ({marcas}) ORDER BY id", ids):
        por_registro[item[coluna]].append(item)
    for r in registros:
        r["itens"] = por_registro[r["id"]]
    return registros
