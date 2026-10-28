"""Testes das melhorias de dados: edição, exclusão lógica, estoque mínimo, migração, concorrência."""
import hashlib
import os
import sqlite3
import tempfile
import threading
import unittest

from sistema.banco import Banco
from sistema.compra_venda.compra import Compra
from sistema.compra_venda.venda import Venda
from sistema.erros import ErroNaoEncontrado, ErroValidacao
from sistema.inicializacao import criar_admin_padrao
from sistema.produtos.produto import Produto
from tests.base import ModulosTestCase


class TestEditarProduto(ModulosTestCase):
    def test_edita_nome_tipo_preco_e_minimo(self):
        p = self.novo_produto()
        novo = self.produtos.editar(p["id"], "  Arroz   Integral ", "Alimento", "7,5", "4")
        self.assertEqual((novo["nome"], novo["preco"], novo["estoque_minimo"]), ("Arroz Integral", 7.5, 4))

    def test_recusa_dados_invalidos_e_nao_altera(self):
        p = self.novo_produto()
        for args in [("", "Alimento", "1", "0"), ("X", "Brinquedo", "1", "0"),
                     ("X", "Alimento", "0", "0"), ("X", "Alimento", "1", "-1"), ("X", "Alimento", "1", "abc")]:
            with self.assertRaises(ErroValidacao):
                self.produtos.editar(p["id"], *args)
        self.assertEqual(self.produtos.buscar_por_id(p["id"])["nome"], "Arroz 5kg")

    def test_editar_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.produtos.editar(999, "X", "Alimento", "1", "0")

    def test_venda_antiga_mantem_o_preco_da_epoca(self):
        p = self.novo_produto(preco="10", quantidade=5)
        venda = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 1}], "admin")
        self.produtos.editar(p["id"], "Arroz", "Alimento", "99", "0")
        self.assertEqual(self.vendas.buscar_por_id(venda["id"])["itens"][0]["preco_unitario"], 10.0)


class TestExclusaoLogica(ModulosTestCase):
    def test_produto_removido_some_mas_historico_fica(self):
        p = self.novo_produto(quantidade=5)
        venda = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 2}], "admin")
        self.produtos.remover(p["id"])
        self.assertIsNone(self.produtos.buscar_por_id(p["id"]))
        self.assertEqual(self.produtos.listar(), [])
        self.assertEqual(self.estoque.listar(), [])
        self.assertEqual(self.vendas.buscar_por_id(venda["id"])["itens"][0]["produto_nome"], "Arroz 5kg")
        linha = self.banco.consultar_um("SELECT ativo FROM produtos WHERE id = ?", (p["id"],))
        self.assertEqual(linha["ativo"], 0)

    def test_produto_removido_nao_pode_ser_vendido_nem_comprado(self):
        p = self.novo_produto(quantidade=5)
        self.produtos.remover(p["id"])
        with self.assertRaises(ErroNaoEncontrado):
            self.vendas.registrar([{"produto_id": p["id"], "quantidade": 1}], "admin")
        with self.assertRaises(ErroNaoEncontrado):
            self.compras.registrar([{"produto_id": p["id"], "quantidade": 1, "preco_unitario": "1"}], "admin")

    def test_cancelar_venda_de_produto_removido_continua_funcionando(self):
        p = self.novo_produto(quantidade=5)
        venda = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 2}], "admin")
        self.produtos.remover(p["id"])
        self.assertEqual(self.vendas.cancelar(venda["id"])["status"], "cancelada")

    def test_banco_recusa_item_apontando_para_produto_inexistente(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.banco.executar(
                "INSERT INTO movimentos_estoque (produto_id, quantidade, tipo, data) VALUES (999, 1, 'entrada', 'x')"
            )


class TestEstoqueMinimo(ModulosTestCase):
    def test_lista_abaixo_do_minimo_e_valor_total(self):
        a = self.produtos.cadastrar("Arroz", "Alimento", "10", 5)
        b = self.produtos.cadastrar("Feijão", "Alimento", "20", 5)
        c = self.produtos.cadastrar("Sal", "Alimento", "3", 0)  # sem mínimo: nunca alerta
        self.compras.registrar([
            {"produto_id": a["id"], "quantidade": 3, "preco_unitario": "1"},
            {"produto_id": b["id"], "quantidade": 9, "preco_unitario": "1"},
        ], "admin")
        alerta = self.estoque.listar_abaixo_do_minimo()
        self.assertEqual([e["nome"] for e in alerta], ["Arroz"])
        self.assertEqual(self.estoque.valor_total(), 3 * 10 + 9 * 20)
        self.assertIn(c["id"], [e["produto_id"] for e in self.estoque.listar()])


class TestListagemEmLote(ModulosTestCase):
    def test_paginacao_e_itens_corretos(self):
        p = self.novo_produto(quantidade=100)
        for i in range(1, 6):
            self.vendas.registrar([{"produto_id": p["id"], "quantidade": i}], "admin")
        pagina = self.vendas.listar(limite=2, deslocamento=0)
        self.assertEqual([v["id"] for v in pagina], [5, 4])
        self.assertEqual(pagina[0]["itens"][0]["quantidade"], 5)
        self.assertEqual([v["id"] for v in self.vendas.listar(limite=2, deslocamento=4)], [1])
        self.assertEqual(self.vendas.contar(), 5)
        self.assertEqual(len(self.vendas.listar()), 5)

    def test_listar_compras_sem_registros(self):
        self.assertEqual(self.compras.listar(limite=10), [])


class TestMigracao(unittest.TestCase):
    ESQUEMA_ANTIGO = """
    CREATE TABLE usuarios (id TEXT PRIMARY KEY, nome_completo TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
        telefone TEXT NOT NULL, senha_hash TEXT NOT NULL, perfil TEXT NOT NULL);
    CREATE TABLE tokens (token TEXT PRIMARY KEY, usuario_id TEXT NOT NULL, expira_em REAL NOT NULL);
    CREATE TABLE produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, tipo TEXT NOT NULL, preco REAL NOT NULL);
    CREATE TABLE estoque (produto_id INTEGER PRIMARY KEY, quantidade INTEGER NOT NULL);
    """

    def test_banco_da_versao_antiga_e_atualizado_sem_perder_dados(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "antigo.db")
            conn = sqlite3.connect(caminho)
            conn.executescript(self.ESQUEMA_ANTIGO)
            sal = "sal"
            hash_antigo = f"{sal}${hashlib.pbkdf2_hmac('sha256', b'admin123', sal.encode(), 60000).hex()}"
            conn.execute("INSERT INTO usuarios VALUES ('admin','Administrador Sistema','admin@sistema.com','(11) 99999-0000',?,'admin')", (hash_antigo,))
            conn.execute("INSERT INTO produtos (nome, tipo, preco) VALUES ('Arroz','Alimento',10)")
            conn.execute("INSERT INTO estoque VALUES (1, 7)")
            conn.commit()
            conn.close()

            banco = Banco(caminho)
            try:
                criar_admin_padrao(banco)
                p = Produto(banco).buscar_por_id(1)
                self.assertEqual((p["nome"], p["ativo"], p["estoque_minimo"]), ("Arroz", 1, 0))
                self.assertEqual(banco.consultar_um("SELECT quantidade FROM estoque")["quantidade"], 7)
                self.assertEqual(banco.consultar_um("SELECT trocar_senha FROM usuarios")["trocar_senha"], 0)
                self.assertEqual(banco.consultar_um("PRAGMA user_version")["user_version"], 2)
                Banco(caminho).fechar()  # abrir de novo (migração repetida) não pode falhar
            finally:
                banco.fechar()


class TestConcorrencia(unittest.TestCase):
    def _vender_em_paralelo(self, bancos, tentativas, estoque_inicial):
        vendas = [Venda(b) for b in bancos]
        produto = Produto(bancos[0]).cadastrar("Raro", "Eletrônico", "10")
        Compra(bancos[0]).registrar(
            [{"produto_id": produto["id"], "quantidade": estoque_inicial, "preco_unitario": "1"}], "admin")
        resultados = []

        def vender(i):
            try:
                vendas[i % len(vendas)].registrar([{"produto_id": produto["id"], "quantidade": 1}], "admin")
                resultados.append(True)
            except ErroValidacao:
                resultados.append(False)

        threads = [threading.Thread(target=vender, args=(i,)) for i in range(tentativas)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return produto, resultados

    def test_threads_na_mesma_conexao_nunca_vendem_alem_do_estoque(self):
        banco = Banco()
        try:
            produto, resultados = self._vender_em_paralelo([banco], tentativas=20, estoque_inicial=5)
            self.assertEqual(sum(resultados), 5)
            self.assertEqual(banco.consultar_um("SELECT quantidade FROM estoque")["quantidade"], 0)
        finally:
            banco.fechar()

    def test_duas_conexoes_no_mesmo_arquivo_nunca_vendem_alem_do_estoque(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "concorrencia.db")
            b1, b2 = Banco(caminho), Banco(caminho)
            try:
                produto, resultados = self._vender_em_paralelo([b1, b2], tentativas=16, estoque_inicial=4)
                self.assertEqual(sum(resultados), 4)
                self.assertEqual(b1.consultar_um("SELECT quantidade FROM estoque")["quantidade"], 0)
            finally:
                b1.fechar()
                b2.fechar()


if __name__ == "__main__":
    unittest.main()
