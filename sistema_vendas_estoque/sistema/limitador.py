"""Limite de tentativas de login (proteção contra adivinhação de senha)."""
import threading
import time


class LimitadorLogin:
    """Bloqueia uma chave (ex.: e-mail + IP) depois de muitas falhas seguidas."""

    def __init__(self, maximo=5, janela=300, relogio=time.time):
        self.maximo = maximo
        self.janela = janela  # segundos
        self.relogio = relogio
        self._falhas = {}
        self._trava = threading.Lock()

    def _recentes(self, chave):
        agora = self.relogio()
        recentes = [t for t in self._falhas.get(chave, []) if agora - t < self.janela]
        if recentes:
            self._falhas[chave] = recentes
        else:
            self._falhas.pop(chave, None)
        return recentes

    def segundos_restantes(self, chave):
        """0 se pode tentar; senão, quantos segundos faltam para liberar."""
        with self._trava:
            recentes = self._recentes(chave)
            if len(recentes) < self.maximo:
                return 0
            return max(1, int(self.janela - (self.relogio() - recentes[0])) + 1)

    def registrar_falha(self, chave):
        with self._trava:
            self._recentes(chave)
            self._falhas.setdefault(chave, []).append(self.relogio())

    def limpar(self, chave):
        with self._trava:
            self._falhas.pop(chave, None)
