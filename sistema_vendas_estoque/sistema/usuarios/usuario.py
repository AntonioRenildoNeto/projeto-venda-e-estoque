"""Classe Usuario: cadastro e remoção de usuários."""
import re

from ..autenticacao.funcoes import comparar_senha, gerar_hash_senha
from ..erros import ErroNaoEncontrado, ErroValidacao
from .funcoes import validar_email, validar_telefone
from .perfil import PERFIS

CAMPOS_PUBLICOS = "id, nome_completo, email, telefone, perfil, trocar_senha"
SENHA_MINIMA_NOVA = 8


class Usuario:
    def __init__(self, banco):
        self.banco = banco

    def cadastrar(self, id, nome_completo, email, telefone, senha, perfil="comum", trocar_senha=False):
        """Valida os dados e salva o usuário."""
        id = (id or "").strip()
        nome_completo = " ".join((nome_completo or "").split())
        email = (email or "").strip().lower()
        telefone = (telefone or "").strip()

        if not id:
            raise ErroValidacao("Informe o ID do usuário.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,20}", id):
            raise ErroValidacao("O ID deve ter até 20 letras, números, '.', '_' ou '-'.")
        if len(nome_completo.split()) < 2:
            raise ErroValidacao("Informe o nome completo (nome e sobrenome).")
        if not validar_email(email):
            raise ErroValidacao("E-mail inválido.")
        if not validar_telefone(telefone):
            raise ErroValidacao("Telefone inválido. Informe o DDD e o número.")
        if not senha or len(senha) < 6:
            raise ErroValidacao("A senha deve ter pelo menos 6 caracteres.")
        if perfil not in PERFIS:
            raise ErroValidacao("Perfil inválido.")

        if self.buscar_por_id(id):
            raise ErroValidacao("Já existe um usuário com esse ID.")
        if self.banco.consultar_um("SELECT 1 FROM usuarios WHERE email = ?", (email,)):
            raise ErroValidacao("Já existe um usuário com esse e-mail.")

        self.banco.executar(
            "INSERT INTO usuarios (id, nome_completo, email, telefone, senha_hash, perfil, trocar_senha) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, nome_completo, email, telefone, gerar_hash_senha(senha), perfil, int(bool(trocar_senha))),
        )
        return self.buscar_por_id(id)

    def listar(self):
        """Retorna os usuários cadastrados (sem a senha)."""
        return self.banco.consultar(f"SELECT {CAMPOS_PUBLICOS} FROM usuarios ORDER BY nome_completo")

    def buscar_por_id(self, id):
        """Procura um usuário pelo ID; devolve None se não existir."""
        return self.banco.consultar_um(f"SELECT {CAMPOS_PUBLICOS} FROM usuarios WHERE id = ?", (id,))

    def remover(self, id, executado_por=None):
        """Exclui o usuário do banco (e encerra as sessões dele)."""
        usuario = self.buscar_por_id(id)
        if usuario is None:
            raise ErroNaoEncontrado("Usuário não encontrado.")
        if executado_por is not None and executado_por == id:
            raise ErroValidacao("Você não pode remover o seu próprio usuário.")
        if usuario["perfil"] == "admin":
            admins = self.banco.consultar_um("SELECT COUNT(*) AS n FROM usuarios WHERE perfil = 'admin'")["n"]
            if admins <= 1:
                raise ErroValidacao("Não é possível remover o único administrador.")
        with self.banco.transacao():
            self.banco.executar("DELETE FROM tokens WHERE usuario_id = ?", (id,))
            self.banco.executar("DELETE FROM usuarios WHERE id = ?", (id,))

    def alterar_senha(self, id, senha_atual, senha_nova):
        """Troca a senha (exige a senha atual) e derruba as outras sessões do usuário."""
        registro = self.banco.consultar_um("SELECT senha_hash FROM usuarios WHERE id = ?", (id,))
        if registro is None:
            raise ErroNaoEncontrado("Usuário não encontrado.")
        if not comparar_senha(senha_atual, registro["senha_hash"]):
            raise ErroValidacao("A senha atual está incorreta.")
        if not senha_nova or len(senha_nova) < SENHA_MINIMA_NOVA:
            raise ErroValidacao(f"A nova senha deve ter pelo menos {SENHA_MINIMA_NOVA} caracteres.")
        if senha_nova == senha_atual:
            raise ErroValidacao("A nova senha deve ser diferente da atual.")
        with self.banco.transacao():
            self.banco.executar(
                "UPDATE usuarios SET senha_hash = ?, trocar_senha = 0 WHERE id = ?",
                (gerar_hash_senha(senha_nova), id),
            )
            self.banco.executar("DELETE FROM tokens WHERE usuario_id = ?", (id,))

    def contar(self):
        return self.banco.consultar_um("SELECT COUNT(*) AS n FROM usuarios")["n"]
