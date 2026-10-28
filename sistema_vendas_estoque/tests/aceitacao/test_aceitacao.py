"""Testes de aceitação: cada requisito da atividade vira um roteiro, aprovado ou reprovado.

Responsáveis (relatório, seção 7): Antonio = REQ-01 a 04, Arthur = REQ-05, 06 e 08, Laerte = REQ-07.

REQ-01  Tela de Login
REQ-02  Usuário Admin
REQ-03  Cadastro de usuário (Nome completo, ID, E-mail, Telefone)
REQ-04  Remoção de usuário
REQ-05  Cadastro de produtos (3 tipos)
REQ-06  Remoção de produtos
REQ-07  Compra e Venda
REQ-08  Atualização de estoque
"""
from tests.base import USUARIO_COMUM, WebTestCase


class TestAceitacao(WebTestCase):
    def test_req01_tela_de_login(self):
        """Quem não está logado vê a tela de login; com dados certos entra, com dados errados não."""
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)  # redireciona para o login
        tela = self.texto(self.client.get("/login"))
        for campo in ['id="email"', 'id="senha"', 'id="btn-entrar"']:
            self.assertIn(campo, tela)

        errado = self.entrar(senha="errada")
        self.assertIn("E-mail ou senha incorretos", self.texto(errado))
        self.assertNotIn("btn-sair", self.texto(errado))

        certo = self.entrar()
        self.assertIn("btn-sair", self.texto(certo))

    def test_req02_usuario_admin(self):
        """Existe um usuário Admin com acesso às telas de administração; o usuário comum não tem."""
        admin = self.s.usuarios.buscar_por_id("admin")
        self.assertEqual(admin["perfil"], "admin")
        self.entrar()
        self.assertEqual(self.client.get("/usuarios").status_code, 200)
        comum = self.cliente_comum()
        self.assertEqual(comum.get("/usuarios").status_code, 403)
        self.assertIn("apenas para o Admin", self.texto(comum.get("/usuarios")))

    def test_req03_cadastro_de_usuario(self):
        """O Admin cadastra um usuário informando Nome completo, ID, E-mail e Telefone."""
        self.entrar()
        tela = self.texto(self.client.get("/usuarios"))
        for campo in ["nome_completo", 'id="id"', 'id="email"', 'id="telefone"']:
            self.assertIn(campo, tela)
        r = self.post("/usuarios", {
            "id": "joao.silva", "nome_completo": "João da Silva", "email": "joao@loja.com",
            "telefone": "(21) 98765-4321", "senha": "abc12345", "perfil": "comum",
        })
        html = self.texto(r)
        self.assertIn("Usuário cadastrado com sucesso", html)
        for dado in ["joao.silva", "João da Silva", "joao@loja.com", "(21) 98765-4321"]:
            self.assertIn(dado, html)

    def test_req03_cadastro_recusa_dados_invalidos(self):
        self.entrar()
        r = self.post("/usuarios", {"id": "x", "nome_completo": "Só Nome", "email": "email-ruim",
                                    "telefone": "123", "senha": "abc12345"})
        self.assertIn("E-mail inválido", self.texto(r))
        self.assertIsNone(self.s.usuarios.buscar_por_id("x"))

    def test_req04_remocao_de_usuario(self):
        """O Admin remove um usuário e ele deixa de aparecer e de conseguir entrar."""
        self.criar_usuario_comum()
        self.entrar()
        r = self.post(f"/usuarios/{USUARIO_COMUM['id']}/remover")
        self.assertIn("Usuário removido com sucesso", self.texto(r))
        self.assertNotIn("maria@loja.com", self.texto(r))
        outro = self.app.test_client()
        self.assertIn("E-mail ou senha incorretos", self.texto(self.entrar(USUARIO_COMUM["email"], USUARIO_COMUM["senha"], outro)))

    def test_req04_admin_nao_remove_a_si_mesmo(self):
        self.entrar()
        r = self.post("/usuarios/admin/remover")
        self.assertIn("não pode remover", self.texto(r))
        self.assertIsNotNone(self.s.usuarios.buscar_por_id("admin"))

    def test_req05_cadastro_de_produtos_com_tres_tipos(self):
        """O Admin cadastra produtos dos três tipos; outro tipo não é aceito."""
        self.entrar()
        tela = self.texto(self.client.get("/produtos"))
        for tipo in ["Alimento", "Eletrônico", "Vestuário"]:
            self.assertIn(f'<option value="{tipo}">', tela)
            r = self.post("/produtos", {"nome": f"Item {tipo}", "tipo": tipo, "preco": "10,00"})
            self.assertIn(f"Item {tipo}", self.texto(r))
        r = self.post("/produtos", {"nome": "Item X", "tipo": "Brinquedo", "preco": "10"})
        self.assertIn("Tipo de produto inválido", self.texto(r))
        self.assertEqual(len(self.s.produtos.listar()), 3)

    def test_req06_remocao_de_produtos(self):
        """O Admin remove um produto e ele some da lista e do estoque."""
        p = self.s.produtos.cadastrar("Arroz", "Alimento", "20")
        self.entrar()
        r = self.post(f"/produtos/{p['id']}/remover")
        self.assertIn("Produto removido com sucesso", self.texto(r))
        self.assertNotIn("Arroz", self.texto(r))
        self.assertNotIn("Arroz", self.texto(self.client.get("/estoque")))

    def test_req07_compra_e_venda(self):
        """É possível comprar (repor) e vender produtos; o total é calculado."""
        p = self.s.produtos.cadastrar("Fone", "Eletrônico", "100")
        self.entrar()
        r = self.post("/compras", {"produto_id": p["id"], "quantidade": 10, "preco_unitario": "70"})
        self.assertIn("Compra registrada", self.texto(r))
        self.assertIn("R$ 700,00", self.texto(r))
        r = self.post("/vendas", {"produto_id": p["id"], "quantidade": 3})
        self.assertIn("Venda registrada", self.texto(r))
        self.assertIn("R$ 300,00", self.texto(r))

    def test_req07_nao_vende_mais_do_que_tem(self):
        p = self.s.produtos.cadastrar("Fone", "Eletrônico", "100")
        self.entrar()
        r = self.post("/vendas", {"produto_id": p["id"], "quantidade": 1})
        self.assertIn("Estoque insuficiente", self.texto(r))

    def test_req08_atualizacao_de_estoque(self):
        """O estoque sobe com a compra, desce com a venda e volta com o cancelamento."""
        p = self.s.produtos.cadastrar("Camiseta", "Vestuário", "40")
        self.entrar()
        self.assertEqual(self.quantidade_na_tela(p["id"]), 0)
        self.post("/compras", {"produto_id": p["id"], "quantidade": 20, "preco_unitario": "25"})
        self.assertEqual(self.quantidade_na_tela(p["id"]), 20)
        self.post("/vendas", {"produto_id": p["id"], "quantidade": 6})
        self.assertEqual(self.quantidade_na_tela(p["id"]), 14)
        venda = self.s.vendas.listar()[0]
        self.post(f"/vendas/{venda['id']}/cancelar")
        self.assertEqual(self.quantidade_na_tela(p["id"]), 20)
