from datetime import datetime
from typing import List, Dict
from collections import defaultdict
from engine.models import Transaction, Anomaly


class AnomalyDetector:
    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions

    def detect_duplicates(self, max_hours_delta: int = 48) -> List[Anomaly]:
        """
        Detecta compras com o mesmo valor e mesmo estabelecimento realizadas
        em um intervalo inferior a max_hours_delta (potenciais cobranças duplicadas).
        """
        duplicates: List[Anomaly] = []
        # Agrupar por (descrição simplificada, valor exato)
        groups: Dict[tuple, List[Transaction]] = defaultdict(list)

        for tx in self.transactions:
            if tx.is_expense() or tx.category_type != "INCOME":
                desc_key = tx.description.strip().lower()
                groups[(desc_key, tx.amount)].append(tx)

        for (desc, amt), txs in groups.items():
            if len(txs) > 1:
                txs_sorted = sorted(txs, key=lambda x: x.date)
                for i in range(1, len(txs_sorted)):
                    try:
                        d1 = datetime.strptime(txs_sorted[i - 1].date[:10], "%Y-%m-%d")
                        d2 = datetime.strptime(txs_sorted[i].date[:10], "%Y-%m-%d")
                        delta_days = (d2 - d1).days
                        if 0 <= delta_days <= (max_hours_delta // 24):
                            duplicates.append(
                                Anomaly(
                                    id=None,
                                    type="DUPLICATE_CHARGE",
                                    severity="HIGH",
                                    merchant=txs_sorted[i].description,
                                    description=(
                                        f"Cobrança potencialmente duplicada: 2x R$ {amt:.2f} "
                                        f"em '{txs_sorted[i].description}' entre {txs_sorted[i-1].date} e {txs_sorted[i].date}."
                                    ),
                                    amount=amt,
                                    date=txs_sorted[i].date
                                )
                            )
                    except ValueError:
                        continue

        return duplicates

    @staticmethod
    def get_unclaimed_funds_advice(country: str = "BR") -> Dict[str, str]:
        """Retorna orientações oficiais para resgate de 'Dinheiro Esquecido' (Found Money)."""
        if country.upper() == "BR":
            return {
                "title": "Sistema de Valores a Receber (SVR) — Banco Central do Brasil",
                "authority": "Banco Central do Brasil (BCB)",
                "official_url": "https://valoresareceber.bcb.gov.br",
                "instructions": (
                    "O Banco Central possui o sistema oficial 'Valores a Receber (SVR)' onde cidadãos "
                    "e empresas podem consultar se esqueceram dinheiro em contas bancárias encerradas, "
                    "consórcios, tarifas cobradas indevidamente ou cooperativas de crédito.\n"
                    "Passo a passo:\n"
                    "1. Acesse o site oficial: valoresareceber.bcb.gov.br (cuidado com golpes! O BCB nunca manda links por WhatsApp ou SMS);\n"
                    "2. Faça login com sua conta gov.br (nível prata ou ouro);\n"
                    "3. Consulte valores e solicite a devolução via chave Pix direto para sua conta."
                )
            }
        else:
            return {
                "title": "State Unclaimed Property Registry (NAUPA)",
                "authority": "National Association of Unclaimed Property Administrators",
                "official_url": "https://www.unclaimed.org",
                "instructions": (
                    "US states hold billions of dollars in unclaimed funds from forgotten bank accounts, "
                    "uncashed payroll checks, utility deposits, and stock dividends.\n"
                    "Steps:\n"
                    "1. Visit MissingMoney.com or unclaimed.org;\n"
                    "2. Search by your full name and state of residence;\n"
                    "3. Submit a claim online with proof of identity to receive a check/direct deposit."
                )
            }
