"""Testes unitários do módulo Estoque (Arthur)."""
import unittest

from sistema.erros import ErroNaoEncontrado, ErroValidacao, EstoqueInsuficiente
from sistema.estoque.funcoes import calcular_nova_quantidade
from tests.base import ModulosTestCase


class TestCalcularNovaQuantidade(unittest.TestCase):
    def test_entrada_soma(self):
        self.assertEqual(calcular_nova_quantidade(10, 5), 15)

    def test_saida_subtrai(self):
        self.assertEqual(calcular_nova_quantidade(10, -4), 6)

    def test_saida_exata_zera_o_estoque(self):
        self.assertEqual(calcular_nova_quantidade(10, -10), 0)

    def test_saida_maior_que_o_estoque_e_recusada(self):
        with self.assertRaises(EstoqueInsuficiente):
            calcular_nova_quantidade(3, -4)

    def test_movimento_zero_ou_nao_inteiro_e_recusado(self):
        for movimento in [0, 2.5, "3", None, True]:
            with self.subTest(movimento=movimento):
                with self.assertRaises(ErroValidacao):
                    calcular_nova_quantidade(10, movimento)


class TestEstoque(ModulosTestCase):
    def test_consultar_quantidade(self):
        p = self.novo_produto(quantidade=7)
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 7)

    def test_consultar_produto_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.estoque.consultar_quantidade(999)

    def test_verificar_disponibilidade(self):
        p = self.novo_produto(quantidade=5)
        self.assertTrue(self.estoque.verificar_disponibilidade(p["id"], 5))
        self.assertFalse(self.estoque.verificar_disponibilidade(p["id"], 6))

    def test_verificar_disponibilidade_recusa_quantidade_invalida(self):
        p = self.novo_produto(quantidade=5)
        for qtd in [0, -1, 1.5, "2"]:
            with self.subTest(qtd=qtd):
                with self.assertRaises(ErroValidacao):
                    self.estoque.verificar_disponibilidade(p["id"], qtd)

    def test_atualizar_soma_e_subtrai(self):
        p = self.novo_produto()
        self.assertEqual(self.estoque.atualizar(p["id"], 10, "teste"), 10)
        self.assertEqual(self.estoque.atualizar(p["id"], -3, "teste"), 7)
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 7)

    def test_atualizar_alem_do_estoque_nao_altera_nada(self):
        p = self.novo_produto(quantidade=2)
        with self.assertRaises(EstoqueInsuficiente):
            self.estoque.atualizar(p["id"], -3)
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 2)
        self.assertEqual(len(self.estoque.movimentos.listar_por_produto(p["id"])), 1)  # só a compra

    def test_atualizar_produto_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.estoque.atualizar(999, 5)

    def test_listar_mostra_produto_e_quantidade(self):
        self.novo_produto("Arroz", quantidade=4)
        self.novo_produto("Feijão", "Alimento", "8")
        itens = {i["nome"]: i["quantidade"] for i in self.estoque.listar()}
        self.assertEqual(itens, {"Arroz": 4, "Feijão": 0})


class TestMovimentoEstoque(ModulosTestCase):
    def test_registrar_e_listar_por_produto(self):
        p = self.novo_produto()
        m = self.estoque.movimentos
        m.registrar(p["id"], 10, "compra")
        m.registrar(p["id"], -2, "venda")
        historico = m.listar_por_produto(p["id"])
        self.assertEqual([h["quantidade"] for h in historico], [10, -2])
        self.assertEqual([h["tipo"] for h in historico], ["entrada", "saida"])

    def test_historico_e_separado_por_produto(self):
        a, b = self.novo_produto("A"), self.novo_produto("B")
        self.estoque.movimentos.registrar(a["id"], 1, "x")
        self.assertEqual(self.estoque.movimentos.listar_por_produto(b["id"]), [])

    def test_atualizar_registra_movimento_com_motivo(self):
        p = self.novo_produto()
        self.estoque.atualizar(p["id"], 5, "ajuste manual")
        ultimo = self.estoque.movimentos.listar_por_produto(p["id"])[-1]
        self.assertEqual((ultimo["quantidade"], ultimo["motivo"]), (5, "ajuste manual"))


if __name__ == "__main__":
    unittest.main()
