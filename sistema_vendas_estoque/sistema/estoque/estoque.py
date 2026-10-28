"""Classe Estoque: quantidade disponível de cada produto."""
from ..erros import ErroNaoEncontrado, ErroValidacao
from .funcoes import calcular_nova_quantidade
from .movimento_estoque import MovimentoEstoque


class Estoque:
    def __init__(self, banco):
        self.banco = banco
        self.movimentos = MovimentoEstoque(banco)

    # Ligação com o módulo Produtos ---------------------------------------
    def criar_registro(self, produto_id):
        """Um produto recém-cadastrado entra no estoque com 0 unidade."""
        self.banco.executar(
            "INSERT INTO estoque (produto_id, quantidade) VALUES (?, 0)", (produto_id,)
        )

    def remover_registro(self, produto_id):
        """Um produto removido sai do estoque."""
        self.banco.executar("DELETE FROM estoque WHERE produto_id = ?", (produto_id,))

    # Operações principais ------------------------------------------------
    def consultar_quantidade(self, produto_id):
        """Informa quantas unidades existem do produto."""
        linha = self.banco.consultar_um(
            "SELECT quantidade FROM estoque WHERE produto_id = ?", (produto_id,)
        )
        if linha is None:
            raise ErroNaoEncontrado("Produto não encontrado no estoque.")
        return linha["quantidade"]

    def verificar_disponibilidade(self, produto_id, quantidade):
        """Confere se há unidades suficientes para a quantidade pedida."""
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ErroValidacao("A quantidade deve ser um número inteiro maior que zero.")
        return self.consultar_quantidade(produto_id) >= quantidade

    def atualizar(self, produto_id, movimento, motivo=""):
        """Soma ou subtrai unidades e registra a movimentação. Devolve a nova quantidade."""
        with self.banco.transacao():
            nova = calcular_nova_quantidade(self.consultar_quantidade(produto_id), movimento)
            self.banco.executar(
                "UPDATE estoque SET quantidade = ? WHERE produto_id = ?", (nova, produto_id)
            )
            self.movimentos.registrar(produto_id, movimento, motivo)
        return nova

    def listar(self):
        """Lista os produtos ativos com a quantidade em estoque e o estoque mínimo."""
        return self.banco.consultar(
            "SELECT p.id AS produto_id, p.nome, p.tipo, p.preco, p.estoque_minimo, e.quantidade "
            "FROM estoque e JOIN produtos p ON p.id = e.produto_id WHERE p.ativo = 1 ORDER BY p.nome"
        )

    def listar_abaixo_do_minimo(self):
        """Produtos com quantidade menor ou igual ao estoque mínimo definido (mínimo > 0)."""
        return self.banco.consultar(
            "SELECT p.id AS produto_id, p.nome, p.tipo, p.estoque_minimo, e.quantidade "
            "FROM estoque e JOIN produtos p ON p.id = e.produto_id "
            "WHERE p.ativo = 1 AND p.estoque_minimo > 0 AND e.quantidade <= p.estoque_minimo "
            "ORDER BY e.quantidade, p.nome"
        )

    def valor_total(self):
        """Valor do estoque (quantidade × preço de cadastro)."""
        linha = self.banco.consultar_um(
            "SELECT COALESCE(SUM(e.quantidade * p.preco), 0) AS v "
            "FROM estoque e JOIN produtos p ON p.id = e.produto_id WHERE p.ativo = 1"
        )
        return round(linha["v"], 2)
