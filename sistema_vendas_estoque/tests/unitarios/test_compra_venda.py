"""Testes unitários do módulo Compra e Venda (Laerte)."""
import unittest

from sistema.compra_venda.funcoes import calcular_subtotal, validar_itens
from sistema.erros import ErroNaoEncontrado, ErroValidacao, EstoqueInsuficiente
from tests.base import ModulosTestCase


class TestFuncoesCompraVenda(unittest.TestCase):
    def test_validar_itens_converte_para_inteiros(self):
        r = validar_itens([{"produto_id": "3", "quantidade": "2", "preco_unitario": "5"}])
        self.assertEqual((r[0]["produto_id"], r[0]["quantidade"]), (3, 2))
        self.assertEqual(r[0]["preco_unitario"], "5")  # demais campos são mantidos

    def test_lista_vazia_e_recusada(self):
        for vazio in [[], None]:
            with self.assertRaises(ErroValidacao):
                validar_itens(vazio)

    def test_item_invalido_e_recusado(self):
        casos = [
            {"produto_id": "", "quantidade": 1},
            {"produto_id": None, "quantidade": 1},
            {"produto_id": 1, "quantidade": 0},
            {"produto_id": 1, "quantidade": -2},
            {"produto_id": 1, "quantidade": 1.5},
            {"produto_id": 1, "quantidade": "abc"},
            {"produto_id": 1},
            {"produto_id": 1, "quantidade": True},
        ]
        for item in casos:
            with self.subTest(item=item):
                with self.assertRaises(ErroValidacao):
                    validar_itens([item])

    def test_um_item_ruim_invalida_a_lista_toda(self):
        with self.assertRaises(ErroValidacao):
            validar_itens([{"produto_id": 1, "quantidade": 1}, {"produto_id": 2, "quantidade": 0}])

    def test_calcular_subtotal(self):
        self.assertEqual(calcular_subtotal({"preco_unitario": 12.5, "quantidade": 4}), 50.0)
        self.assertEqual(calcular_subtotal({"preco_unitario": "0.10", "quantidade": "3"}), 0.30)


class TestCompra(ModulosTestCase):
    def item(self, produto, quantidade=10, preco="20"):
        return {"produto_id": produto["id"], "quantidade": quantidade, "preco_unitario": preco}

    def test_calcular_total_soma_os_itens(self):
        itens = [{"quantidade": 2, "preco_unitario": 10.0}, {"quantidade": 3, "preco_unitario": 5.5}]
        self.assertEqual(self.compras.calcular_total(itens), 36.5)

    def test_registrar_grava_compra_e_total(self):
        p = self.novo_produto()
        c = self.compras.registrar([self.item(p, 10, "20,50")], "admin")
        self.assertEqual(c["total"], 205.0)
        self.assertEqual(c["usuario_id"], "admin")
        self.assertEqual(c["itens"][0]["produto_nome"], "Arroz 5kg")

    def test_registrar_com_varios_itens(self):
        a, b = self.novo_produto("A"), self.novo_produto("B")
        c = self.compras.registrar([self.item(a, 2, "10"), self.item(b, 3, "5")], "admin")
        self.assertEqual(c["total"], 35.0)
        self.assertEqual(len(c["itens"]), 2)

    def test_registrar_recusa_dados_invalidos_sem_gravar(self):
        p = self.novo_produto()
        casos = {
            "sem itens": [],
            "quantidade zero": [self.item(p, 0)],
            "preço zero": [self.item(p, 1, "0")],
            "preço negativo": [self.item(p, 1, "-3")],
            "preço texto": [self.item(p, 1, "abc")],
        }
        for descricao, itens in casos.items():
            with self.subTest(descricao):
                with self.assertRaises(ErroValidacao):
                    self.compras.registrar(itens, "admin")
        self.assertEqual(self.compras.listar(), [])

    def test_registrar_produto_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.compras.registrar([{"produto_id": 999, "quantidade": 1, "preco_unitario": "1"}], "admin")

    def test_listar_mostra_a_mais_recente_primeiro(self):
        p = self.novo_produto()
        self.compras.registrar([self.item(p, 1)], "admin")
        segunda = self.compras.registrar([self.item(p, 2)], "admin")
        lista = self.compras.listar()
        self.assertEqual(lista[0]["id"], segunda["id"])
        self.assertEqual(len(lista), 2)


class TestVenda(ModulosTestCase):
    def item(self, produto, quantidade=1):
        return {"produto_id": produto["id"], "quantidade": quantidade}

    def test_calcular_total(self):
        itens = [{"quantidade": 2, "preco_unitario": 10.0}, {"quantidade": 1, "preco_unitario": 0.99}]
        self.assertEqual(self.vendas.calcular_total(itens), 20.99)

    def test_registrar_usa_o_preco_do_cadastro(self):
        p = self.novo_produto(preco="25,90", quantidade=10)
        v = self.vendas.registrar([self.item(p, 3)], "admin")
        self.assertEqual(v["total"], 77.7)
        self.assertEqual(v["status"], "concluida")
        self.assertEqual(v["itens"][0]["preco_unitario"], 25.9)

    def test_registrar_bloqueia_quando_nao_ha_estoque(self):
        p = self.novo_produto(quantidade=2)
        with self.assertRaises(EstoqueInsuficiente):
            self.vendas.registrar([self.item(p, 3)], "admin")
        self.assertEqual(self.vendas.listar(), [])

    def test_registrar_produto_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.vendas.registrar([{"produto_id": 999, "quantidade": 1}], "admin")

    def test_registrar_recusa_quantidade_invalida(self):
        p = self.novo_produto(quantidade=5)
        for qtd in [0, -1, "x"]:
            with self.subTest(qtd=qtd):
                with self.assertRaises(ErroValidacao):
                    self.vendas.registrar([self.item(p, qtd)], "admin")

    def test_cancelar_muda_o_status(self):
        p = self.novo_produto(quantidade=5)
        v = self.vendas.registrar([self.item(p, 2)], "admin")
        self.assertEqual(self.vendas.cancelar(v["id"])["status"], "cancelada")

    def test_cancelar_duas_vezes_e_recusado(self):
        p = self.novo_produto(quantidade=5)
        v = self.vendas.registrar([self.item(p, 2)], "admin")
        self.vendas.cancelar(v["id"])
        with self.assertRaises(ErroValidacao):
            self.vendas.cancelar(v["id"])

    def test_cancelar_venda_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.vendas.cancelar(999)

    def test_listar(self):
        p = self.novo_produto(quantidade=5)
        self.vendas.registrar([self.item(p, 1)], "admin")
        self.vendas.registrar([self.item(p, 1)], "admin")
        self.assertEqual(len(self.vendas.listar()), 2)


if __name__ == "__main__":
    unittest.main()
