"""Testes unitários do módulo Autenticação (Antonio)."""
import unittest

from sistema.autenticacao.funcoes import comparar_senha, gerar_hash_senha, token_expirado
from sistema.autenticacao.sessao import Sessao
from sistema.erros import ErroValidacao
from sistema.inicializacao import ADMIN_PADRAO
from tests.base import ModulosTestCase


class TestFuncoesAutenticacao(unittest.TestCase):
    def test_comparar_senha_correta_e_aceita(self):
        self.assertTrue(comparar_senha("abc123", gerar_hash_senha("abc123")))

    def test_comparar_senha_incorreta_e_recusada(self):
        self.assertFalse(comparar_senha("outra", gerar_hash_senha("abc123")))

    def test_comparar_senha_vazia_ou_hash_invalido_e_recusada(self):
        self.assertFalse(comparar_senha("", gerar_hash_senha("abc123")))
        self.assertFalse(comparar_senha("abc123", ""))
        self.assertFalse(comparar_senha("abc123", "texto-sem-formato"))

    def test_hash_nao_guarda_a_senha_em_texto_puro(self):
        self.assertNotIn("abc123", gerar_hash_senha("abc123"))

    def test_mesma_senha_gera_hashes_diferentes(self):
        self.assertNotEqual(gerar_hash_senha("abc123"), gerar_hash_senha("abc123"))

    def test_token_expirado(self):
        self.assertFalse(token_expirado(expira_em=100, agora=99))
        self.assertTrue(token_expirado(expira_em=100, agora=100))
        self.assertTrue(token_expirado(expira_em=100, agora=500))


class TestAutenticador(ModulosTestCase):
    def test_validar_senha(self):
        hash_ = gerar_hash_senha("segredo")
        self.assertTrue(self.autenticador.validar_senha("segredo", hash_))
        self.assertFalse(self.autenticador.validar_senha("errada", hash_))

    def test_login_com_credenciais_corretas_devolve_token(self):
        token = self.autenticador.login(ADMIN_PADRAO["email"], ADMIN_PADRAO["senha"])
        self.assertTrue(token)

    def test_login_aceita_email_com_maiusculas_e_espacos(self):
        token = self.autenticador.login("  ADMIN@Sistema.com ", ADMIN_PADRAO["senha"])
        self.assertTrue(token)

    def test_login_com_senha_errada_e_recusado(self):
        with self.assertRaises(ErroValidacao):
            self.autenticador.login(ADMIN_PADRAO["email"], "senha-errada")

    def test_login_com_email_inexistente_e_recusado(self):
        with self.assertRaises(ErroValidacao):
            self.autenticador.login("ninguem@loja.com", "123456")

    def test_login_com_campos_vazios_e_recusado(self):
        with self.assertRaises(ErroValidacao):
            self.autenticador.login("", "")

    def test_mensagem_de_erro_nao_revela_se_o_email_existe(self):
        with self.assertRaises(ErroValidacao) as a:
            self.autenticador.login(ADMIN_PADRAO["email"], "errada")
        with self.assertRaises(ErroValidacao) as b:
            self.autenticador.login("x@y.com", "errada")
        self.assertEqual(str(a.exception), str(b.exception))

    def test_logout_invalida_o_token(self):
        token = self.autenticador.login(ADMIN_PADRAO["email"], ADMIN_PADRAO["senha"])
        self.autenticador.logout(token)
        self.assertIsNone(self.sessao.validar_token(token))


class TestSessao(ModulosTestCase):
    def test_gerar_token_cria_tokens_diferentes(self):
        self.assertNotEqual(self.sessao.gerar_token("admin"), self.sessao.gerar_token("admin"))

    def test_validar_token_devolve_o_usuario(self):
        token = self.sessao.gerar_token("admin")
        usuario = self.sessao.validar_token(token)
        self.assertEqual(usuario["id"], "admin")
        self.assertEqual(usuario["perfil"], "admin")
        self.assertNotIn("senha_hash", usuario)

    def test_token_inexistente_ou_vazio_e_invalido(self):
        self.assertIsNone(self.sessao.validar_token("token-falso"))
        self.assertIsNone(self.sessao.validar_token(""))
        self.assertIsNone(self.sessao.validar_token(None))

    def test_token_expirado_e_rejeitado_e_apagado(self):
        agora = [1000.0]
        sessao = Sessao(self.banco, duracao=60, relogio=lambda: agora[0])
        token = sessao.gerar_token("admin")
        agora[0] = 1059.0
        self.assertIsNotNone(sessao.validar_token(token))
        agora[0] = 1061.0
        self.assertIsNone(sessao.validar_token(token))
        self.assertIsNone(self.banco.consultar_um("SELECT 1 FROM tokens WHERE token = ?", (token,)))


if __name__ == "__main__":
    unittest.main()
