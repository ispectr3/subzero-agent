import unittest
from engine.models import Transaction, Category
from engine.detector import SubscriptionDetector, normalize_merchant
from engine.anomaly import AnomalyDetector


class TestSubscriptionDetector(unittest.TestCase):
    def test_normalize_merchant(self):
        name, cat = normalize_merchant("NETFLIX.COM 192837 BR")
        self.assertEqual(name, "Netflix")
        self.assertEqual(cat, "Lazer & Entretenimento")

        name, cat = normalize_merchant("SPOTIFY AB PREMIUM")
        self.assertEqual(name, "Spotify")

    def test_recurring_monthly_detection(self):
        txs = [
            Transaction(1, 49.90, 1, "NETFLIX.COM", "2026-06-10", category_type="EXPENSE"),
            Transaction(2, 49.90, 1, "NETFLIX.COM", "2026-07-10", category_type="EXPENSE"),
            Transaction(3, 59.90, 1, "NETFLIX.COM", "2026-08-10", category_type="EXPENSE"),
        ]
        detector = SubscriptionDetector(txs)
        subs, anomalies = detector.detect()

        self.assertEqual(len(subs), 1)
        sub = subs[0]
        self.assertEqual(sub.name, "Netflix")
        self.assertEqual(sub.amount, 59.90)
        self.assertEqual(sub.cadence, "MONTHLY")
        self.assertEqual(sub.charges_count, 3)

        # Price increase anomaly
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].type, "PRICE_INCREASE")
        self.assertEqual(anomalies[0].merchant, "Netflix")


class TestAnomalyDetector(unittest.TestCase):
    def test_duplicate_detection(self):
        txs = [
            Transaction(1, 85.00, 1, "RESTAURANTE CENTRAL", "2026-08-15", category_type="EXPENSE"),
            Transaction(2, 85.00, 1, "RESTAURANTE CENTRAL", "2026-08-15", category_type="EXPENSE"),
            Transaction(3, 120.00, 1, "OUTRO LUGAR", "2026-08-15", category_type="EXPENSE"),
        ]
        detector = AnomalyDetector(txs)
        dups = detector.detect_duplicates(max_hours_delta=24)

        self.assertEqual(len(dups), 1)
        self.assertEqual(dups[0].type, "DUPLICATE_CHARGE")
        self.assertEqual(dups[0].amount, 85.00)


if __name__ == "__main__":
    unittest.main()
