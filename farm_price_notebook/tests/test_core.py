import json, tempfile, unittest
from datetime import date, timedelta
from pathlib import Path

from pricebook import analytics, exporters
from pricebook.importer import import_csv
from pricebook.seed import build_rows
from pricebook.storage import Store
from pricebook.validation import ValidationError, validate_entry

GOOD = {"date": "2026-01-05", "produce": " tomato ", "category": "vegetable", "market": "Local Mandi", "price": "₹1,042.50"}


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "p.json"
        self.store = Store(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_validation_cleans(self):
        c = validate_entry(GOOD)
        self.assertEqual((c["produce"], c["category"], c["price"]), ("Tomato", "Vegetable", 1042.5))

    def test_validation_collects_all_errors(self):
        with self.assertRaises(ValidationError) as cm:
            validate_entry({"date": "2999-01-01", "produce": "", "category": "x", "market": "", "price": "abc"})
        self.assertEqual(len(cm.exception.errors), 5)

    def test_price_boundaries(self):
        for p in ("0.5", "5000"):
            validate_entry({**GOOD, "price": p})
        for p in ("0.49", "5000.01", "-1", "nan", "inf", ""):
            with self.assertRaises(ValidationError):
                validate_entry({**GOOD, "price": p})

    def test_persistence_roundtrip_and_duplicates(self):
        self.store.add(GOOD)
        self.assertEqual(len(Store(self.path).records), 1)
        with self.assertRaises(ValidationError):
            self.store.add(GOOD)

    def test_corrupt_file_recovered(self):
        self.path.write_text("{not json", encoding="utf-8")
        s = Store(self.path)
        self.assertEqual(s.records, [])
        self.assertTrue(s.recovery_note)
        self.assertEqual(json.loads(self.path.read_text())["records"], [])
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.corrupt-*"))), 1)

    def test_search(self):
        for r in build_rows():
            self.store.add(r, save=False)
        self.assertTrue(all(r.category == "Fruit" for r in self.store.search(categories=["Fruit"])))
        self.assertEqual(len(self.store.search("tomato")), 5)

    def test_seed_analytics_and_warnings(self):
        for r in build_rows():
            self.store.add(r, save=False)
        self.assertEqual(len(self.store.records), 40)
        stats = {s["produce"]: s for s in analytics.produce_stats(self.store.records)}
        self.assertEqual(stats["Rice"]["trend"], "Rising")
        msgs = " ".join(f["message"] for f in analytics.warnings(self.store.records))
        self.assertIn("Tomato", msgs)

    def test_stale_warning(self):
        self.store.add({**GOOD, "date": "2026-01-01"})
        for i in range(2, 7):
            self.store.add({**GOOD, "date": f"2026-01-0{i}"})
        fl = analytics.warnings(self.store.records, today=date(2026, 6, 1))
        self.assertTrue(any(f["level"] == "info" for f in fl))

    def test_import_error_log(self):
        t = date.today()
        text = f"date,produce,category,market,price\n{t},Cabbage,Vegetable,Mandi,22\n{t},Apple,Bad,Mandi,5\n{t + timedelta(1)},Fig,Fruit,Mandi,9\n"
        res = import_csv(text, self.store)
        self.assertEqual(res.imported, 1)
        self.assertEqual([n for n, _ in res.errors], [3, 4])
        self.assertEqual(import_csv("a,b\n1,2\n", self.store).imported, 0)

    def test_exports(self):
        for r in build_rows():
            self.store.add(r, save=False)
        self.assertIn("## Price trends", exporters.to_markdown(self.store.records))
        self.assertIn("WARNINGS", exporters.to_text(self.store.records))
        self.assertEqual(len(exporters.to_csv(self.store.records).strip().splitlines()), 41)


if __name__ == "__main__":
    unittest.main()
