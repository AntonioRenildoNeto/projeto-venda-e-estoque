"""Automação do tipo macro (Selenium + Python).

Abre o navegador e repete, sozinho, o que uma pessoa faria na tela do sistema:
login, cadastro e remoção de usuário, cadastro e remoção de produto, compra,
venda e conferência do estoque.

Como rodar (na pasta do projeto):

    pip install selenium
    python automacao/macro_selenium.py                  # abre o Chrome e mostra a macro
    HEADLESS=1 python automacao/macro_selenium.py       # sem abrir a janela
    PAUSA=1 python automacao/macro_selenium.py          # mais devagar (segundos entre ações)
    BASE_URL=http://127.0.0.1:5000 python automacao/macro_selenium.py   # usa um sistema já em execução

Sem BASE_URL, a macro sobe uma cópia própria do sistema (banco em memória),
então não mexe nos dados reais. Precisa do Google Chrome instalado.
Divisão (ver relatório): Antonio = login e usuários, Arthur = produtos e estoque,
Laerte = compra e venda.
"""
import os
import sys
import threading
import time
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from selenium import webdriver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import Select, WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from sistema.app import criar_app  # noqa: E402

HEADLESS = os.environ.get("HEADLESS") == "1"
PAUSA = float(os.environ.get("PAUSA", "0" if HEADLESS else "0.4"))
BASE_URL_EXTERNA = os.environ.get("BASE_URL", "").rstrip("/")
ADMIN_EMAIL, ADMIN_SENHA = "admin@sistema.com", "admin123"


class MacroBase(unittest.TestCase):
    driver = None

    @classmethod
    def setUpClass(cls):
        opcoes = webdriver.ChromeOptions()
        if HEADLESS:
            for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage"):
                opcoes.add_argument(arg)
        opcoes.add_argument("--window-size=1280,900")
        cls.driver = webdriver.Chrome(options=opcoes)
        cls.espera = WebDriverWait(cls.driver, 10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def setUp(self):
        self.servidor = None
        if BASE_URL_EXTERNA:
            self.base = BASE_URL_EXTERNA
        else:
            app = criar_app()  # banco em memória, novo a cada macro
            self.servidor = make_server("127.0.0.1", 0, app, threaded=False)
            self.base = f"http://127.0.0.1:{self.servidor.server_port}"
            threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.sufixo = str(int(time.time() * 1000))[-6:]
        self.driver.delete_all_cookies()

    def tearDown(self):
        if self.servidor:
            self.servidor.shutdown()

    # ---- ações básicas da macro -------------------------------------------------
    def pausa(self):
        time.sleep(PAUSA)

    def abrir(self, caminho):
        self.driver.get(self.base + caminho)
        self.pausa()

    def preencher(self, campo_id, texto):
        campo = self.espera.until(EC.visibility_of_element_located((By.ID, campo_id)))
        campo.clear()
        campo.send_keys(texto)

    def escolher(self, campo_id, texto=None, valor=None):
        select = Select(self.espera.until(EC.presence_of_element_located((By.ID, campo_id))))
        if valor is not None:
            select.select_by_value(str(valor))
        else:
            select.select_by_visible_text(texto)

    def escolher_produto(self, nome):
        opcao = self.driver.find_element(
            By.XPATH, f"//select[@id='produto_id']/option[starts-with(normalize-space(), '{nome}')]"
        )
        Select(self.driver.find_element(By.ID, "produto_id")).select_by_value(opcao.get_attribute("value"))

    def clicar(self, botao_id):
        self.espera.until(EC.element_to_be_clickable((By.ID, botao_id))).click()
        self.pausa()

    def confirmar_alerta(self):
        """Aceita a janela "Tem certeza?" que o sistema mostra antes de remover ou cancelar."""
        self.espera.until(EC.alert_is_present()).accept()
        self.pausa()

    def mensagem(self):
        return self.espera.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".mensagem"))).text

    def texto_da_pagina(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

    def entrar(self, email=ADMIN_EMAIL, senha=ADMIN_SENHA):
        self.abrir("/login")
        self.preencher("email", email)
        self.preencher("senha", senha)
        self.clicar("btn-entrar")

    def cadastrar_produto(self, nome, tipo, preco):
        self.abrir("/produtos")
        self.preencher("nome", nome)
        self.escolher("tipo", texto=tipo)
        self.preencher("preco", preco)
        self.clicar("btn-cadastrar-produto")

    def quantidade_em_estoque(self, nome):
        self.abrir("/estoque")
        celula = self.driver.find_element(
            By.XPATH, f"//table[@id='tabela-estoque']//tr[td[normalize-space()='{nome}']]/td[5]"
        )
        return int(celula.text)


class MacroAntonioLoginEUsuarios(MacroBase):
    """Antonio: tela de login e cadastro/remoção de usuário."""

    def test_login_invalido_e_valido(self):
        self.entrar(senha="senha-errada")
        self.assertIn("E-mail ou senha incorretos", self.mensagem())
        self.assertIn("/login", self.driver.current_url)

        self.entrar()
        self.assertTrue(self.driver.find_element(By.ID, "btn-sair").is_displayed())
        self.assertIn("Olá, Administrador", self.texto_da_pagina())

    def test_cadastro_e_remocao_de_usuario(self):
        uid, email = f"u{self.sufixo}", f"u{self.sufixo}@loja.com"
        self.entrar()
        self.abrir("/usuarios")
        self.preencher("id", uid)
        self.preencher("nome_completo", "Joana Teste Silva")
        self.preencher("email", email)
        self.preencher("telefone", "(11) 91234-5678")
        self.preencher("senha", "senha123")
        self.escolher("perfil", texto="Comum")
        self.clicar("btn-cadastrar-usuario")
        self.assertIn("Usuário cadastrado com sucesso", self.mensagem())
        self.assertIn(email, self.driver.find_element(By.ID, "tabela-usuarios").text)

        self.clicar(f"btn-remover-usuario-{uid}")
        self.confirmar_alerta()
        self.assertIn("Usuário removido com sucesso", self.mensagem())
        self.assertNotIn(email, self.driver.find_element(By.ID, "tabela-usuarios").text)

    def test_usuario_comum_nao_acessa_a_tela_de_usuarios(self):
        uid, email = f"c{self.sufixo}", f"c{self.sufixo}@loja.com"
        self.entrar()
        self.abrir("/usuarios")
        self.preencher("id", uid)
        self.preencher("nome_completo", "Carlos Comum Souza")
        self.preencher("email", email)
        self.preencher("telefone", "11987654321")
        self.preencher("senha", "senha123")
        self.clicar("btn-cadastrar-usuario")
        self.clicar("btn-sair")

        self.entrar(email, "senha123")
        self.abrir("/usuarios")
        self.assertIn("Acesso negado", self.texto_da_pagina())


class MacroArthurProdutosEEstoque(MacroBase):
    """Arthur: cadastro/remoção de produtos (3 tipos) e conferência do estoque."""

    def test_cadastro_dos_tres_tipos_e_remocao(self):
        self.entrar()
        itens = [(f"Arroz {self.sufixo}", "Alimento", "25,90"),
                 (f"Fone {self.sufixo}", "Eletrônico", "120,00"),
                 (f"Camiseta {self.sufixo}", "Vestuário", "39,90")]
        for nome, tipo, preco in itens:
            self.cadastrar_produto(nome, tipo, preco)
            self.assertIn("Produto cadastrado com sucesso", self.mensagem())
        tabela = self.driver.find_element(By.ID, "tabela-produtos").text
        for nome, tipo, _ in itens:
            self.assertIn(nome, tabela)
            self.assertIn(tipo, tabela)

        nome_removido = itens[0][0]
        linha = self.driver.find_element(By.XPATH, f"//tr[td[normalize-space()='{nome_removido}']]")
        linha.find_element(By.XPATH, ".//button[starts-with(@id, 'btn-remover-produto-')]").click()
        self.confirmar_alerta()
        self.pausa()
        self.assertIn("Produto removido com sucesso", self.mensagem())
        self.assertNotIn(nome_removido, self.driver.find_element(By.ID, "tabela-produtos").text)
        self.assertEqual(self.quantidade_em_estoque(itens[1][0]), 0)

    def test_produto_com_dados_invalidos_e_recusado(self):
        self.entrar()
        self.cadastrar_produto(f"Ruim {self.sufixo}", "Alimento", "-5")
        self.assertIn("preço deve ser maior que zero", self.mensagem())


class MacroLaerteCompraEVenda(MacroBase):
    """Laerte: compra, venda e atualização do estoque."""

    def test_compra_venda_cancelamento_e_estoque(self):
        nome = f"Produto {self.sufixo}"
        self.entrar()
        self.cadastrar_produto(nome, "Eletrônico", "100,00")
        self.assertEqual(self.quantidade_em_estoque(nome), 0)

        self.abrir("/compras")
        self.escolher_produto(nome)
        self.preencher("quantidade", "10")
        self.preencher("preco_unitario", "70")
        self.clicar("btn-registrar-compra")
        self.assertIn("Compra registrada", self.mensagem())
        self.assertIn("R$ 700,00", self.driver.find_element(By.ID, "tabela-compras").text)
        self.assertEqual(self.quantidade_em_estoque(nome), 10)

        self.abrir("/vendas")
        self.escolher_produto(nome)
        self.preencher("quantidade", "3")
        self.clicar("btn-registrar-venda")
        self.assertIn("Venda registrada", self.mensagem())
        self.assertIn("R$ 300,00", self.driver.find_element(By.ID, "tabela-vendas").text)
        self.assertEqual(self.quantidade_em_estoque(nome), 7)

        self.abrir("/vendas")
        self.escolher_produto(nome)
        self.preencher("quantidade", "50")
        self.clicar("btn-registrar-venda")
        self.assertIn("Estoque insuficiente", self.mensagem())
        self.assertEqual(self.quantidade_em_estoque(nome), 7)

        self.abrir("/vendas")
        botao = self.driver.find_element(By.XPATH, "//button[starts-with(@id, 'btn-cancelar-venda-')]")
        botao.click()
        self.confirmar_alerta()
        self.pausa()
        self.assertIn("Venda cancelada", self.mensagem())
        self.assertEqual(self.quantidade_em_estoque(nome), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
