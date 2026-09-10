import re
import csv
from datetime import datetime
from typing import List, Dict, Any
from engine.repository import FinanceRepository
from engine.detector import normalize_merchant


class StatementImporter:
    def __init__(self, repo: FinanceRepository):
        self.repo = repo

    def import_csv(self, file_path: str) -> int:
        """
        Importa extratos em formato CSV detectando automaticamente colunas
        de bancos populares (Nubank, Itaú, Inter, C6, Chase, formato genérico).
        """
        imported_count = 0

        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            # Tentar detectar o delimitador (vírgula, ponto e vírgula, tabulação)
            sample = f.read(2048)
            f.seek(0)
            delimiter = ";" if sample.count(";") > sample.count(",") else ","
            reader = csv.DictReader(f, delimiter=delimiter)

            # Normalizar nomes de colunas para minúsculas
            fieldnames = [c.strip().lower() for c in (reader.fieldnames or [])]

            date_col = next((c for c in fieldnames if c in ("data", "date", "dt", "data_lancamento")), None)
            desc_col = next((c for c in fieldnames if c in ("descricao", "description", "title", "historico", "estabelecimento", "memo")), None)
            amount_col = next((c for c in fieldnames if c in ("valor", "amount", "value")), None)

            if not (date_col and desc_col and amount_col):
                raise ValueError(
                    f"Colunas não reconhecidas no CSV. Esperado: data, descrição e valor. "
                    f"Encontrado: {fieldnames}"
                )

            for row in reader:
                # Mapear chaves normalizadas
                row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                date_val = row_clean.get(date_col, "")
                desc_val = row_clean.get(desc_col, "")
                amount_str = row_clean.get(amount_col, "")

                if not (date_val and desc_val and amount_str):
                    continue

                # Normalizar data para YYYY-MM-DD
                parsed_date = self._parse_date(date_val)
                if not parsed_date:
                    continue

                # Normalizar valor
                parsed_amount = self._parse_amount(amount_str)
                if parsed_amount <= 0:
                    continue

                # Auto-categorizar com base em padrões conhecidos
                clean_name, suggested_cat = normalize_merchant(desc_val)
                cat_name = suggested_cat or "Outros"
                cat = self.repo.get_or_create_category(cat_name, cat_type="EXPENSE")

                self.repo.add_transaction(
                    amount=parsed_amount,
                    category_id=cat.id,
                    description=desc_val,
                    date_str=parsed_date
                )
                imported_count += 1

        return imported_count

    def import_ofx(self, file_path: str) -> int:
        """
        Lê arquivos OFX bancários extraindo transações via tags padrão <STMTTRN>.
        """
        imported_count = 0
        with open(file_path, "r", encoding="latin-1") as f:
            content = f.read()

        transactions = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL | re.IGNORECASE)

        for raw_tx in transactions:
            type_match = re.search(r"<TRNTYPE>(.*)", raw_tx, re.IGNORECASE)
            date_match = re.search(r"<DTPOSTED>(\d{8})", raw_tx, re.IGNORECASE)
            amount_match = re.search(r"<TRNAMT>([-+]?\d*\.?\d+)", raw_tx, re.IGNORECASE)
            memo_match = re.search(r"<MEMO>(.*)", raw_tx, re.IGNORECASE)

            if not (date_match and amount_match):
                continue

            raw_date = date_match.group(1).strip()
            date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

            amount_val = abs(float(amount_match.group(1).strip()))
            desc_str = memo_match.group(1).strip() if memo_match else "Transação OFX"

            clean_name, suggested_cat = normalize_merchant(desc_str)
            cat_name = suggested_cat or "Outros"
            cat = self.repo.get_or_create_category(cat_name, cat_type="EXPENSE")

            self.repo.add_transaction(
                amount=amount_val,
                category_id=cat.id,
                description=desc_str,
                date_str=date_str
            )
            imported_count += 1

        return imported_count

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Converte formatos DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY para ISO YYYY-MM-DD."""
        date_str = date_str.strip().split("T")[0].split(" ")[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return ""

    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Trata 'R$ 1.234,56', '-49.90', '49,90', '1234.56'."""
        cleaned = re.sub(r"[^\d,\.-]", "", amount_str).strip()
        if not cleaned:
            return 0.0

        # Se tiver vírgula como separador decimal (formato brasileiro)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            return abs(float(cleaned))
        except ValueError:
            return 0.0
