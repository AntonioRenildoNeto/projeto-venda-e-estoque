"""Testes do Sistema de Vendas e Estoque."""
import os

# O hash de senha de produção é propositalmente lento (600 mil voltas). Nos testes
# usamos poucas voltas para a suíte continuar rápida; tests/unitarios/test_seguranca.py
# confirma que o padrão de produção continua sendo o forte.
os.environ.setdefault("SENHA_ITERACOES", "1000")
