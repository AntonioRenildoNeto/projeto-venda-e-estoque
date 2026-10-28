"""Testes unitários do módulo Usuários (Antonio)."""
import unittest

from sistema.erros import ErroNaoEncontrado, ErroValidacao
from sistema.usuarios.funcoes import validar_email, validar_telefone
from sistema.usuarios.perfil import Perfil
from tests.base import USUARIO_COMUM, ModulosTestCase


class TestFuncoesUsuarios(unittest.TestCase):
    def test_validar_email(self):
        for ok in ["a@b.com", "nome.sobrenome@empresa.com.br", " x@y.co "]:
            self.assertTrue(validar_email(ok), ok)
        for ruim in ["", None, "sem-arroba", "a@b", "a b@c.com", "@b.com", "a@@b.com"]:
            self.assertFalse(validar_email(ruim), ruim)

    def test_validar_telefone(self):
        for ok in ["(11) 91234-5678", "11912345678", "1132345678", "11 3234-5678"]:
            self.assertTrue(validar_telefone(ok), ok)
        for ruim in ["", None, "12345", "abc", "(11) 91234-567a", "119123456789"]:
            self.assertFalse(validar_telefone(ruim), ruim)


class TestPerfil(unittest.TestCase):
    def test_eh_admin(self):
        self.assertTrue(Perfil("admin").eh_admin())
        self.assertFalse(Perfil("comum").eh_admin())

    def test_listar_permissoes(self):
        self.assertIn("cadastrar_usuario", Perfil("admin").listar_permissoes())
        self.assertNotIn("cadastrar_usuario", Perfil("comum").listar_permissoes())
        self.assertIn("vender", Perfil("comum").listar_permissoes())

    def test_tem_permissao(self):
        self.assertTrue(Perfil("admin").tem_permissao("remover_produto"))
        self.assertFalse(Perfil("comum").tem_permissao("remover_produto"))

    def test_perfil_invalido(self):
        with self.assertRaises(ErroValidacao):
            Perfil("gerente")

    def test_listar_permissoes_nao_deixa_alterar_a_lista_original(self):
        Perfil("comum").listar_permissoes().append("remover_usuario")
        self.assertNotIn("remover_usuario", Perfil("comum").listar_permissoes())


class TestUsuario(ModulosTestCase):
    def cadastrar(self, **mudancas):
        return self.usuarios.cadastrar(**{**USUARIO_COMUM, **mudancas})

    def test_cadastrar_salva_todos_os_campos(self):
        u = self.cadastrar()
        self.assertEqual(u["id"], "maria01")
        self.assertEqual(u["nome_completo"], "Maria Souza")
        self.assertEqual(u["email"], "maria@loja.com")
        self.assertEqual(u["telefone"], "(11) 91234-5678")
        self.assertEqual(u["perfil"], "comum")

    def test_cadastrar_normaliza_email_e_nome(self):
        u = self.cadastrar(email="  MARIA@Loja.com ", nome_completo="  Maria   Souza ")
        self.assertEqual(u["email"], "maria@loja.com")
        self.assertEqual(u["nome_completo"], "Maria Souza")

    def test_cadastrar_recusa_dados_invalidos(self):
        casos = {
            "id vazio": {"id": ""},
            "id com caracteres inválidos": {"id": "ma ria!"},
            "id muito longo": {"id": "a" * 21},
            "nome sem sobrenome": {"nome_completo": "Maria"},
            "nome vazio": {"nome_completo": ""},
            "email inválido": {"email": "maria.loja.com"},
            "telefone inválido": {"telefone": "123"},
            "senha curta": {"senha": "123"},
            "senha vazia": {"senha": ""},
            "perfil inválido": {"perfil": "gerente"},
        }
        for descricao, mudanca in casos.items():
            with self.subTest(descricao):
                with self.assertRaises(ErroValidacao):
                    self.cadastrar(**mudanca)
        self.assertEqual(len(self.usuarios.listar()), 1)  # só o Admin

    def test_cadastrar_recusa_id_e_email_repetidos(self):
        self.cadastrar()
        with self.assertRaises(ErroValidacao):
            self.cadastrar(email="outro@loja.com")  # mesmo ID
        with self.assertRaises(ErroValidacao):
            self.cadastrar(id="outro", email="MARIA@loja.com")  # mesmo e-mail

    def test_listar_nao_mostra_senha(self):
        self.cadastrar()
        for u in self.usuarios.listar():
            self.assertNotIn("senha_hash", u)
            self.assertNotIn("senha", u)

    def test_buscar_por_id(self):
        self.cadastrar()
        self.assertEqual(self.usuarios.buscar_por_id("maria01")["email"], "maria@loja.com")
        self.assertIsNone(self.usuarios.buscar_por_id("nao-existe"))

    def test_remover_exclui_o_usuario(self):
        self.cadastrar()
        self.usuarios.remover("maria01")
        self.assertIsNone(self.usuarios.buscar_por_id("maria01"))

    def test_remover_usuario_inexistente(self):
        with self.assertRaises(ErroNaoEncontrado):
            self.usuarios.remover("fantasma")

    def test_remover_apaga_as_sessoes_do_usuario(self):
        self.cadastrar()
        token = self.sessao.gerar_token("maria01")
        self.usuarios.remover("maria01")
        self.assertIsNone(self.sessao.validar_token(token))

    def test_nao_pode_remover_a_si_mesmo(self):
        self.cadastrar(id="admin2", email="admin2@loja.com", perfil="admin")
        with self.assertRaises(ErroValidacao):
            self.usuarios.remover("admin2", executado_por="admin2")

    def test_nao_pode_remover_o_unico_admin(self):
        with self.assertRaises(ErroValidacao):
            self.usuarios.remover("admin", executado_por="outro")
        self.assertIsNotNone(self.usuarios.buscar_por_id("admin"))


if __name__ == "__main__":
    unittest.main()
