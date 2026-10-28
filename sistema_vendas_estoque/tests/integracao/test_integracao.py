"""Testes de integração: vários módulos funcionando juntos.

Responsáveis (ver relatório, seção 7):
  Antonio: Autenticação x banco, Autenticação x Usuários, token nos demais módulos
  Arthur:  Produtos x Estoque
  Arthur + Laerte: Compra e Venda x Produtos, Compra e Venda x Estoque
"""
from sistema.erros import ErroNaoEncontrado, ErroValidacao, EstoqueInsuficiente
from sistema.inicializacao import ADMIN_PADRAO
from tests.base import USUARIO_COMUM, ModulosTestCase, WebTestCase


class TestAutenticacaoComBancoEUsuarios(ModulosTestCase):
    """Antonio: Autenticação x banco de dados e Autenticação x Usuários."""

    def test_login_consulta_o_banco_e_grava_o_token(self):
        token = self.autenticador.login(ADMIN_PADRAO["email"], ADMIN_PADRAO["senha"])
        linha = self.banco.consultar_um("SELECT * FROM tokens WHERE token = ?", (token,))
        self.assertEqual(linha["usuario_id"], "admin")

    def test_usuario_recem_cadastrado_consegue_entrar(self):
        self.usuarios.cadastrar(**USUARIO_COMUM)
        token = self.autenticador.login(USUARIO_COMUM["email"], USUARIO_COMUM["senha"])
        self.assertEqual(self.sessao.validar_token(token)["nome_completo"], "Maria Souza")

    def test_usuario_removido_nao_consegue_entrar(self):
        self.usuarios.cadastrar(**USUARIO_COMUM)
        self.usuarios.remover("maria01")
        with self.assertRaises(ErroValidacao):
            self.autenticador.login(USUARIO_COMUM["email"], USUARIO_COMUM["senha"])

    def test_usuario_removido_perde_a_sessao_que_estava_aberta(self):
        self.usuarios.cadastrar(**USUARIO_COMUM)
        token = self.autenticador.login(USUARIO_COMUM["email"], USUARIO_COMUM["senha"])
        self.usuarios.remover("maria01")
        self.assertIsNone(self.sessao.validar_token(token))

    def test_senha_fica_guardada_apenas_como_hash(self):
        self.usuarios.cadastrar(**USUARIO_COMUM)
        linha = self.banco.consultar_um("SELECT senha_hash FROM usuarios WHERE id = 'maria01'")
        self.assertNotIn(USUARIO_COMUM["senha"], linha["senha_hash"])


class TestTokenNosDemaisModulos(WebTestCase):
    """Antonio: o token é validado antes de liberar cada módulo; só o Admin cadastra e remove."""

    ROTAS_PROTEGIDAS = ["/", "/usuarios", "/produtos", "/compras", "/vendas", "/estoque"]

    def test_sem_token_todas_as_telas_pedem_login(self):
        for rota in self.ROTAS_PROTEGIDAS:
            with self.subTest(rota=rota):
                r = self.client.get(rota)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/login", r.headers["Location"])

    def test_sem_token_as_acoes_tambem_sao_bloqueadas(self):
        acoes = [
            ("/usuarios", {"id": "x", "nome_completo": "A B", "email": "a@b.com", "telefone": "1132345678", "senha": "123456"}),
            ("/usuarios/admin/remover", {}),
            ("/produtos", {"nome": "X", "tipo": "Alimento", "preco": "1"}),
            ("/compras", {"produto_id": "1", "quantidade": "1", "preco_unitario": "1"}),
            ("/vendas", {"produto_id": "1", "quantidade": "1"}),
        ]
        for rota, dados in acoes:
            with self.subTest(rota=rota):
                r = self.client.post(rota, data=dados)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/login", r.headers["Location"])
        self.assertEqual(self.s.produtos.listar(), [])

    def test_token_invalido_no_cookie_e_rejeitado(self):
        with self.client.session_transaction() as sessao:
            sessao["token"] = "token-falso"
        self.assertEqual(self.client.get("/estoque").status_code, 302)

    def test_token_expirado_e_rejeitado(self):
        self.s.sessao.duracao = -1  # o token já nasce vencido
        self.entrar()
        self.assertEqual(self.client.get("/estoque").status_code, 302)

    def test_usuario_comum_nao_acessa_telas_nem_acoes_do_admin(self):
        comum = self.cliente_comum()
        self.assertEqual(comum.get("/usuarios").status_code, 403)
        self.assertEqual(comum.post("/usuarios", data={}).status_code, 403)
        self.assertEqual(comum.post("/usuarios/admin/remover").status_code, 403)
        self.assertEqual(comum.post("/produtos", data={"nome": "X", "tipo": "Alimento", "preco": "1"}).status_code, 403)
        self.assertEqual(comum.post("/produtos/1/remover").status_code, 403)
        self.assertIsNotNone(self.s.usuarios.buscar_por_id("admin"))

    def test_usuario_comum_acessa_o_que_e_permitido(self):
        comum = self.cliente_comum()
        for rota in ["/", "/produtos", "/compras", "/vendas", "/estoque"]:
            with self.subTest(rota=rota):
                self.assertEqual(comum.get(rota).status_code, 200)

    def test_admin_acessa_tudo(self):
        self.entrar()
        for rota in self.ROTAS_PROTEGIDAS:
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(rota).status_code, 200)

    def test_logout_invalida_o_acesso(self):
        self.entrar()
        self.client.post("/logout")
        self.assertEqual(self.client.get("/estoque").status_code, 302)


class TestProdutosComEstoque(ModulosTestCase):
    """Arthur: Produtos x Estoque."""

    def test_produto_cadastrado_aparece_no_estoque_com_zero(self):
        p = self.produtos.cadastrar("Fone", "Eletrônico", "99")
        item = next(i for i in self.estoque.listar() if i["produto_id"] == p["id"])
        self.assertEqual((item["nome"], item["quantidade"]), ("Fone", 0))

    def test_produto_removido_some_do_estoque(self):
        p = self.novo_produto(quantidade=5)
        self.produtos.remover(p["id"])
        self.assertEqual(self.estoque.listar(), [])
        with self.assertRaises(ErroNaoEncontrado):
            self.estoque.consultar_quantidade(p["id"])

    def test_falha_no_cadastro_nao_deixa_registro_no_estoque(self):
        with self.assertRaises(ErroValidacao):
            self.produtos.cadastrar("", "Alimento", "10")
        self.assertEqual(self.estoque.listar(), [])


class TestCompraEVendaComProdutos(ModulosTestCase):
    """Arthur + Laerte: Compra e Venda x Produtos."""

    def test_so_e_possivel_comprar_produto_cadastrado(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.compras.registrar([{"produto_id": 42, "quantidade": 1, "preco_unitario": "5"}], "admin")

    def test_so_e_possivel_vender_produto_cadastrado(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.vendas.registrar([{"produto_id": 42, "quantidade": 1}], "admin")

    def test_venda_usa_o_preco_e_o_nome_do_cadastro(self):
        p = self.novo_produto("Camisa", "Vestuário", "50", quantidade=3)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 2}], "admin")
        self.assertEqual((v["total"], v["itens"][0]["produto_nome"]), (100.0, "Camisa"))

    def test_historico_guarda_o_nome_mesmo_se_o_produto_for_removido(self):
        p = self.novo_produto("Camisa", "Vestuário", "50", quantidade=3)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 1}], "admin")
        self.produtos.remover(p["id"])
        self.assertEqual(self.vendas.buscar_por_id(v["id"])["itens"][0]["produto_nome"], "Camisa")


class TestCompraEVendaComEstoque(ModulosTestCase):
    """Arthur + Laerte: Compra e Venda x Estoque."""

    def test_compra_aumenta_o_estoque_e_registra_o_movimento(self):
        p = self.novo_produto()
        c = self.compras.registrar([{"produto_id": p["id"], "quantidade": 12, "preco_unitario": "5"}], "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 12)
        mov = self.estoque.movimentos.listar_por_produto(p["id"])[-1]
        self.assertEqual((mov["tipo"], mov["quantidade"], mov["motivo"]), ("entrada", 12, f"compra #{c['id']}"))

    def test_venda_diminui_o_estoque_e_registra_o_movimento(self):
        p = self.novo_produto(quantidade=10)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 4}], "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 6)
        mov = self.estoque.movimentos.listar_por_produto(p["id"])[-1]
        self.assertEqual((mov["tipo"], mov["quantidade"], mov["motivo"]), ("saida", -4, f"venda #{v['id']}"))

    def test_venda_e_bloqueada_sem_unidades_e_nada_e_gravado(self):
        p = self.novo_produto(quantidade=2)
        with self.assertRaises(EstoqueInsuficiente):
            self.vendas.registrar([{"produto_id": p["id"], "quantidade": 3}], "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 2)
        self.assertEqual(self.vendas.listar(), [])

    def test_venda_pode_zerar_o_estoque(self):
        p = self.novo_produto(quantidade=3)
        self.vendas.registrar([{"produto_id": p["id"], "quantidade": 3}], "admin")
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 0)

    def test_venda_com_varios_itens_so_vale_se_todos_tiverem_estoque(self):
        a, b = self.novo_produto("A", quantidade=5), self.novo_produto("B", quantidade=1)
        itens = [{"produto_id": a["id"], "quantidade": 2}, {"produto_id": b["id"], "quantidade": 2}]
        with self.assertRaises(EstoqueInsuficiente):
            self.vendas.registrar(itens, "admin")
        self.assertEqual(self.estoque.consultar_quantidade(a["id"]), 5)  # nada foi descontado

    def test_cancelar_venda_devolve_as_unidades(self):
        p = self.novo_produto(quantidade=10)
        v = self.vendas.registrar([{"produto_id": p["id"], "quantidade": 4}], "admin")
        self.vendas.cancelar(v["id"])
        self.assertEqual(self.estoque.consultar_quantidade(p["id"]), 10)


class TestCatalogoDeProdutosDisponiveis(WebTestCase):
    """Catálogo: mostra só produtos com estoque e leva o produto escolhido para a tela de venda."""

    def preparar(self):
        arroz = self.s.produtos.cadastrar("Arroz 5kg", "Alimento", "25,90")
        tv = self.s.produtos.cadastrar("Televisão", "Eletrônico", "1999")
        camisa = self.s.produtos.cadastrar("Camisa", "Vestuário", "59,90")  # ficará sem estoque
        for p, q in ((arroz, 10), (tv, 3)):
            self.s.compras.registrar([{"produto_id": p["id"], "quantidade": q, "preco_unitario": "5"}], "admin")
        self.entrar()
        return arroz, tv, camisa

    def test_catalogo_mostra_apenas_produtos_com_estoque(self):
        arroz, tv, camisa = self.preparar()
        html = self.texto(self.client.get("/catalogo"))
        self.assertIn(f'id="produto-card-{arroz["id"]}"', html)
        self.assertIn(f'id="produto-card-{tv["id"]}"', html)
        self.assertNotIn(f'id="produto-card-{camisa["id"]}"', html)
        self.assertIn("1 produto(s) sem estoque", html)

    def test_catalogo_filtra_por_tipo(self):
        arroz, tv, _ = self.preparar()
        html = self.texto(self.client.get("/catalogo?tipo=Eletrônico"))
        self.assertIn(f'id="produto-card-{tv["id"]}"', html)
        self.assertNotIn(f'id="produto-card-{arroz["id"]}"', html)

    def test_tipo_invalido_no_filtro_e_ignorado(self):
        arroz, tv, _ = self.preparar()
        html = self.texto(self.client.get("/catalogo?tipo=Inexistente"))
        self.assertIn(f'id="produto-card-{arroz["id"]}"', html)
        self.assertIn(f'id="produto-card-{tv["id"]}"', html)

    def test_catalogo_some_de_estoque_zerado_depois_da_venda(self):
        _, tv, _ = self.preparar()
        self.s.vendas.registrar([{"produto_id": tv["id"], "quantidade": 3}], "admin")
        html = self.texto(self.client.get("/catalogo"))
        self.assertNotIn(f'id="produto-card-{tv["id"]}"', html)

    def test_botao_vender_escolhe_o_produto_na_tela_de_venda(self):
        arroz, tv, _ = self.preparar()
        html = self.texto(self.client.get(f'/vendas?produto={tv["id"]}'))
        self.assertIn(f'<option value="{tv["id"]}" selected>', html)
        self.assertNotIn(f'<option value="{arroz["id"]}" selected>', html)

    def test_catalogo_vazio_mostra_mensagem(self):
        self.entrar()
        self.assertIn('id="catalogo-vazio"', self.texto(self.client.get("/catalogo")))

    def test_usuario_comum_acessa_o_catalogo(self):
        self.preparar()
        cliente = self.cliente_comum()
        self.assertEqual(cliente.get("/catalogo").status_code, 200)

    def test_catalogo_exige_login(self):
        resposta = self.client.get("/catalogo")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login", resposta.headers["Location"])
