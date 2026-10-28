"""Acesso ao banco de dados SQLite."""
import sqlite3
import threading
from contextlib import contextmanager

from .erros import ErroValidacao

MENSAGEM_NUMERO_GRANDE = "Valor numérico grande demais."

VERSAO_ESQUEMA = 2

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            TEXT PRIMARY KEY,
    nome_completo TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    telefone      TEXT NOT NULL,
    senha_hash    TEXT NOT NULL,
    perfil        TEXT NOT NULL CHECK (perfil IN ('admin', 'comum')),
    trocar_senha  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tokens (
    token      TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    expira_em  REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS produtos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL,
    tipo           TEXT NOT NULL,
    preco          REAL NOT NULL,
    estoque_minimo INTEGER NOT NULL DEFAULT 0,
    ativo          INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS estoque (
    produto_id INTEGER PRIMARY KEY REFERENCES produtos(id),
    quantidade INTEGER NOT NULL CHECK (quantidade >= 0)
);
CREATE TABLE IF NOT EXISTS movimentos_estoque (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade INTEGER NOT NULL,
    tipo       TEXT NOT NULL,
    motivo     TEXT,
    data       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compras (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    total      REAL NOT NULL,
    data       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS itens_compra (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    compra_id      INTEGER NOT NULL REFERENCES compras(id),
    produto_id     INTEGER NOT NULL REFERENCES produtos(id),
    produto_nome   TEXT NOT NULL,
    quantidade     INTEGER NOT NULL,
    preco_unitario REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS vendas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    total      REAL NOT NULL,
    status     TEXT NOT NULL DEFAULT 'concluida',
    data       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS itens_venda (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id       INTEGER NOT NULL REFERENCES vendas(id),
    produto_id     INTEGER NOT NULL REFERENCES produtos(id),
    produto_nome   TEXT NOT NULL,
    quantidade     INTEGER NOT NULL,
    preco_unitario REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS auditoria (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    data       TEXT NOT NULL,
    usuario_id TEXT,
    acao       TEXT NOT NULL,
    detalhe    TEXT
);
"""

# Colunas acrescentadas depois da primeira versão: bancos antigos recebem
# essas colunas automaticamente na abertura (migração simples e repetível).
COLUNAS_NOVAS = [
    ("usuarios", "trocar_senha", "INTEGER NOT NULL DEFAULT 0"),
    ("produtos", "estoque_minimo", "INTEGER NOT NULL DEFAULT 0"),
    ("produtos", "ativo", "INTEGER NOT NULL DEFAULT 1"),
]

INDICES = """
CREATE INDEX IF NOT EXISTS idx_itens_compra_compra ON itens_compra(compra_id);
CREATE INDEX IF NOT EXISTS idx_itens_venda_venda   ON itens_venda(venda_id);
CREATE INDEX IF NOT EXISTS idx_itens_venda_produto ON itens_venda(produto_id);
CREATE INDEX IF NOT EXISTS idx_movimentos_produto  ON movimentos_estoque(produto_id);
CREATE INDEX IF NOT EXISTS idx_vendas_data         ON vendas(data);
CREATE INDEX IF NOT EXISTS idx_tokens_expira       ON tokens(expira_em);
CREATE INDEX IF NOT EXISTS idx_auditoria_data      ON auditoria(data);
"""


class Banco:
    """Pequena camada sobre o sqlite3.

    Dentro de ``with banco.transacao():`` as alterações só são gravadas se
    nada der errado; se acontecer um erro, tudo é desfeito. A transação mais
    externa usa ``BEGIN IMMEDIATE``: ela reserva o banco para escrita logo no
    início, então "conferir o estoque" e "baixar o estoque" não podem ser
    interrompidos por outra venda ao mesmo tempo.
    """

    def __init__(self, caminho=":memory:"):
        self.caminho = caminho
        self.conn = sqlite3.connect(caminho, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if caminho != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self._trava = threading.RLock()
        self._nivel = 0
        self._migrar()

    # ---- preparação do banco --------------------------------------------------
    def _migrar(self):
        self.conn.executescript(ESQUEMA)
        for tabela, coluna, definicao in COLUNAS_NOVAS:
            colunas = [c["name"] for c in self.conn.execute(f"PRAGMA table_info({tabela})")]
            if coluna not in colunas:
                self.conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
        self.conn.executescript(INDICES)
        self.conn.execute(f"PRAGMA user_version = {VERSAO_ESQUEMA}")

    # ---- consultas e alterações -----------------------------------------------
    def executar(self, sql, parametros=()):
        with self._trava:
            try:
                return self.conn.execute(sql, parametros)
            except OverflowError:
                raise ErroValidacao(MENSAGEM_NUMERO_GRANDE) from None

    def consultar(self, sql, parametros=()):
        with self._trava:
            try:
                return [dict(linha) for linha in self.conn.execute(sql, parametros).fetchall()]
            except OverflowError:
                raise ErroValidacao(MENSAGEM_NUMERO_GRANDE) from None

    def consultar_um(self, sql, parametros=()):
        with self._trava:
            try:
                linha = self.conn.execute(sql, parametros).fetchone()
            except OverflowError:
                raise ErroValidacao(MENSAGEM_NUMERO_GRANDE) from None
            return dict(linha) if linha else None

    @contextmanager
    def transacao(self):
        with self._trava:
            if self._nivel == 0:
                self.conn.execute("BEGIN IMMEDIATE")
            self._nivel += 1
            try:
                yield
            except BaseException:
                self._nivel -= 1
                if self._nivel == 0:
                    self.conn.execute("ROLLBACK")
                raise
            else:
                self._nivel -= 1
                if self._nivel == 0:
                    self.conn.execute("COMMIT")

    def copiar_para(self, destino):
        """Faz uma cópia consistente do banco (backup) para o arquivo ``destino``."""
        with self._trava:
            copia = sqlite3.connect(destino)
            try:
                self.conn.backup(copia)
            finally:
                copia.close()

    def fechar(self):
        self.conn.close()
