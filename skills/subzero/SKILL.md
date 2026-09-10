---
name: subzero
description: Audits recurring subscriptions, flags stealth price increases, detects duplicate charges, summarizes monthly spending, imports bank statements, and guides found money recovery on the user's Mac via Plow Latch.
---

# SubZero — Financial & Subscription Butler Workflow

## When to Trigger This Skill

Trigger this skill whenever the user:
- Asks about their active or recurring subscriptions (*"quais minhas assinaturas?"*, *"quanto gasto com streaming?"*, *"what subscriptions am I paying for?"*)
- Asks to check for price increases, billing errors or duplicate charges (*"tem alguma cobrança duplicada?"*, *"subiu de preço alguma coisa?"*, *"check for anomalies"*)
- Asks for a monthly spending summary or cash flow breakdown (*"como foram os gastos desse mês?"*, *"resumo financeiro"*, *"monthly summary"*)
- Inquires about unclaimed funds or forgotten government balances (*"dinheiro esquecido"*, *"valores a receber"*, *"unclaimed property"*, *"found money"*)
- Requests to import a bank statement (*"importar extrato.csv"*, *"leia o ofx do Itaú"*)
- Requests to manually record a transaction (*"adicionei gasto de R$ 45 no almoço"*)

---

## Tool Execution via Plow Latch MCP

All operations execute strictly on the owner's Mac through the **Plow Latch MCP** using `latch:run_command` (or `plow_run_command`).

The local engine CLI can be executed via:
`subzero <subcommand>` (global command) or `python3 scripts/subzero_cli.py <subcommand>`

### 1. Subscription & Anomaly Audit (`audit`)
Execute:
```bash
subzero audit --json
```
- Inspect the output:
  - `subscriptions`: List of detected subscriptions, intervals, monthly amounts, annual impact, and any price changes (`price_change_pct != null`).
  - `anomalies`: List of duplicate transactions or price hike alerts.
  - `total_monthly` and `total_annual`: Total committed recurring spending.
- Format the response into concise iMessage-ready cards.

### 2. Monthly Cash Flow & Expense Summary (`summary`)
Execute:
```bash
subzero summary --json
# Or for a specific month:
subzero summary --month 2026-03 --json
```
- Report:
  - Total Income & Total Expenses
  - Net Cash Flow (Surplus or Deficit)
  - Top spending categories with percentage breakdown.

### 3. Forgotten / Unclaimed Money Guidance (`found-money`)
Execute:
```bash
subzero found-money --country BR
# Or for US:
subzero found-money --country US
```
- Explain the official, free government portals (Banco Central do Brasil SVR / NAUPA MissingMoney).
- Warn explicitly against scams or third parties charging fees to recover funds.

### 4. Bank Statement Import (`import-statement`)
Execute:
```bash
subzero import-statement --file /path/to/statement.csv
```
- Automatically detects Nubank, Itaú, Inter, generic CSV, or OFX formats.
- Reports imported transactions count and automatically triggers an `audit` if new recurring patterns or duplicates appear.

### 5. Add Manual Transaction (`add-tx`)
Execute:
```bash
subzero add-tx --amount 45.00 --description "Almoço Executivo" --category "Alimentação"
```

---

## Proactive Engagement & Notifications

If a new statement is imported or the user initiates conversation after a billing cycle:
1. Proactively highlight any **price increases** (e.g. Netflix increased by 18%).
2. Alert immediately on **duplicate charges** in the last 48h.
3. Suggest calculated annual savings if unused subscriptions are cancelled.

---

## Output Standards for iMessage & Plow Chat

1. **Keep it Visual and Scannable:**
   - 🔄 **Assinaturas Ativas:** List name, monthly cost, and annual cost.
   - 📈 **Alerta de Aumento:** Highlight any service that increased in price with previous vs current cost.
   - 🚨 **Cobranças Suspeitas / Duplicadas:** Clearly state date, amount, merchant, and reason for alert.
   - 💰 **Potencial de Economia:** Calculate immediate annual savings if non-essential subscriptions are cancelled.
2. **Privacy Boundary:** Never send raw bank account numbers, passwords, or personal tax IDs outside the local machine.
