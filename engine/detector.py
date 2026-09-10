import re
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from engine.models import Transaction, Subscription, Anomaly


KNOWN_SUBSCRIPTION_PATTERNS = [
    (r"(?i)\bnetflix\b", "Netflix", "Lazer & Entretenimento"),
    (r"(?i)\bspotify\b", "Spotify", "Lazer & Entretenimento"),
    (r"(?i)\bchatgpt|openai\b", "ChatGPT Plus / OpenAI", "Assinaturas & Serviços"),
    (r"(?i)\bclaude|anthropic\b", "Claude Pro / Anthropic", "Assinaturas & Serviços"),
    (r"(?i)\bapple\.com/bill|icloud\b", "Apple iCloud / Services", "Assinaturas & Serviços"),
    (r"(?i)\bgoogle\s*(one|storage|workspace|play)\b", "Google Workspace / One", "Assinaturas & Serviços"),
    (r"(?i)\bamazon\s*(prime|music|video)\b", "Amazon Prime", "Lazer & Entretenimento"),
    (r"(?i)\byoutube\s*(premium|music)\b", "YouTube Premium", "Lazer & Entretenimento"),
    (r"(?i)\bgithub\b", "GitHub Copilot / Sub", "Assinaturas & Serviços"),
    (r"(?i)\bdisney(\+|plus)\b", "Disney+", "Lazer & Entretenimento"),
    (r"(?i)\bhbo\s*max|max\.com\b", "Max / HBO", "Lazer & Entretenimento"),
    (r"(?i)\bsmart\s*fit|gympass|totalpass\b", "Academia / Fitness", "Saúde & Bem-estar"),
    (r"(?i)\bdropbox\b", "Dropbox", "Assinaturas & Serviços"),
    (r"(?i)\bnotion\b", "Notion", "Assinaturas & Serviços"),
    (r"(?i)\bcursor\b", "Cursor AI", "Assinaturas & Serviços"),
    (r"(?i)\bmidjourney\b", "Midjourney", "Assinaturas & Serviços"),
    (r"(?i)\bfigma\b", "Figma", "Assinaturas & Serviços"),
    (r"(?i)\bvercel\b", "Vercel Pro", "Assinaturas & Serviços"),
    (r"(?i)\baws|amazon web services\b", "Amazon Web Services", "Assinaturas & Serviços"),
    (r"(?i)\bhetzner|digitalocean\b", "Cloud Hosting / VPS", "Assinaturas & Serviços"),
]


def normalize_merchant(description: str) -> Tuple[str, Optional[str]]:
    """Identifica padrões conhecidos de serviços recorrentes ou limpa o nome da transação."""
    desc_clean = description.strip()
    for pattern, clean_name, category in KNOWN_SUBSCRIPTION_PATTERNS:
        if re.search(pattern, desc_clean):
            return clean_name, category

    # Limpeza genérica de ruídos de cartão (ex: "PGTO ELETRON", números de série, etc.)
    cleaned = re.sub(r"(?i)\b(pgto|compra|cartao|elo|visa|master|debito|credito|pag\*|picpay\*|mercadopago\*)\b", "", desc_clean)
    cleaned = re.sub(r"\d{3,}", "", cleaned)
    cleaned = re.sub(r"[-_*#]", " ", cleaned).strip()
    return cleaned.title() if len(cleaned) > 2 else desc_clean, None


class SubscriptionDetector:
    def __init__(self, transactions: List[Transaction]):
        self.transactions = transactions

    def detect(self) -> Tuple[List[Subscription], List[Anomaly]]:
        """
        Analisa o histórico de transações e detecta:
        1. Serviços recorrentes com periodicidade mensal, semanal ou anual.
        2. Variações e aumentos de preço em assinaturas.
        """
        # Agrupar transações apenas de despesa por merchant normalizado
        merchant_groups: Dict[str, List[Transaction]] = defaultdict(list)

        for tx in self.transactions:
            if tx.is_expense() or tx.category_type != "INCOME":
                clean_name, default_cat = normalize_merchant(tx.description)
                merchant_groups[clean_name].append(tx)

        detected_subscriptions: List[Subscription] = []
        anomalies: List[Anomaly] = []

        for merchant, txs in merchant_groups.items():
            # Ordenar por data cronológica crescente
            txs_sorted = sorted(txs, key=lambda x: x.date)

            if len(txs_sorted) < 2:
                # Se houver apenas 1 transação, verificar se é um padrão de assinatura conhecido
                is_known = any(merchant == known[1] for known in KNOWN_SUBSCRIPTION_PATTERNS)
                if is_known:
                    tx = txs_sorted[0]
                    detected_subscriptions.append(
                        Subscription(
                            id=None,
                            name=merchant,
                            amount=tx.amount,
                            cadence="MONTHLY",
                            status="ACTIVE",
                            category_name=tx.category_name or "Assinaturas & Serviços",
                            first_seen=tx.date,
                            last_seen=tx.date,
                            charges_count=1,
                            previous_amount=None
                        )
                    )
                continue

            # Calcular intervalos em dias entre cobranças consecutivas
            intervals = []
            for i in range(1, len(txs_sorted)):
                try:
                    d1 = datetime.strptime(txs_sorted[i - 1].date[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(txs_sorted[i].date[:10], "%Y-%m-%d")
                    delta = (d2 - d1).days
                    if delta > 0:
                        intervals.append(delta)
                except ValueError:
                    continue

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)

            # Determinar cadência
            cadence = None
            if 20 <= avg_interval <= 40:
                cadence = "MONTHLY"
            elif 320 <= avg_interval <= 400:
                cadence = "YEARLY"
            elif 5 <= avg_interval <= 9:
                cadence = "WEEKLY"

            if cadence or any(merchant == known[1] for known in KNOWN_SUBSCRIPTION_PATTERNS):
                cadence = cadence or "MONTHLY"
                latest_tx = txs_sorted[-1]
                earliest_tx = txs_sorted[0]

                # Verificar se houve mudança de preço
                amounts = [t.amount for t in txs_sorted]
                latest_amount = latest_tx.amount
                prev_amount = None
                price_change_pct = None

                # Comparar com cobrança anterior de valor diferente
                for amt in reversed(amounts[:-1]):
                    if amt != latest_amount:
                        prev_amount = amt
                        price_change_pct = ((latest_amount - prev_amount) / prev_amount) * 100
                        break

                sub = Subscription(
                    id=None,
                    name=merchant,
                    amount=latest_amount,
                    cadence=cadence,
                    status="ACTIVE",
                    category_name=latest_tx.category_name or "Assinaturas & Serviços",
                    first_seen=earliest_tx.date,
                    last_seen=latest_tx.date,
                    charges_count=len(txs_sorted),
                    previous_amount=prev_amount,
                    price_change_pct=price_change_pct
                )
                detected_subscriptions.append(sub)

                # Se o preço aumentou, gera anomalia de aviso
                if prev_amount and latest_amount > prev_amount:
                    anomalies.append(
                        Anomaly(
                            id=None,
                            type="PRICE_INCREASE",
                            severity="MEDIUM",
                            merchant=merchant,
                            description=(
                                f"Assinatura '{merchant}' aumentou de R$ {prev_amount:.2f} "
                                f"para R$ {latest_amount:.2f} (+{price_change_pct:.1f}%)."
                            ),
                            amount=latest_amount - prev_amount,
                            date=latest_tx.date
                        )
                    )

        return detected_subscriptions, anomalies
