"""Classe Produto: cadastro, edição e remoção de produtos."""
from ..erros import ErroNaoEncontrado
from ..estoque.estoque import Estoque
from .funcoes import salvar_no_banco, validar_dados


class Produto:
    """Produtos removidos ficam no banco com ``ativo = 0``.

    Assim o histórico de compras, vendas e movimentos continua íntegro, mas o
    produto some das telas e não pode mais ser comprado nem vendido.
    """

    def __init__(self, banco):
        self.banco = banco
        self.estoque = Estoque(banco)

    def cadastrar(self, nome, tipo, preco, estoque_minimo=0):
        """Valida os dados, salva o produto e o coloca no estoque com 0 unidade."""
        dados = validar_dados({"nome": nome, "tipo": tipo, "preco": preco, "estoque_minimo": estoque_minimo})
        with self.banco.transacao():
            produto_id = salvar_no_banco(self.banco, dados)
            self.estoque.criar_registro(produto_id)
        return self.buscar_por_id(produto_id)

    def editar(self, produto_id, nome, tipo, preco, estoque_minimo=0):
        """Altera nome, tipo, preço e estoque mínimo de um produto existente."""
        if self.buscar_por_id(produto_id) is None:
            raise ErroNaoEncontrado("Produto não encontrado.")
        dados = validar_dados({"nome": nome, "tipo": tipo, "preco": preco, "estoque_minimo": estoque_minimo})
        self.banco.executar(
            "UPDATE produtos SET nome = ?, tipo = ?, preco = ?, estoque_minimo = ? WHERE id = ?",
            (dados["nome"], dados["tipo"], dados["preco"], dados["estoque_minimo"], produto_id),
        )
        return self.buscar_por_id(produto_id)

    def listar(self):
        """Retorna os produtos cadastrados (ativos)."""
        return self.banco.consultar("SELECT * FROM produtos WHERE ativo = 1 ORDER BY nome")

    def contar(self):
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM produtos WHERE ativo = 1")["n"]

    def buscar_por_id(self, produto_id):
        """Procura um produto ativo pelo id; devolve None se não existir ou tiver sido removido."""
        return self.banco.consultar_um("SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,))

    def buscar_por_nome(self, nome):
        """Procura produtos cujo nome contém o texto informado (sem diferenciar maiúsculas)."""
        termo = f"%{(nome or '').strip().lower()}%"
        return self.banco.consultar(
            "SELECT * FROM produtos WHERE ativo = 1 AND lower(nome) LIKE ? ORDER BY nome", (termo,)
        )

    def remover(self, produto_id):
        """Tira o produto de circulação (some das telas e do estoque; o histórico é mantido)."""
        if self.buscar_por_id(produto_id) is None:
            raise ErroNaoEncontrado("Produto não encontrado.")
        with self.banco.transacao():
            self.estoque.remover_registro(produto_id)
            self.banco.executar("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
