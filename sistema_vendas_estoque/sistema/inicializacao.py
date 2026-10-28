"""Preparação inicial do sistema."""
import os

from .usuarios.usuario import Usuario

ADMIN_PADRAO = {
    "id": "admin",
    "nome_completo": "Administrador do Sistema",
    "email": "admin@sistema.com",
    "telefone": "(11) 99999-0000",
    "senha": "admin123",
    "perfil": "admin",
}


def criar_admin_padrao(banco, exigir_troca_senha=False):
    """Cria o usuário Admin na primeira vez que o sistema roda.

    A senha inicial pode vir da variável de ambiente ADMIN_SENHA. Com
    ``exigir_troca_senha=True`` o Admin é obrigado a trocá-la no primeiro login.
    """
    existe = banco.consultar_um("SELECT 1 AS x FROM usuarios WHERE perfil = 'admin'")
    if not existe:
        dados = dict(ADMIN_PADRAO)
        dados["senha"] = os.environ.get("ADMIN_SENHA") or dados["senha"]
        Usuario(banco).cadastrar(**dados, trocar_senha=exigir_troca_senha)
