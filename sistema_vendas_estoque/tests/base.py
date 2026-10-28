"""Classes e funções de apoio compartilhadas pelas suítes de teste."""
import re
import unittest

from sistema.app import criar_app
from sistema.autenticacao.autenticador import Autenticador
from sistema.autenticacao.sessao import Sessao
from sistema.banco import Banco
from sistema.compra_venda.compra import Compra
from sistema.compra_venda.venda import Venda
from sistema.estoque.estoque import Estoque
from sistema.inicializacao import ADMIN_PADRAO, criar_admin_padrao
from sistema.produtos.produto import Produto
from sistema.usuarios.usuario import Usuario

USUARIO_COMUM = {
    "id": "maria01",
    "nome_completo": "Maria Souza",
    "email": "maria@loja.com",
    "telefone": "(11) 91234-5678",
    "senha": "senha123",
    "perfil": "comum",
}


class ModulosTestCase(unittest.TestCase):
    """Cria um banco em memória novo (com o Admin) e os objetos dos módulos."""

    def setUp(self):
        self.banco = Banco()
        criar_admin_padrao(self.banco)
        self.sessao = Sessao(self.banco)
        self.autenticador = Autenticador(self.banco, self.sessao)
        self.usuarios = Usuario(self.banco)
        self.produtos = Produto(self.banco)
        self.estoque = Estoque(self.banco)
        self.compras = Compra(self.banco)
        self.vendas = Venda(self.banco)

    def tearDown(self):
        self.banco.fechar()

    def novo_produto(self, nome="Arroz 5kg", tipo="Alimento", preco="25,90", quantidade=0):
        produto = self.produtos.cadastrar(nome, tipo, preco)
        if quantidade:
            self.compras.registrar(
                [{"produto_id": produto["id"], "quantidade": quantidade, "preco_unitario": "10"}], "admin"
            )
        return produto


class WebTestCase(unittest.TestCase):
    """Cria a aplicação web completa (banco em memória) e um navegador de teste."""

    def setUp(self):
        self.app = criar_app()
        self.app.config["TESTING"] = True
        self.s = self.app.extensions["sistema"]
        self.client = self.app.test_client()

    def tearDown(self):
        self.s.banco.fechar()

    def entrar(self, email=ADMIN_PADRAO["email"], senha=ADMIN_PADRAO["senha"], client=None):
        return (client or self.client).post(
            "/login", data={"email": email, "senha": senha}, follow_redirects=True
        )

    def criar_usuario_comum(self):
        return self.s.usuarios.cadastrar(**USUARIO_COMUM)

    def cliente_comum(self):
        """Cria o usuário comum, faz login com ele e devolve o navegador dele."""
        self.criar_usuario_comum()
        cliente = self.app.test_client()
        self.entrar(USUARIO_COMUM["email"], USUARIO_COMUM["senha"], cliente)
        return cliente

    def post(self, rota, dados=None, client=None):
        return (client or self.client).post(rota, data=dados or {}, follow_redirects=True)

    def texto(self, resposta):
        return resposta.get_data(as_text=True)

    def quantidade_na_tela(self, produto_id):
        html = self.texto(self.client.get("/estoque"))
        m = re.search(rf'id="qtd-produto-{produto_id}"[^>]*>\s*(\d+)\s*<', html)
        return int(m.group(1)) if m else None
