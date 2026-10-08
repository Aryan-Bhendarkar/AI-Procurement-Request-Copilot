"""UI smoke test: the Streamlit app renders and runs every dataset request in engine-only mode (no LLM, no network)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from src import data_access as da
from src.review_packet import build_packet
from src.pipeline import analyze_request_full


class UiSmokeTests(unittest.TestCase):
    def test_app_renders_initial_page(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.title[0].value, "AI Procurement Request Copilot")

    def test_every_dataset_request_runs_in_engine_mode(self):
        for req in da.load_requests():
            with self.subTest(request=req["request_id"]):
                at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
                at.sidebar.selectbox[0].set_value(req["request_id"])
                at.sidebar.radio[1].set_value("engine")
                at.sidebar.selectbox[1].set_value("503" if req["request_id"] == "REQ-1009" else "none")
                at.sidebar.button[0].click().run()
                self.assertFalse(at.exception, [e.value for e in at.exception])
                if req["request_id"] == "REQ-1009":  # the simulated outage must show the degraded-mode banner
                    self.assertTrue(any("Degraded mode" in e.value for e in at.error))
                else:
                    self.assertFalse(at.error, [e.value for e in at.error])
                self.assertTrue(any("human approval required" in w.value for w in at.warning))

    def test_custom_request_form_runs_end_to_end(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        at.sidebar.radio[0].set_value("Custom request").run()
        for ti in at.sidebar.text_input:
            if ti.label.startswith("Annual cost"):
                ti.set_value("12000")
        at.sidebar.selectbox[1].set_value("customer_pii")  # data access level (requester is selectbox[0])
        [b for b in at.sidebar.button if b.label == "Use this request"][0].click().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        at.sidebar.radio[1].set_value("engine")
        [b for b in at.sidebar.button if b.label == "Run analysis"][0].click().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("Security", text)
        self.assertIn("Privacy", text)

    def test_review_packet_has_a_section_per_approver_and_no_approve_action(self):
        req = da.get_request("REQ-1002")
        res = analyze_request_full(req, "engine", {"vendor_risk": {"fault": "503"}})
        md = build_packet(req, res.decision, res.engine, {"name": "Sarah Lee", "department": "Marketing"})
        for role in res.decision.required_approvals:
            self.assertIn(f"### To: {role}", md)
        self.assertIn("recommendation only", md.lower())


if __name__ == "__main__":
    unittest.main()
