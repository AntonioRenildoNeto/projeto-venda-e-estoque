"""Teste de sistema (Laerte): o sistema completo, de ponta a ponta, pela interface web.

Fluxo: login do Admin -> cadastro de usuário -> cadastro de produtos (3 tipos)
-> compra -> venda -> conferência do estoque final -> logout.
"""
from tests.base import USUARIO_COMUM, WebTestCase


class TestFluxoCompleto(WebTestCase):
    def test_fluxo_de_ponta_a_ponta(self):
        # 1. Admin entra no sistema
        r = self.entrar()
        self.assertIn("Olá, Administrador", self.texto(r))

        # 2. Admin cadastra um usuário comum
        r = self.post("/usuarios", {
            "id": USUARIO_COMUM["id"], "nome_completo": USUARIO_COMUM["nome_completo"],
            "email": USUARIO_COMUM["email"], "telefone": USUARIO_COMUM["telefone"],
            "senha": USUARIO_COMUM["senha"], "perfil": "comum",
        })
        self.assertIn("Usuário cadastrado com sucesso", self.texto(r))
        self.assertIn("Maria Souza", self.texto(r))

        # 3. Admin cadastra os três tipos de produto
        for nome, tipo, preco in [("Arroz 5kg", "Alimento", "25,90"),
                                  ("Fone Bluetooth", "Eletrônico", "120,00"),
                                  ("Camiseta", "Vestuário", "39,90")]:
            r = self.post("/produtos", {"nome": nome, "tipo": tipo, "preco": preco})
            self.assertIn("Produto cadastrado com sucesso", self.texto(r))
        produtos = {p["nome"]: p["id"] for p in self.s.produtos.listar()}
        self.assertEqual(len(produtos), 3)
        self.assertEqual({p["tipo"] for p in self.s.produtos.listar()}, {"Alimento", "Eletrônico", "Vestuário"})

        # 4. Produtos novos entram no estoque zerados
        for pid in produtos.values():
            self.assertEqual(self.quantidade_na_tela(pid), 0)

        # 5. Compras repõem o estoque
        arroz, fone, camiseta = produtos["Arroz 5kg"], produtos["Fone Bluetooth"], produtos["Camiseta"]
        for pid, qtd, preco in [(arroz, 50, "20"), (fone, 10, "90"), (camiseta, 30, "25")]:
            r = self.post("/compras", {"produto_id": pid, "quantidade": qtd, "preco_unitario": preco})
            self.assertIn("Compra registrada", self.texto(r))
        self.assertEqual([self.quantidade_na_tela(p) for p in (arroz, fone, camiseta)], [50, 10, 30])

        # 6. Venda diminui o estoque
        r = self.post("/vendas", {"produto_id": arroz, "quantidade": 8})
        self.assertIn("Venda registrada", self.texto(r))
        self.assertIn("R$ 207,20", self.texto(r))  # 8 x 25,90
        self.assertEqual(self.quantidade_na_tela(arroz), 42)

        # 7. Venda maior que o estoque é bloqueada e o estoque não muda
        r = self.post("/vendas", {"produto_id": fone, "quantidade": 11})
        self.assertIn("Estoque insuficiente", self.texto(r))
        self.assertEqual(self.quantidade_na_tela(fone), 10)

        # 8. Cancelar a venda devolve as unidades
        venda = self.s.vendas.listar()[0]
        r = self.post(f"/vendas/{venda['id']}/cancelar")
        self.assertIn("Venda cancelada", self.texto(r))
        self.assertEqual(self.quantidade_na_tela(arroz), 50)

        # 9. Usuário comum (cadastrado no passo 2) consegue vender, mas não administrar
        comum = self.app.test_client()
        r = self.entrar(USUARIO_COMUM["email"], USUARIO_COMUM["senha"], comum)
        self.assertIn("Olá, Maria", self.texto(r))
        r = self.post("/vendas", {"produto_id": camiseta, "quantidade": 5}, comum)
        self.assertIn("Venda registrada", self.texto(r))
        self.assertEqual(self.quantidade_na_tela(camiseta), 25)
        self.assertEqual(comum.get("/usuarios").status_code, 403)

        # 10. Admin remove o usuário e o produto; tudo some do sistema
        self.post(f"/usuarios/{USUARIO_COMUM['id']}/remover")
        self.assertIsNone(self.s.usuarios.buscar_por_id(USUARIO_COMUM["id"]))
        self.assertEqual(comum.get("/estoque").status_code, 302)  # sessão do removido caiu
        self.post(f"/produtos/{fone}/remover")
        self.assertIsNone(self.quantidade_na_tela(fone))

        # 11. Logout
        self.client.post("/logout")
        self.assertEqual(self.client.get("/").status_code, 302)
