"""Classe TipoProduto: as três categorias aceitas."""

TIPOS = ("Alimento", "Eletrônico", "Vestuário")


class TipoProduto:
    def listar(self):
        """Retorna os três tipos de produto aceitos."""
        return list(TIPOS)

    def validar_tipo(self, tipo):
        """Confere se o tipo informado é um dos três aceitos."""
        return tipo in TIPOS
