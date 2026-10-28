"""Integração web das melhorias: CSRF, limite de login, cabeçalhos, senha, itens múltiplos, CSV, auditoria."""
import re
from datetime import date

from sistema.app import criar_app
from tests.base import WebTestCase


class WebCsrfTestCase(WebTestCase):
    """Igual ao WebTestCase, mas com a proteção CSRF LIGADA (como em produção)."""

    def setUp(self):
        self.app = criar_app()
        self.app.config["TESTING"] = True
        self.app.config["CSRF_NOS_TESTES"] = True
        self.s = self.app.extensions["sistema"]
        self.client = self.app.test_client()

    def token(self, client=None, rota="/login"):
        html = (client or self.client).get(rota).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


class TestCsrf(WebCsrfTestCase):
    def test_post_sem_token_e_recusado(self):
        r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "admin123"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Requisição recusada", self.texto(r))

    def test_post_com_token_errado_e_recusado(self):
        self.token()
        r = self.client.post("/login", data={"email": "a@b.com", "senha": "x", "csrf_token": "falso"})
        self.assertEqual(r.status_code, 400)

    def test_login_com_token_certo_funciona_e_acoes_exigem_token(self):
        t = self.token()
        r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "admin123", "csrf_token": t},
                             follow_redirects=True)
        self.assertIn("btn-sair", self.texto(r))
        # logado: um POST sem token (ataque vindo de outro site) não remove nada
        self.s.produtos.cadastrar("Arroz", "Alimento", "5")
        r = self.client.post("/produtos/1/remover")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.s.produtos.listar()), 1)
        # com o token da página, funciona
        t = self.token(rota="/produtos")
        r = self.client.post("/produtos/1/remover", data={"csrf_token": t}, follow_redirects=True)
        self.assertIn("Produto removido", self.texto(r))

    def test_todo_formulario_post_da_tela_traz_o_token(self):
        t = self.token()
        self.client.post("/login", data={"email": "admin@sistema.com", "senha": "admin123", "csrf_token": t})
        self.s.produtos.cadastrar("Arroz", "Alimento", "5")
        for rota in ["/usuarios", "/produtos", "/compras", "/vendas", "/conta/senha", "/produtos/1/editar"]:
            html = self.texto(self.client.get(rota))
            for form in re.findall(r"<form[^>]*method=\"post\".*?</form>", html, flags=re.S):
                self.assertIn('name="csrf_token"', form, f"{rota}: formulário sem token")
        html = self.texto(self.client.get("/"))
        self.assertIn('name="csrf_token"', html)  # botão Sair


class TestLimiteDeLogin(WebTestCase):
    def test_bloqueia_depois_de_5_senhas_erradas(self):
        for _ in range(5):
            r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "errada"})
            self.assertEqual(r.status_code, 200)
        r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "admin123"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Muitas tentativas", self.texto(r))
        self.assertNotIn("btn-sair", self.texto(r))

    def test_acerto_zera_a_contagem(self):
        for _ in range(4):
            self.client.post("/login", data={"email": "admin@sistema.com", "senha": "errada"})
        self.entrar()
        self.client.post("/logout")
        for _ in range(4):
            r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "errada"})
            self.assertEqual(r.status_code, 200)

    def test_falhas_ficam_na_auditoria(self):
        self.client.post("/login", data={"email": "alguem@x.com", "senha": "errada"})
        acoes = [r["acao"] for r in self.s.auditoria.listar()]
        self.assertIn("login_falhou", acoes)


class TestCabecalhosECookies(WebTestCase):
    def test_cabecalhos_de_seguranca(self):
        r = self.client.get("/login")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_cookie_de_sessao_e_httponly_e_samesite(self):
        r = self.client.post("/login", data={"email": "admin@sistema.com", "senha": "admin123"})
        cookie = r.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_nao_ha_script_ou_estilo_inline_nas_telas(self):
        self.entrar()
        for rota in ["/", "/produtos", "/vendas", "/compras", "/estoque", "/catalogo", "/relatorios", "/auditoria"]:
            html = self.texto(self.client.get(rota))
            self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)")
            self.assertNotIn(" style=", html)
            self.assertNotRegex(html, r"\son(click|submit|load)=")

    def test_paginas_de_erro_personalizadas(self):
        r = self.client.get("/nao-existe")
        self.assertEqual(r.status_code, 404)
        self.assertIn("Página não encontrada", self.texto(r))
        r = self.client.get("/logout")
        self.assertEqual(r.status_code, 405)


class TestTrocaDeSenhaObrigatoria(WebTestCase):
    def setUp(self):
        self.app = criar_app(exigir_troca_senha=True)
        self.app.config["TESTING"] = True
        self.s = self.app.extensions["sistema"]
        self.client = self.app.test_client()

    def test_admin_novo_e_levado_para_a_troca(self):
        r = self.entrar()
        self.assertIn("Esta é a senha inicial", self.texto(r))
        r = self.client.get("/produtos")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/conta/senha"))

    def test_depois_de_trocar_entra_com_a_nova_senha(self):
        self.entrar()
        r = self.post("/conta/senha", {"senha_atual": "admin123", "senha_nova": "Outra#Senha9",
                                       "senha_confirmacao": "Outra#Senha9"})
        self.assertIn("Senha alterada", self.texto(r))
        self.assertIn("btn-entrar", self.texto(r))
        r = self.entrar(senha="Outra#Senha9")
        self.assertIn("btn-sair", self.texto(r))
        self.assertEqual(self.client.get("/produtos").status_code, 200)

    def test_confirmacao_diferente_e_senha_atual_errada(self):
        self.entrar()
        r = self.post("/conta/senha", {"senha_atual": "admin123", "senha_nova": "Outra#Senha9", "senha_confirmacao": "x"})
        self.assertIn("confirmação não é igual", self.texto(r))
        r = self.post("/conta/senha", {"senha_atual": "errada", "senha_nova": "Outra#Senha9", "senha_confirmacao": "Outra#Senha9"})
        self.assertIn("senha atual está incorreta", self.texto(r))

    def test_sair_continua_liberado(self):
        self.entrar()
        r = self.client.post("/logout", follow_redirects=True)
        self.assertIn("Você saiu", self.texto(r))


class TestSecretKey(WebTestCase):
    def test_chave_informada_e_usada_e_sem_chave_gera_aleatoria(self):
        a = criar_app(secret_key="minha-chave")
        b, c = criar_app(), criar_app()
        self.assertEqual(a.secret_key, "minha-chave")
        self.assertNotEqual(b.secret_key, c.secret_key)
        self.assertNotEqual(b.secret_key, "chave-de-desenvolvimento")
        for app in (a, b, c):
            app.extensions["sistema"].banco.fechar()


class TestEditarProdutoWeb(WebTestCase):
    def test_admin_edita_e_ve_o_novo_valor(self):
        self.entrar()
        self.s.produtos.cadastrar("Arroz", "Alimento", "5")
        tela = self.texto(self.client.get("/produtos/1/editar"))
        self.assertIn('value="Arroz"', tela)
        self.assertIn('value="5,00"', tela)
        r = self.post("/produtos/1/editar", {"nome": "Arroz Integral", "tipo": "Alimento", "preco": "7,50", "estoque_minimo": "3"})
        html = self.texto(r)
        self.assertIn("Produto atualizado", html)
        self.assertIn("Arroz Integral", html)
        self.assertIn("R$ 7,50", html)

    def test_erro_de_validacao_mantem_o_formulario(self):
        self.entrar()
        self.s.produtos.cadastrar("Arroz", "Alimento", "5")
        r = self.post("/produtos/1/editar", {"nome": "", "tipo": "Alimento", "preco": "5", "estoque_minimo": "0"})
        self.assertIn("Informe o nome", self.texto(r))
        self.assertEqual(self.s.produtos.buscar_por_id(1)["nome"], "Arroz")

    def test_comum_nao_edita(self):
        self.s.produtos.cadastrar("Arroz", "Alimento", "5")
        comum = self.cliente_comum()
        self.assertEqual(comum.get("/produtos/1/editar").status_code, 403)
        self.assertEqual(comum.post("/produtos/1/editar", data={"nome": "X"}).status_code, 403)

    def test_produto_inexistente(self):
        self.entrar()
        r = self.client.get("/produtos/99/editar", follow_redirects=True)
        self.assertIn("Produto não encontrado", self.texto(r))


class TestVariosItens(WebTestCase):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.a = self.s.produtos.cadastrar("Arroz", "Alimento", "10")["id"]
        self.b = self.s.produtos.cadastrar("Fone", "Eletrônico", "50")["id"]

    def test_compra_com_dois_produtos_de_uma_vez(self):
        r = self.post("/compras", {"produto_id": [self.a, self.b], "quantidade": ["10", "4"], "preco_unitario": ["5", "30"]})
        self.assertIn("Compra registrada", self.texto(r))
        compra = self.s.compras.listar()[0]
        self.assertEqual(len(compra["itens"]), 2)
        self.assertEqual(compra["total"], 10 * 5 + 4 * 30)
        self.assertEqual(self.quantidade_na_tela(self.b), 4)

    def test_venda_com_dois_produtos_e_linha_em_branco_ignorada(self):
        self.s.compras.registrar([{"produto_id": self.a, "quantidade": 10, "preco_unitario": "1"},
                                  {"produto_id": self.b, "quantidade": 10, "preco_unitario": "1"}], "admin")
        r = self.post("/vendas", {"produto_id": [self.a, self.b, ""], "quantidade": ["2", "3", ""]})
        self.assertIn("Venda registrada", self.texto(r))
        venda = self.s.vendas.listar()[0]
        self.assertEqual(venda["total"], 2 * 10 + 3 * 50)
        self.assertEqual(self.quantidade_na_tela(self.a), 8)

    def test_venda_com_um_item_sem_estoque_nao_grava_nada(self):
        self.s.compras.registrar([{"produto_id": self.a, "quantidade": 10, "preco_unitario": "1"}], "admin")
        r = self.post("/vendas", {"produto_id": [self.a, self.b], "quantidade": ["2", "3"]})
        self.assertIn("Estoque insuficiente", self.texto(r))
        self.assertEqual(self.s.vendas.listar(), [])
        self.assertEqual(self.quantidade_na_tela(self.a), 10)

    def test_formulario_vazio_mostra_mensagem_de_validacao(self):
        r = self.post("/vendas", {"produto_id": "", "quantidade": ""})
        self.assertIn("Selecione um produto", self.texto(r))

    def test_botao_de_adicionar_item_existe_e_o_script_e_externo(self):
        html = self.texto(self.client.get("/vendas"))
        self.assertIn('id="btn-adicionar-item"', html)
        self.assertIn("/static/app.js", html)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)


class TestPaginacao(WebTestCase):
    def test_paginas_de_vendas(self):
        self.entrar()
        p = self.s.produtos.cadastrar("Arroz", "Alimento", "1")
        self.s.compras.registrar([{"produto_id": p["id"], "quantidade": 100, "preco_unitario": "1"}], "admin")
        for _ in range(20):
            self.s.vendas.registrar([{"produto_id": p["id"], "quantidade": 1}], "admin")
        p1 = self.texto(self.client.get("/vendas"))
        self.assertIn("Página 1 de 2", p1)
        self.assertIn('id="linha-venda-20"', p1)
        self.assertNotIn('id="linha-venda-1"', p1)
        p2 = self.texto(self.client.get("/vendas?pagina=2"))
        self.assertIn('id="linha-venda-1"', p2)
        # página fora do limite cai na última; valor inválido cai na primeira
        self.assertIn("Página 2 de 2", self.texto(self.client.get("/vendas?pagina=99")))
        self.assertEqual(self.client.get("/vendas?pagina=abc").status_code, 200)


class TestEstoqueTela(WebTestCase):
    def test_situacao_e_historico(self):
        self.entrar()
        p = self.s.produtos.cadastrar("Arroz", "Alimento", "10", 5)
        html = self.texto(self.client.get("/estoque"))
        self.assertIn("Sem estoque", html)
        self.s.compras.registrar([{"produto_id": p["id"], "quantidade": 3, "preco_unitario": "1"}], "admin")
        self.assertIn("Abaixo do mínimo (5)", self.texto(self.client.get("/estoque")))
        self.s.compras.registrar([{"produto_id": p["id"], "quantidade": 20, "preco_unitario": "1"}], "admin")
        self.assertIn("Normal", self.texto(self.client.get("/estoque")))
        hist = self.texto(self.client.get(f"/estoque/{p['id']}/movimentos"))
        self.assertIn("compra #1", hist)
        self.assertIn("+20", hist)
        self.assertIn('id="quantidade-atual">23<', hist)

    def test_historico_de_produto_inexistente(self):
        self.entrar()
        r = self.client.get("/estoque/99/movimentos", follow_redirects=True)
        self.assertIn("Produto não encontrado", self.texto(r))


class TestPainel(WebTestCase):
    def test_painel_mostra_vendas_estoque_baixo_e_mais_vendidos(self):
        self.entrar()
        a = self.s.produtos.cadastrar("Arroz", "Alimento", "10", 50)
        self.s.compras.registrar([{"produto_id": a["id"], "quantidade": 20, "preco_unitario": "1"}], "admin")
        self.s.vendas.registrar([{"produto_id": a["id"], "quantidade": 4}], "admin")
        html = self.texto(self.client.get("/"))
        self.assertIn('id="vendas-hoje">R$ 40,00<', html)
        self.assertIn('id="vendas-mes">R$ 40,00<', html)
        self.assertIn('id="valor-estoque">R$ 160,00<', html)  # 16 un. x R$ 10
        self.assertIn("Arroz", html.split('id="alerta-estoque"')[1])
        self.assertIn("4 un.", html.split('id="mais-vendidos"')[1])

    def test_venda_cancelada_nao_conta_no_painel(self):
        self.entrar()
        a = self.s.produtos.cadastrar("Arroz", "Alimento", "10")
        self.s.compras.registrar([{"produto_id": a["id"], "quantidade": 20, "preco_unitario": "1"}], "admin")
        v = self.s.vendas.registrar([{"produto_id": a["id"], "quantidade": 4}], "admin")
        self.s.vendas.cancelar(v["id"])
        html = self.texto(self.client.get("/"))
        self.assertIn('id="vendas-hoje">R$ 0,00<', html)
        self.assertIn('id="total-vendas">0<', html)


class TestRelatoriosECsv(WebTestCase):
    def setUp(self):
        super().setUp()
        self.entrar()
        self.p = self.s.produtos.cadastrar("Arroz", "Alimento", "10")
        self.s.compras.registrar([{"produto_id": self.p["id"], "quantidade": 50, "preco_unitario": "1"}], "admin")
        self.s.vendas.registrar([{"produto_id": self.p["id"], "quantidade": 3}], "admin")
        v2 = self.s.vendas.registrar([{"produto_id": self.p["id"], "quantidade": 2}], "admin")
        self.s.vendas.cancelar(v2["id"])

    def test_relatorio_do_periodo(self):
        hoje = date.today().isoformat()
        html = self.texto(self.client.get(f"/relatorios?inicio={hoje}&fim={hoje}"))
        self.assertIn('id="rel-total">R$ 30,00<', html)
        self.assertIn('id="rel-quantidade">1<', html)
        self.assertIn('id="rel-canceladas">1<', html)

    def test_periodo_sem_vendas(self):
        html = self.texto(self.client.get("/relatorios?inicio=2000-01-01&fim=2000-01-31"))
        self.assertIn("Nenhuma venda no período", html)

    def test_datas_invalidas_nao_quebram(self):
        for qs in ["inicio=abc", "inicio=2026-12-31&fim=2026-01-01"]:
            r = self.client.get(f"/relatorios?{qs}")
            self.assertEqual(r.status_code, 200)
            self.assertIn("mensagem erro", self.texto(r))
        r = self.client.get("/relatorios/vendas.csv?inicio=abc", follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_csv_de_vendas_e_de_estoque(self):
        r = self.client.get("/relatorios/vendas.csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r.headers["Content-Type"])
        self.assertIn("attachment", r.headers["Content-Disposition"])
        linhas = self.texto(r).lstrip("﻿").splitlines()
        self.assertEqual(linhas[0], "Venda;Data;Status;Usuario;Produto;Quantidade;Preco unitario;Subtotal")
        self.assertTrue(any("Arroz;3;10,00;30,00" in l and "concluida" in l for l in linhas))
        self.assertTrue(any("cancelada" in l for l in linhas))
        est = self.texto(self.client.get("/relatorios/estoque.csv")).lstrip("﻿").splitlines()
        self.assertEqual(est[1].split(";")[1:5], ["Arroz", "Alimento", "10,00", "47"])

    def test_csv_protege_contra_injecao_de_formula(self):
        self.s.produtos.cadastrar("=HYPERLINK(\"http://x\")", "Alimento", "1")
        est = self.texto(self.client.get("/relatorios/estoque.csv"))
        self.assertIn("'=HYPERLINK", est)
        self.assertNotIn(";=HYPERLINK", est)

    def test_so_admin_ve_relatorios_e_auditoria(self):
        comum = self.cliente_comum()
        for rota in ["/relatorios", "/relatorios/vendas.csv", "/relatorios/estoque.csv", "/auditoria"]:
            self.assertEqual(comum.get(rota).status_code, 403, rota)


class TestAuditoriaWeb(WebTestCase):
    def test_acoes_importantes_ficam_registradas(self):
        self.entrar()
        self.post("/produtos", {"nome": "Arroz", "tipo": "Alimento", "preco": "5"})
        self.post("/produtos/1/editar", {"nome": "Arroz", "tipo": "Alimento", "preco": "6", "estoque_minimo": "0"})
        self.post("/compras", {"produto_id": "1", "quantidade": "5", "preco_unitario": "1"})
        self.post("/vendas", {"produto_id": "1", "quantidade": "2"})
        self.post("/vendas/1/cancelar")
        self.post("/produtos/1/remover")
        self.post("/usuarios", {"id": "ana", "nome_completo": "Ana Lima", "email": "ana@x.com",
                                "telefone": "(11) 91234-5678", "senha": "abc12345", "perfil": "comum"})
        self.post("/usuarios/ana/remover")
        acoes = [r["acao"] for r in self.s.auditoria.listar(limite=50)]
        for esperada in ["login", "produto_cadastrado", "produto_editado", "compra_registrada", "venda_registrada",
                         "venda_cancelada", "produto_removido", "usuario_cadastrado", "usuario_removido"]:
            self.assertIn(esperada, acoes)
        html = self.texto(self.client.get("/auditoria"))
        self.assertIn("Venda cancelada", html)

    def test_operacao_que_falha_nao_e_auditada(self):
        self.entrar()
        self.post("/vendas", {"produto_id": "", "quantidade": ""})
        self.assertNotIn("venda_registrada", [r["acao"] for r in self.s.auditoria.listar()])

    def test_detalhe_da_auditoria_e_escapado(self):
        self.entrar()
        self.post("/produtos", {"nome": "<script>alert(1)</script>", "tipo": "Alimento", "preco": "5"})
        html = self.texto(self.client.get("/auditoria"))
        self.assertNotIn("<script>alert(1)", html)


class TestMenuAtivo(WebTestCase):
    def test_pagina_atual_fica_marcada(self):
        self.entrar()
        html = self.texto(self.client.get("/vendas"))
        self.assertRegex(html, r'id="menu-vendas" class="ativo"')
        self.assertNotRegex(html, r'id="menu-compras" class="ativo"')

    def test_comum_nao_ve_menus_de_admin(self):
        comum = self.cliente_comum()
        html = self.texto(comum.get("/"))
        self.assertNotIn("menu-relatorios", html)
        self.assertNotIn("menu-auditoria", html)
        self.assertNotIn("menu-usuarios", html)
