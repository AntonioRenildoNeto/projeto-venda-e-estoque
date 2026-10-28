"""Testes das melhorias de segurança: hash de senha, limitador de login, tokens."""
import os
import unittest
from unittest import mock

from sistema.autenticacao import funcoes
from sistema.autenticacao.funcoes import (
    ITERACOES_PADRAO,
    comparar_senha,
    gerar_hash_senha,
    precisa_atualizar_hash,
)
from sistema.limitador import LimitadorLogin
from tests.base import ModulosTestCase


class TestHashSenha(unittest.TestCase):
    def test_padrao_de_producao_e_forte(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("SENHA_ITERACOES", None)
            self.assertGreaterEqual(ITERACOES_PADRAO, 600_000)
            self.assertEqual(funcoes.iteracoes_atuais(), ITERACOES_PADRAO)

    def test_hash_novo_guarda_formato_e_voltas(self):
        h = gerar_hash_senha("segredo123", iteracoes=2000)
        self.assertTrue(h.startswith("pbkdf2_sha256$2000$"))
        self.assertTrue(comparar_senha("segredo123", h))
        self.assertFalse(comparar_senha("outra", h))

    def test_hash_antigo_sal_dollar_hash_ainda_funciona(self):
        import hashlib
        sal = "abcdef"
        antigo = f"{sal}${hashlib.pbkdf2_hmac('sha256', b'velha123', sal.encode(), 60_000).hex()}"
        self.assertTrue(comparar_senha("velha123", antigo))
        self.assertFalse(comparar_senha("errada", antigo))
        self.assertTrue(precisa_atualizar_hash(antigo))

    def test_hash_corrompido_nao_quebra(self):
        self.assertFalse(comparar_senha("x", "pbkdf2_sha256$abc$sal$hash"))
        self.assertFalse(comparar_senha("x", "lixo"))

    def test_hash_com_menos_voltas_pede_atualizacao(self):
        self.assertTrue(precisa_atualizar_hash(gerar_hash_senha("a1b2c3", iteracoes=10)))
        self.assertFalse(precisa_atualizar_hash(gerar_hash_senha("a1b2c3")))


class TestLoginAtualizaHash(ModulosTestCase):
    def test_login_com_hash_antigo_converte_para_o_novo(self):
        import hashlib
        sal = "s4l"
        antigo = f"{sal}${hashlib.pbkdf2_hmac('sha256', b'admin123', sal.encode(), 60_000).hex()}"
        self.banco.executar("UPDATE usuarios SET senha_hash = ? WHERE id = 'admin'", (antigo,))
        self.autenticador.login("admin@sistema.com", "admin123")
        novo = self.banco.consultar_um("SELECT senha_hash FROM usuarios WHERE id = 'admin'")["senha_hash"]
        self.assertTrue(novo.startswith("pbkdf2_sha256$"))
        self.autenticador.login("admin@sistema.com", "admin123")  # continua funcionando


class TestLimitador(unittest.TestCase):
    def setUp(self):
        self.agora = 1000.0
        self.lim = LimitadorLogin(maximo=3, janela=60, relogio=lambda: self.agora)

    def test_bloqueia_apos_o_maximo_de_falhas(self):
        for _ in range(2):
            self.lim.registrar_falha("a")
        self.assertEqual(self.lim.segundos_restantes("a"), 0)
        self.lim.registrar_falha("a")
        self.assertGreater(self.lim.segundos_restantes("a"), 0)

    def test_libera_depois_da_janela(self):
        for _ in range(3):
            self.lim.registrar_falha("a")
        self.agora += 61
        self.assertEqual(self.lim.segundos_restantes("a"), 0)

    def test_chaves_sao_independentes_e_limpar_zera(self):
        for _ in range(3):
            self.lim.registrar_falha("a")
        self.assertEqual(self.lim.segundos_restantes("b"), 0)
        self.lim.limpar("a")
        self.assertEqual(self.lim.segundos_restantes("a"), 0)


class TestTokensExpirados(ModulosTestCase):
    def test_gerar_token_limpa_os_vencidos(self):
        self.banco.executar("INSERT INTO tokens (token, usuario_id, expira_em) VALUES ('velho', 'admin', 1)")
        self.sessao.gerar_token("admin")
        self.assertIsNone(self.banco.consultar_um("SELECT 1 FROM tokens WHERE token = 'velho'"))

    def test_encerrar_todas_derruba_as_sessoes_do_usuario(self):
        t1, t2 = self.sessao.gerar_token("admin"), self.sessao.gerar_token("admin")
        self.sessao.encerrar_todas("admin")
        self.assertIsNone(self.sessao.validar_token(t1))
        self.assertIsNone(self.sessao.validar_token(t2))


class TestAlterarSenha(ModulosTestCase):
    def test_troca_a_senha_e_derruba_sessoes(self):
        token = self.autenticador.login("admin@sistema.com", "admin123")
        self.usuarios.alterar_senha("admin", "admin123", "NovaSenha#1")
        self.assertIsNone(self.sessao.validar_token(token))
        self.autenticador.login("admin@sistema.com", "NovaSenha#1")

    def test_exige_senha_atual_correta(self):
        with self.assertRaisesRegex(Exception, "senha atual"):
            self.usuarios.alterar_senha("admin", "errada", "NovaSenha#1")

    def test_recusa_senha_curta_ou_igual(self):
        with self.assertRaisesRegex(Exception, "pelo menos 8"):
            self.usuarios.alterar_senha("admin", "admin123", "curta")
        with self.assertRaisesRegex(Exception, "diferente"):
            self.usuarios.alterar_senha("admin", "admin123", "admin123")

    def test_troca_desliga_a_obrigatoriedade(self):
        self.banco.executar("UPDATE usuarios SET trocar_senha = 1 WHERE id = 'admin'")
        self.usuarios.alterar_senha("admin", "admin123", "NovaSenha#1")
        self.assertEqual(self.usuarios.buscar_por_id("admin")["trocar_senha"], 0)


if __name__ == "__main__":
    unittest.main()
