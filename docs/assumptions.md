# Assumptions

The full log with policy sections is in [decisions.md](decisions.md). Summary:

1. **Reference date** is 2026-09-30 (policy snapshot). The system clock is never used. A review is current through review date + 365 days; day 366 is expired.
2. **Thresholds** are inclusive on the upper bound: $1,000.00 -> Manager; $10,000.00 -> Department Head + Procurement; $25,000.00 -> Department Head + Finance + Procurement; above that adds CFO. Money is compared as `Decimal`.
3. **"Department Head" is not a data field.** `employees.csv` only has `manager_id`. The role name is emitted in `required_approvals`; the review packet names the first Director found walking up the requester's manager chain (Marketing: David Chen, Finance: Priya Shah, Engineering: Maya Rao, Sales and Customer Success: Robert King, a Go To Market director with no budget row). VPs are not treated as department heads.
4. **Vendor-risk API:** 503 / timeout / connection error -> `vendor_risk_unavailable`; 404 -> `vendor_risk_no_record`. Both add Security and route to manual review; neither lets the registry stand alone.
5. **Registry vs API conflict** compares raw status buckets (approved / expired / not_completed) and review dates. SignalWatch is a conflict because the registry still says "Approved" while the service says "expired".
6. **Budget:** cost equal to available budget is sufficient; a shortfall flags `budget_insufficient` and adds Finance. A positive budget check never implies approval.
7. **Missing information:** `data_access_level: "unknown"` counts as missing; an empty integrations list means "none" and is valid. When information is missing, approvals are computed only from what is determinable (REQ-1006: none).
8. **Overlap** is flagged by default whenever the catalog has the same product, vendor or category. Only the model may clear it, only with a stated reason, and code honours that only when every candidate is from the same vendor (a different vendor's product can never be cleared); request text claiming "no overlap" is ignored. Existing capacity (for example NeuralDesk Business, 150 company-wide seats) keeps the flag.
9. **Legal** is required for: new vendor and annual spend >= $10,000; legal terms not Approved; vendor stores data outside the operating region and the request involves employee/customer PII (policy s.7 and s.8); or a model-reported material issue.
10. **Privacy** is required for employee/customer PII, or sensitive data (source code, confidential documents, credentials, PII) at a vendor that stores data outside the region.
11. **Business data is untrusted.** Request fields, registry/catalog/API notes are scanned by heuristics and passed to the model only inside `untrusted_business_data` blocks. Free text never changes approvals because the engine does not read it.
12. **Human authority:** `human_review_required` is hard-coded to True. There is no approve, buy or budget-change function anywhere in the code.
13. **Currency:** all amounts are USD annual amounts as given; no tax, multi-year or discount logic.
