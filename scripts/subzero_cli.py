#!/usr/bin/env python3
import sys
import os
import argparse
import json
from datetime import datetime

# Garantir importação do módulo engine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.database import Database
from engine.repository import FinanceRepository
from engine.detector import SubscriptionDetector
from engine.anomaly import AnomalyDetector
from engine.importer import StatementImporter


def get_repo(db_path: str = None) -> FinanceRepository:
    db = Database(db_path) if db_path else Database()
    return FinanceRepository(db)


def cmd_audit(args):
    repo = get_repo(args.db)
    # Buscar todas as transações para análise histórica de assinaturas
    txs = repo.list_transactions(limit=1000)

    if not txs:
        print("💳 SubZero — Nenhuma transação encontrada no banco de dados local.")
        print("Importe seu extrato bancário usando: subzero import-statement --file extrato.csv")
        return

    # 1. Detectar Assinaturas
    detector = SubscriptionDetector(txs)
    subs, sub_anomalies = detector.detect()

    # Salvar assinaturas detectadas no banco
    for s in subs:
        repo.upsert_subscription(s)

    # 2. Detectar Cobranças Duplicadas
    anomaly_detector = AnomalyDetector(txs)
    dup_anomalies = anomaly_detector.detect_duplicates()

    # Salvar anomalias
    all_anomalies = sub_anomalies + dup_anomalies
    for a in all_anomalies:
        repo.add_anomaly(a)

    if args.json:
        result = {
            "subscriptions": [
                {
                    "name": s.name,
                    "amount": s.amount,
                    "cadence": s.cadence,
                    "annual_impact": s.annual_impact,
                    "price_change_pct": s.price_change_pct,
                    "last_seen": s.last_seen
                }
                for s in subs
            ],
            "anomalies": [
                {
                    "type": a.type,
                    "severity": a.severity,
                    "merchant": a.merchant,
                    "description": a.description,
                    "amount": a.amount,
                    "date": a.date
                }
                for a in all_anomalies
            ],
            "total_monthly": sum(s.amount for s in subs if s.cadence == "MONTHLY"),
            "total_annual": sum(s.annual_impact for s in subs)
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Formatação limpa para iMessage / terminal
    total_monthly = sum(s.amount for s in subs if s.cadence == "MONTHLY")
    total_annual = sum(s.annual_impact for s in subs)

    output = []
    output.append("💳 SubZero — Auditoria de Assinaturas & Recorrências")
    output.append("═" * 50)
    output.append(f"🔎 {len(subs)} serviço(s) recorrente(s) identificado(s):\n")

    for s in subs:
        change_tag = ""
        if s.price_change_pct and s.price_change_pct > 0:
            change_tag = f" ⚠️ (aumentou {s.price_change_pct:.0f}%!)"
        elif s.price_change_pct and s.price_change_pct < 0:
            change_tag = f" 📉 (reduziu {abs(s.price_change_pct):.0f}%)"

        cadence_label = "/mês" if s.cadence == "MONTHLY" else ("/ano" if s.cadence == "YEARLY" else "/sem")
        output.append(f" • {s.name}: R$ {s.amount:.2f}{cadence_label}{change_tag}")

    output.append("\n" + "─" * 50)
    output.append(f"💸 Sangramento Recorrente: R$ {total_monthly:.2f}/mês")
    output.append(f"📈 Impacto Projetado:     R$ {total_annual:.2f}/ano")
    output.append("─" * 50)

    if dup_anomalies:
        output.append("\n🚨 Alertas de Cobrança Duplicada Detectados:")
        for d in dup_anomalies:
            output.append(f" • {d.description}")

    if sub_anomalies:
        output.append("\n📈 Alertas de Aumento de Preço:")
        for a in sub_anomalies:
            output.append(f" • {a.description}")

    print("\n".join(output))


def cmd_summary(args):
    repo = get_repo(args.db)
    target_month = args.month or datetime.now().strftime("%Y-%m")
    income, expense, net, categories = repo.get_monthly_summary(target_month)

    if args.json:
        print(json.dumps({
            "month": target_month,
            "total_income": income,
            "total_expense": expense,
            "net_balance": net,
            "categories": categories
        }, indent=2, ensure_ascii=False))
        return

    output = []
    output.append(f"📊 Resumo Financeiro — Mês {target_month}")
    output.append("═" * 45)
    output.append(f"🟢 Entradas:      R$ {income:.2f}")
    output.append(f"🔴 Saídas:        R$ {expense:.2f}")
    bal_emoji = "🟢" if net >= 0 else "🔴"
    output.append(f"{bal_emoji} Saldo Líquido:  R$ {net:.2f}")
    output.append("─" * 45)
    output.append("Principais Gastos por Categoria:")

    for c in categories:
        if c["type"] == "EXPENSE":
            output.append(f" • {c['icon']} {c['name']}: R$ {c['total']:.2f} ({c['count']} tx)")

    print("\n".join(output))


def cmd_add_tx(args):
    repo = get_repo(args.db)
    cat = repo.get_or_create_category(args.category, cat_type="EXPENSE")
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    tx = repo.add_transaction(
        amount=args.amount,
        category_id=cat.id,
        description=args.description,
        date_str=date_str
    )
    print(f"✅ Transação registrada: R$ {tx.amount:.2f} em '{tx.category_name}' ({tx.description}) na data {tx.date}.")


def cmd_import(args):
    repo = get_repo(args.db)
    importer = StatementImporter(repo)

    if not os.path.exists(args.file):
        print(f"❌ Arquivo não encontrado: {args.file}")
        sys.exit(1)

    ext = os.path.splitext(args.file)[1].lower()
    if ext == ".ofx":
        count = importer.import_ofx(args.file)
    else:
        count = importer.import_csv(args.file)

    print(f"✅ Sucesso: {count} transações importadas com sucesso para o banco SQLite local!")


def cmd_found_money(args):
    advice = AnomalyDetector.get_unclaimed_funds_advice(args.country)
    if args.json:
        print(json.dumps(advice, indent=2, ensure_ascii=False))
        return

    print("💰 SubZero — Guia de Dinheiro Esquecido (Found Money)")
    print("═" * 50)
    print(f"🏛️ Autoridade: {advice['authority']}")
    print(f"🔗 Site Oficial: {advice['official_url']}")
    print("─" * 50)
    print(advice['instructions'])


def main():
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--db", help="Caminho do arquivo SQLite (opcional)")
    common_parser.add_argument("--json", action="store_true", help="Saída formatada em JSON")

    parser = argparse.ArgumentParser(
        description="SubZero — The Privacy-First Subscription & Financial Butler",
        parents=[common_parser]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # audit
    p_audit = subparsers.add_parser("audit", parents=[common_parser], help="Audita assinaturas recorrentes e anomalias")
    p_audit.set_defaults(func=cmd_audit)

    # summary
    p_summary = subparsers.add_parser("summary", parents=[common_parser], help="Exibe o resumo mensal")
    p_summary.add_argument("--month", help="Mês no formato YYYY-MM")
    p_summary.set_defaults(func=cmd_summary)

    # add-tx
    p_add = subparsers.add_parser("add-tx", parents=[common_parser], help="Lança uma nova transação")
    p_add.add_argument("--amount", type=float, required=True, help="Valor da despesa")
    p_add.add_argument("--category", default="Outros", help="Nome da categoria")
    p_add.add_argument("--description", required=True, help="Descrição da transação")
    p_add.add_argument("--date", help="Data da transação (YYYY-MM-DD)")
    p_add.set_defaults(func=cmd_add_tx)

    # import-statement
    p_import = subparsers.add_parser("import-statement", parents=[common_parser], help="Importa extrato CSV ou OFX")
    p_import.add_argument("--file", required=True, help="Caminho do arquivo de extrato")
    p_import.set_defaults(func=cmd_import)

    # found-money
    p_fm = subparsers.add_parser("found-money", parents=[common_parser], help="Instruções para resgate de dinheiro esquecido")
    p_fm.add_argument("--country", default="BR", choices=["BR", "US"], help="País para consulta")
    p_fm.set_defaults(func=cmd_found_money)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
