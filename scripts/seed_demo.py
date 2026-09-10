#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.database import Database
from engine.repository import FinanceRepository


def seed(db_path: str = None):
    db = Database(db_path) if db_path else Database()
    repo = FinanceRepository(db)

    # Buscar ou criar categorias
    cat_salario = repo.get_or_create_category("Salário", "INCOME", "💼")
    cat_alimentacao = repo.get_or_create_category("Alimentação & Mercado", "EXPENSE", "🍔")
    cat_transporte = repo.get_or_create_category("Transporte", "EXPENSE", "🚗")
    cat_assinaturas = repo.get_or_create_category("Assinaturas & Serviços", "EXPENSE", "💳")
    cat_lazer = repo.get_or_create_category("Lazer & Entretenimento", "EXPENSE", "🍿")
    cat_saude = repo.get_or_create_category("Saúde & Bem-estar", "EXPENSE", "💊")

    demo_txs = [
        # Salário
        (8500.00, cat_salario.id, "Salário Mensal Tech Corp", "2026-07-05"),
        (8500.00, cat_salario.id, "Salário Mensal Tech Corp", "2026-08-05"),
        (8500.00, cat_salario.id, "Salário Mensal Tech Corp", "2026-09-05"),

        # Assinatura Netflix (com aumento em Agosto!)
        (55.90, cat_assinaturas.id, "NETFLIX.COM MENSALIDADE", "2026-06-12"),
        (55.90, cat_assinaturas.id, "NETFLIX.COM MENSALIDADE", "2026-07-12"),
        (65.90, cat_assinaturas.id, "NETFLIX.COM MENSALIDADE", "2026-08-12"),

        # Spotify Family
        (34.90, cat_assinaturas.id, "SPOTIFY AB PREMIUM", "2026-06-18"),
        (34.90, cat_assinaturas.id, "SPOTIFY AB PREMIUM", "2026-07-18"),
        (34.90, cat_assinaturas.id, "SPOTIFY AB PREMIUM", "2026-08-18"),

        # Claude Pro
        (115.00, cat_assinaturas.id, "ANTHROPIC CLAUDE PRO", "2026-07-02"),
        (115.00, cat_assinaturas.id, "ANTHROPIC CLAUDE PRO", "2026-08-02"),
        (115.00, cat_assinaturas.id, "ANTHROPIC CLAUDE PRO", "2026-09-02"),

        # ChatGPT Plus
        (115.00, cat_assinaturas.id, "OPENAI CHATGPT SUBSCRIPTION", "2026-07-10"),
        (115.00, cat_assinaturas.id, "OPENAI CHATGPT SUBSCRIPTION", "2026-08-10"),
        (115.00, cat_assinaturas.id, "OPENAI CHATGPT SUBSCRIPTION", "2026-09-10"),

        # SmartFit Academia
        (129.90, cat_saude.id, "SMART FIT MENSALIDADE", "2026-06-25"),
        (129.90, cat_saude.id, "SMART FIT MENSALIDADE", "2026-07-25"),
        (129.90, cat_saude.id, "SMART FIT MENSALIDADE", "2026-08-25"),

        # Apple iCloud
        (14.90, cat_assinaturas.id, "APPLE.COM/BILL ICLOUD 200GB", "2026-06-28"),
        (14.90, cat_assinaturas.id, "APPLE.COM/BILL ICLOUD 200GB", "2026-07-28"),
        (14.90, cat_assinaturas.id, "APPLE.COM/BILL ICLOUD 200GB", "2026-08-28"),

        # Amazon Prime
        (19.90, cat_lazer.id, "AMAZON PRIME BRASIL", "2026-06-03"),
        (19.90, cat_lazer.id, "AMAZON PRIME BRASIL", "2026-07-03"),
        (19.90, cat_lazer.id, "AMAZON PRIME BRASIL", "2026-08-03"),

        # GitHub Copilot
        (55.00, cat_assinaturas.id, "GITHUB COPILOT MONTHLY", "2026-07-15"),
        (55.00, cat_assinaturas.id, "GITHUB COPILOT MONTHLY", "2026-08-15"),

        # Despesas diárias (Uber, Mercado, Restaurantes)
        (38.50, cat_transporte.id, "Uber Viagem Aeroporto", "2026-08-04"),
        (42.00, cat_alimentacao.id, "Almoço Restaurante Central", "2026-08-06"),
        (25.00, cat_transporte.id, "Uber Corrida Trabalho", "2026-08-09"),
        (85.00, cat_alimentacao.id, "Jantar Pizzaria do Bairro", "2026-08-11"),

        # COBRANÇA DUPLICADA! (Mesmo dia, mesmo valor de mercado)
        (142.50, cat_alimentacao.id, "PÃO DE AÇÚCAR LOJA 14", "2026-08-14"),
        (142.50, cat_alimentacao.id, "PÃO DE AÇÚCAR LOJA 14", "2026-08-14"),

        (32.00, cat_alimentacao.id, "Padaria Café da Manhã", "2026-08-20"),
        (65.00, cat_alimentacao.id, "Almoço Executivo", "2026-08-22"),
        (45.00, cat_transporte.id, "Uber Ida Evento", "2026-08-26"),
        (195.00, cat_alimentacao.id, "Compras Mercado da Semana", "2026-08-29"),
    ]

    for amount, cat_id, desc, date_str in demo_txs:
        repo.add_transaction(amount=amount, category_id=cat_id, description=desc, date_str=date_str)

    print(f"✨ Banco populado com sucesso! {len(demo_txs)} transações realistas inseridas.")


if __name__ == "__main__":
    seed()
