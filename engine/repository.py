import sqlite3
from typing import List, Optional, Tuple, Dict, Any
from engine.database import Database
from engine.models import Category, Transaction, Subscription, Anomaly


class FinanceRepository:
    def __init__(self, db: Database):
        self.db = db

    # -------------------------------------------------------------------------
    # Categorias
    # -------------------------------------------------------------------------
    def get_categories(self, cat_type: Optional[str] = None) -> List[Category]:
        """Retorna todas as categorias cadastradas."""
        query = "SELECT id, name, type, icon FROM categories"
        params = []
        if cat_type:
            query += " WHERE type = ?"
            params.append(cat_type)
        query += " ORDER BY type DESC, name ASC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Category(id=r["id"], name=r["name"], type=r["type"], icon=r["icon"]) for r in rows]

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type, icon FROM categories WHERE id = ?", (category_id,))
            r = cursor.fetchone()
            if r:
                return Category(id=r["id"], name=r["name"], type=r["type"], icon=r["icon"])
            return None

    def get_or_create_category(self, name: str, cat_type: str = "EXPENSE", icon: str = "📦") -> Category:
        """Busca ou cria uma categoria pelo nome."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type, icon FROM categories WHERE LOWER(name) = LOWER(?)", (name,))
            r = cursor.fetchone()
            if r:
                return Category(id=r["id"], name=r["name"], type=r["type"], icon=r["icon"])

            cursor.execute("INSERT INTO categories (name, type, icon) VALUES (?, ?, ?)", (name, cat_type, icon))
            conn.commit()
            return Category(id=cursor.lastrowid, name=name, type=cat_type, icon=icon)

    # -------------------------------------------------------------------------
    # Transações
    # -------------------------------------------------------------------------
    def add_transaction(self, amount: float, category_id: int, description: str, date_str: str) -> Transaction:
        cat = self.get_category_by_id(category_id)
        if not cat:
            raise ValueError(f"Categoria com ID {category_id} não existe.")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transactions (amount, category_id, description, date) VALUES (?, ?, ?, ?)",
                (amount, category_id, description, date_str)
            )
            transaction_id = cursor.lastrowid
            conn.commit()

        return Transaction(
            id=transaction_id,
            amount=amount,
            category_id=category_id,
            description=description,
            date=date_str,
            category_name=cat.name,
            category_type=cat.type,
            category_icon=cat.icon
        )

    def list_transactions(
        self,
        month_year: Optional[str] = None,
        category_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Transaction]:
        query = """
            SELECT t.id, t.amount, t.category_id, t.description, t.date, t.created_at,
                   c.name as category_name, c.type as category_type, c.icon as category_icon
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []
        if month_year:
            query += " AND t.date LIKE ?"
            params.append(f"{month_year}%")
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)

        query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                Transaction(
                    id=r["id"],
                    amount=r["amount"],
                    category_id=r["category_id"],
                    description=r["description"],
                    date=r["date"],
                    category_name=r["category_name"],
                    category_type=r["category_type"],
                    category_icon=r["category_icon"],
                    created_at=r["created_at"]
                )
                for r in cursor.fetchall()
            ]

    def get_monthly_summary(self, month_year: str) -> Tuple[float, float, float, List[Dict[str, Any]]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN c.type = 'INCOME' THEN t.amount ELSE 0 END), 0) as total_income,
                    COALESCE(SUM(CASE WHEN c.type = 'EXPENSE' THEN t.amount ELSE 0 END), 0) as total_expense
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.date LIKE ?;
            """, (f"{month_year}%",))
            res = cursor.fetchone()
            total_income = res["total_income"]
            total_expense = res["total_expense"]
            net_balance = total_income - total_expense

            cursor.execute("""
                SELECT c.name, c.type, c.icon, SUM(t.amount) as total, COUNT(t.id) as count
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.date LIKE ?
                GROUP BY c.id
                ORDER BY total DESC;
            """, (f"{month_year}%",))
            categories_summary = [
                {"name": r["name"], "type": r["type"], "icon": r["icon"], "total": r["total"], "count": r["count"]}
                for r in cursor.fetchall()
            ]

            return total_income, total_expense, net_balance, categories_summary

    # -------------------------------------------------------------------------
    # Assinaturas
    # -------------------------------------------------------------------------
    def upsert_subscription(self, sub: Subscription) -> int:
        """Salva ou atualiza uma assinatura identificada."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, amount FROM subscriptions WHERE name = ?", (sub.name,))
            existing = cursor.fetchone()

            if existing:
                prev_amount = existing["amount"] if existing["amount"] != sub.amount else sub.previous_amount
                cursor.execute("""
                    UPDATE subscriptions
                    SET amount = ?, cadence = ?, status = ?, category_name = ?,
                        last_seen = ?, charges_count = ?, previous_amount = ?
                    WHERE id = ?
                """, (sub.amount, sub.cadence, sub.status, sub.category_name, sub.last_seen,
                      sub.charges_count, prev_amount, existing["id"]))
                conn.commit()
                return existing["id"]
            else:
                cursor.execute("""
                    INSERT INTO subscriptions (name, amount, cadence, status, category_name, first_seen, last_seen, charges_count, previous_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sub.name, sub.amount, sub.cadence, sub.status, sub.category_name,
                      sub.first_seen, sub.last_seen, sub.charges_count, sub.previous_amount))
                conn.commit()
                return cursor.lastrowid

    def list_subscriptions(self, status: Optional[str] = "ACTIVE") -> List[Subscription]:
        query = "SELECT * FROM subscriptions"
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY amount DESC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = []
            for r in cursor.fetchall():
                sub = Subscription(
                    id=r["id"],
                    name=r["name"],
                    amount=r["amount"],
                    cadence=r["cadence"],
                    status=r["status"],
                    category_name=r["category_name"],
                    first_seen=r["first_seen"],
                    last_seen=r["last_seen"],
                    charges_count=r["charges_count"],
                    previous_amount=r["previous_amount"]
                )
                if sub.previous_amount and sub.previous_amount > 0:
                    sub.price_change_pct = ((sub.amount - sub.previous_amount) / sub.previous_amount) * 100
                results.append(sub)
            return results

    # -------------------------------------------------------------------------
    # Anomalias
    # -------------------------------------------------------------------------
    def add_anomaly(self, anomaly: Anomaly) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO anomalies (type, severity, merchant, description, amount, date, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (anomaly.type, anomaly.severity, anomaly.merchant, anomaly.description,
                  anomaly.amount, anomaly.date, 1 if anomaly.resolved else 0))
            conn.commit()
            return cursor.lastrowid

    def list_anomalies(self, only_unresolved: bool = True) -> List[Anomaly]:
        query = "SELECT * FROM anomalies"
        params = []
        if only_unresolved:
            query += " WHERE resolved = 0"
        query += " ORDER BY date DESC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [
                Anomaly(
                    id=r["id"],
                    type=r["type"],
                    severity=r["severity"],
                    merchant=r["merchant"],
                    description=r["description"],
                    amount=r["amount"],
                    date=r["date"],
                    resolved=bool(r["resolved"])
                )
                for r in cursor.fetchall()
            ]
