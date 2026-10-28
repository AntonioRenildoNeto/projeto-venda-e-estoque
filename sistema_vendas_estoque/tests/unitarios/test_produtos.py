"""Testes unitários do módulo Produtos (Arthur)."""
import unittest

from sistema.erros import ErroNaoEncontrado, ErroValidacao
from sistema.produtos.funcoes import salvar_no_banco, validar_dados
from sistema.produtos.tipo_produto import TipoProduto
from tests.base import ModulosTestCase


class TestTipoProduto(unittest.TestCase):
    def test_listar_retorna_os_tres_tipos(self):
        self.assertEqual(TipoProduto().listar(), ["Alimento", "Eletrônico", "Vestuário"])

    def test_validar_tipo(self):
        for tipo in ["Alimento", "Eletrônico", "Vestuário"]:
            self.assertTrue(TipoProduto().validar_tipo(tipo))
        for tipo in ["Brinquedo", "alimento", "", None]:
            self.assertFalse(TipoProduto().validar_tipo(tipo))


class TestValidarDados(unittest.TestCase):
    def dados(self, **m):
        return {**{"nome": "Camiseta", "tipo": "Vestuário", "preco": "39,90"}, **m}

    def test_dados_corretos_sao_aceitos_e_limpos(self):
        r = validar_dados(self.dados(nome="  Camiseta   Azul "))
        self.assertEqual(r, {"nome": "Camiseta Azul", "tipo": "Vestuário", "preco": 39.90})

    def test_preco_aceita_virgula_ponto_e_numero(self):
        self.assertEqual(validar_dados(self.dados(preco="10,5"))["preco"], 10.5)
        self.assertEqual(validar_dados(self.dados(preco="10.5"))["preco"], 10.5)
        self.assertEqual(validar_dados(self.dados(preco=10))["preco"], 10.0)

    def test_dados_invalidos_sao_recusados(self):
        casos = {
            "nome vazio": {"nome": "   "},
            "nome ausente": {"nome": None},
            "nome longo": {"nome": "x" * 81},
            "tipo inválido": {"tipo": "Brinquedo"},
            "preço negativo": {"preco": "-5"},
            "preço zero": {"preco": "0"},
            "preço texto": {"preco": "abc"},
            "preço vazio": {"preco": ""},
            "preço nulo": {"preco": None},
            "preço infinito": {"preco": "inf"},
            "preço nan": {"preco": "nan"},
        }
        for descricao, mudanca in casos.items():
            with self.subTest(descricao):
                with self.assertRaises(ErroValidacao):
                    validar_dados(self.dados(**mudanca))


class TestSalvarNoBanco(ModulosTestCase):
    def test_grava_o_produto_e_devolve_o_id(self):
        pid = salvar_no_banco(self.banco, {"nome": "Arroz", "tipo": "Alimento", "preco": 20.0})
        linha = self.banco.consultar_um("SELECT * FROM produtos WHERE id = ?", (pid,))
        self.assertEqual(linha["nome"], "Arroz")


class TestProduto(ModulosTestCase):
    def test_cadastrar_os_tres_tipos(self):
        for nome, tipo in [("Arroz", "Alimento"), ("Fone", "Eletrônico"), ("Camisa", "Vestuário")]:
            p = self.produtos.cadastrar(nome, tipo, "10")
            self.assertEqual(p["tipo"], tipo)
        self.assertEqual(len(self.produtos.listar()), 3)

    def test_cadastrar_coloca_o_produto_no_estoque_com_zero(self):
        p = self.produtos.cadastrar("Arroz", "Alimento", "10")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 0)

    def test_cadastrar_invalido_nao_grava_nada(self):
        with self.assertRaises(ErroValidacao):
            self.produtos.cadastrar("Arroz", "Brinquedo", "10")
        self.assertEqual(self.produtos.listar(), [])
        self.assertEqual(self.estoque.listar(), [])

    def test_listar_ordena_por_nome(self):
        self.produtos.cadastrar("Zebra", "Vestuário", "1")
        self.produtos.cadastrar("Abacate", "Alimento", "1")
        self.assertEqual([p["nome"] for p in self.produtos.listar()], ["Abacate", "Zebra"])

    def test_buscar_por_nome_ignora_maiusculas_e_acha_parte_do_nome(self):
        self.produtos.cadastrar("Arroz Integral", "Alimento", "10")
        self.produtos.cadastrar("Feijão", "Alimento", "8")
        achados = self.produtos.buscar_por_nome("ARROZ")
        self.assertEqual([p["nome"] for p in achados], ["Arroz Integral"])
        self.assertEqual(self.produtos.buscar_por_nome("xyz"), [])

    def test_buscar_por_id(self):
        p = self.produtos.cadastrar("Arroz", "Alimento", "10")
        self.assertEqual(self.produtos.buscar_por_id(p["id"])["nome"], "Arroz")
        self.assertIsNone(self.produtos.buscar_por_id(999))

    def test_remover_tira_do_cadastro_e_do_estoque(self):
        p = self.produtos.cadastrar("Arroz", "Alimento", "10")
        self.produtos.remover(p["id"])
        self.assertIsNone(self.produtos.buscar_por_id(p["id"]))
        self.assertEqual(self.estoque.listar(), [])

    def test_remover_produto_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.produtos.remover(999)


if __name__ == "__main__":
    unittest.main()
