"""Testes de regressão (Arthur).

Guardam comportamentos delicados, fáceis de quebrar quando alguém mexe no código.
Depois de qualquer correção, rode:  python executar_testes.py regressao
(isso executa de novo os unitários, os de integração e este grupo).
"""
from sistema.erros import ErroValidacao, EstoqueInsuficiente
from tests.base import USUARIO_COMUM, ModulosTestCase, WebTestCase


class TestRegressaoEstoqueEVendas(ModulosTestCase):
    def test_cancelar_venda_de_produto_removido_nao_quebra(self):
        p = self.novo_produto(quantidade=5)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 2}], "admin")
        self.produtos.remover(p["id"])
        self.assertEqual(self.vendas.cancelar(v["id"])["status"], "cancelada")

    def test_cancelar_duas_vezes_nao_duplica_o_estoque(self):
        p = self.novo_produto(quantidade=10)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 4}], "admin")
        self.vendas.cancelar(v["id"])
        with self.assertRaises(ErroValidacao):
            self.vendas.cancelar(v["id"])
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 10)

    def test_mesmo_produto_em_dois_itens_soma_as_quantidades(self):
        p = self.novo_produto(quantidade=5)
        itens = [{"produto_id": p["id"], "quantidade": 3}, {"produto_id": p["id"], "quantidade": 3}]
        with self.assertRaises(EstoqueInsuficiente):
            self.vendas.registrar(itens, "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 5)

    def test_venda_que_falha_no_meio_desfaz_tudo(self):
        a, b = self.novo_produto("A", quantidade=5), self.novo_produto("B", quantidade=5)
        original = self.estoque.atualizar

        def falha_no_segundo(produto_id, movimento, motivo=""):
            if produto_id == b["id"]:
                raise RuntimeError("falha simulada")
            return original(produto_id, movimento, motivo)

        self.vendas.estoque.atualizar = falha_no_segundo
        with self.assertRaises(RuntimeError):
            self.vendas.registrar(
                [{"produto_id": a["id"], "quantidade": 1}, {"produto_id": b["id"], "quantidade": 1}], "admin"
            )
        self.assertEqual(self.estoque.consultar_quantidade(a["id"]), 5)
        self.assertEqual(self.vendas.listar(), [])

    def test_estoque_nunca_fica_negativo(self):
        p = self.novo_produto(quantidade=1)
        for _ in range(3):
            try:
                self.vendas.registrar([{"produto_id": p["id"], "quantidade": 1}], "admin")
            except EstoqueInsuficiente:
                pass
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 0)

    def test_historico_de_compras_continua_depois_de_remover_o_produto(self):
        p = self.novo_produto("Arroz", quantidade=5)
        self.produtos.remover(p["id"])
        itens = self.compras.listar()[0]["itens"]
        self.assertEqual(itens[0]["produto_nome"], "Arroz")

    def test_quantidade_decimal_zero_ou_negativa_e_recusada(self):
        p = self.novo_produto(quantidade=5)
        for qtd in ["1.5", "0", "-3", "dois", ""]:
            with self.subTest(qtd=qtd):
                with self.assertRaises(ErroValidacao):
                    self.vendas.registrar([{"produto_id": p["id"], "quantidade": qtd}], "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 5)

    def test_preco_com_virgula_e_aceito(self):
        self.assertEqual(self.produtos.cadastrar("Café", "Alimento", "12,75")["preco"], 12.75)

    def test_soma_de_precos_nao_acumula_erro_de_ponto_flutuante(self):
        itens = [{"quantidade": 3, "preco_unitario": 0.1}] * 3
        self.assertEqual(self.compras.calcular_total(itens), 0.9)


class TestRegressaoUsuariosESessao(ModulosTestCase):
    def test_email_com_letras_maiusculas_funciona_no_cadastro_e_no_login(self):
        self.usuarios.cadastrar(**{**USUARIO_COMUM, "email": "Maria@Loja.COM"})
        self.assertTrue(self.autenticador.login("maria@loja.com", USUARIO_COMUM["senha"]))
        self.assertTrue(self.autenticador.login("MARIA@LOJA.COM", USUARIO_COMUM["senha"]))

    def test_cadastro_recusado_nao_deixa_usuario_pela_metade(self):
        with self.assertRaises(ErroValidacao):
            self.usuarios.cadastrar(**{**USUARIO_COMUM, "telefone": "123"})
        self.assertIsNone(self.usuarios.buscar_por_id(USUARIO_COMUM["id"]))

    def test_admin_padrao_nao_e_criado_duas_vezes(self):
        from sistema.inicializacao import criar_admin_padrao
        criar_admin_padrao(self.banco)
        self.assertEqual(len([u for u in self.usuarios.listar() if u["perfil"] == "admin"]), 1)


class TestRegressaoWeb(WebTestCase):
    def test_senha_nunca_aparece_nas_telas(self):
        self.criar_usuario_comum()
        self.entrar()
        html = self.texto(self.client.get("/usuarios"))
        self.assertNotIn(USUARIO_COMUM["senha"], html)
        self.assertNotIn("senha_hash", html)
        self.assertNotIn("$", html.split("<tbody>")[1])  # nenhum hash na tabela

    def test_usuario_removido_com_sessao_aberta_perde_o_acesso_na_hora(self):
        comum = self.cliente_comum()
        self.assertEqual(comum.get("/estoque").status_code, 200)
        self.s.usuarios.remover(USUARIO_COMUM["id"])
        self.assertEqual(comum.get("/estoque").status_code, 302)

    def test_nome_de_produto_com_html_e_escapado_na_tela(self):
        self.entrar()
        self.post("/produtos", {"nome": "<script>alert(1)</script>", "tipo": "Alimento", "preco": "1"})
        html = self.texto(self.client.get("/produtos"))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_busca_de_produto_pela_tela(self):
        self.entrar()
        self.post("/produtos", {"nome": "Arroz Integral", "tipo": "Alimento", "preco": "10"})
        self.post("/produtos", {"nome": "Camiseta", "tipo": "Vestuário", "preco": "40"})
        html = self.texto(self.client.get("/produtos?busca=arroz"))
        self.assertIn("Arroz Integral", html)
        self.assertNotIn("Camiseta", html)

    def test_erro_em_uma_acao_nao_derruba_o_sistema(self):
        self.entrar()
        for rota, dados in [("/vendas", {"produto_id": "", "quantidade": ""}),
                            ("/compras", {"produto_id": "999", "quantidade": "1", "preco_unitario": "1"}),
                            ("/produtos/999/remover", {}), ("/usuarios/fantasma/remover", {}),
                            ("/vendas/999/cancelar", {})]:
            with self.subTest(rota=rota):
                self.assertEqual(self.post(rota, dados).status_code, 200)

    def test_numeros_gigantes_viram_mensagem_de_erro_e_nao_erro_500(self):
        """Antes da correção, quantidade ou ID acima do limite do SQLite derrubava a tela (erro 500)."""
        p = self.s.produtos.cadastrar("Arroz", "Alimento", "10")
        self.entrar()
        gigante = "9" * 30
        casos = [
            ("/compras", {"produto_id": p["id"], "quantidade": gigante, "preco_unitario": "1"}),
            ("/compras", {"produto_id": gigante, "quantidade": "1", "preco_unitario": "1"}),
            ("/vendas", {"produto_id": gigante, "quantidade": "1"}),
            ("/compras", {"produto_id": p["id"], "quantidade": "1", "preco_unitario": "1e308"}),
            (f"/produtos/{gigante}/remover", {}),
            (f"/vendas/{gigante}/cancelar", {}),
        ]
        for rota, dados in casos:
            with self.subTest(rota=rota, dados=dados):
                r = self.post(rota, dados)
                self.assertEqual(r.status_code, 200)
                self.assertIn('class="mensagem', self.texto(r))
        self.assertEqual(self.s.estoque.consultar_quantidade(p["id"]), 0)
        self.assertEqual(self.s.compras.listar(), [])
