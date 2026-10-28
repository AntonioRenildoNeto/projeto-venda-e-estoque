"""Números do painel, relatórios por período e exportação em CSV."""
import csv
import io
from datetime import date, datetime

from .erros import ErroValidacao


def _texto_seguro(valor):
    """Evita 'injeção de fórmula' ao abrir o CSV no Excel: texto que começa com = + - @ vira texto puro."""
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return valor


def gerar_csv(cabecalho, linhas):
    """Gera o CSV (separador ';' e BOM UTF-8, que o Excel em português abre sem estragar acentos)."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(cabecalho)
    for linha in linhas:
        escritor.writerow([_texto_seguro(c) for c in linha])
    return "﻿" + saida.getvalue()


def numero_br(valor):
    """1234.5 -> '1234,50' (decimal com vírgula, como o Excel brasileiro espera)."""
    return f"{valor:.2f}".replace(".", ",")


def converter_data(texto, padrao=None):
    """Converte 'AAAA-MM-DD' em date; texto vazio devolve o padrão."""
    if not texto:
        return padrao
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ErroValidacao("Data inválida. Use o formato AAAA-MM-DD.") from None


class Relatorios:
    def __init__(self, banco, estoque):
        self.banco = banco
        self.estoque = estoque

    # ---- painel inicial -------------------------------------------------------
    def painel(self, hoje=None):
        hoje = hoje or date.today()
        dia = hoje.isoformat()
        mes = hoje.strftime("%Y-%m")
        um = self.banco.consultar_um
        concluida = "status = 'concluida'"

        def vendas_em(prefixo):
            r = um(
                f"SELECT COUNT(*) AS n, COALESCE(SUM(total), 0) AS total FROM vendas "
                f"WHERE {concluida} AND substr(data, 1, {len(prefixo)}) = ?", (prefixo,)
            )
            return {"quantidade": r["n"], "total": round(r["total"], 2)}

        return {
            "usuarios": um("SELECT COUNT(*) AS n FROM usuarios")["n"],
            "produtos": um("SELECT COUNT(*) AS n FROM produtos WHERE ativo = 1")["n"],
            "compras": um("SELECT COUNT(*) AS n FROM compras")["n"],
            "vendas": um(f"SELECT COUNT(*) AS n FROM vendas WHERE {concluida}")["n"],
            "vendas_hoje": vendas_em(dia),
            "vendas_mes": vendas_em(mes),
            "valor_estoque": self.estoque.valor_total(),
            "abaixo_do_minimo": self.estoque.listar_abaixo_do_minimo(),
            "mais_vendidos": self.mais_vendidos(limite=5),
        }

    def mais_vendidos(self, limite=5, inicio=None, fim=None):
        """Produtos que mais saíram em vendas concluídas (por unidades), opcionalmente num período."""
        filtro, parametros = "", []
        if inicio:
            filtro += " AND substr(v.data, 1, 10) >= ?"
            parametros.append(inicio.isoformat())
        if fim:
            filtro += " AND substr(v.data, 1, 10) <= ?"
            parametros.append(fim.isoformat())
        return self.banco.consultar(
            "SELECT i.produto_nome AS nome, SUM(i.quantidade) AS unidades, "
            "ROUND(SUM(i.quantidade * i.preco_unitario), 2) AS receita "
            "FROM itens_venda i JOIN vendas v ON v.id = i.venda_id "
            f"WHERE v.status = 'concluida'{filtro} "
            "GROUP BY i.produto_id, i.produto_nome ORDER BY unidades DESC, nome LIMIT ?",
            (*parametros, limite),
        )

    # ---- relatório de vendas por período -------------------------------------
    def vendas_do_periodo(self, inicio, fim):
        if inicio > fim:
            raise ErroValidacao("A data inicial não pode ser depois da data final.")
        vendas = self.banco.consultar(
            "SELECT * FROM vendas WHERE substr(data, 1, 10) BETWEEN ? AND ? ORDER BY id",
            (inicio.isoformat(), fim.isoformat()),
        )
        concluidas = [v for v in vendas if v["status"] == "concluida"]
        return {
            "vendas": vendas,
            "quantidade": len(concluidas),
            "canceladas": len(vendas) - len(concluidas),
            "total": round(sum(v["total"] for v in concluidas), 2),
            "mais_vendidos": self.mais_vendidos(limite=10, inicio=inicio, fim=fim),
        }

    # ---- CSV -------------------------------------------------------------------
    def csv_vendas(self, inicio, fim):
        linhas = self.banco.consultar(
            "SELECT v.id, v.data, v.status, v.usuario_id, i.produto_nome, i.quantidade, i.preco_unitario "
            "FROM vendas v JOIN itens_venda i ON i.venda_id = v.id "
            "WHERE substr(v.data, 1, 10) BETWEEN ? AND ? ORDER BY v.id, i.id",
            (inicio.isoformat(), fim.isoformat()),
        )
        return gerar_csv(
            ["Venda", "Data", "Status", "Usuario", "Produto", "Quantidade", "Preco unitario", "Subtotal"],
            [[r["id"], r["data"].replace("T", " "), r["status"], r["usuario_id"], r["produto_nome"],
              r["quantidade"], numero_br(r["preco_unitario"]), numero_br(r["quantidade"] * r["preco_unitario"])]
             for r in linhas],
        )

    def csv_estoque(self):
        return gerar_csv(
            ["ID", "Produto", "Tipo", "Preco", "Quantidade", "Estoque minimo", "Valor em estoque"],
            [[e["produto_id"], e["nome"], e["tipo"], numero_br(e["preco"]), e["quantidade"],
              e["estoque_minimo"], numero_br(e["preco"] * e["quantidade"])]
             for e in self.estoque.listar()],
        )
