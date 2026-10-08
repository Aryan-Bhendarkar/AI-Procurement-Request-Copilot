"""Scripted fake LLM client (OpenAI-SDK shaped) so tests never touch the network."""
from __future__ import annotations

import json
from types import SimpleNamespace


def tool_call(name: str, args: dict, call_id: str = "c1"):
    return SimpleNamespace(id=call_id, type="function", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def message(content: str | None = None, tool_calls: list | None = None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or None)


class FakeOpenAI:
    """`replies` is a list of messages (or Exceptions) returned in order, one per chat.completions.create call."""

    def __init__(self, replies: list):
        self.replies = list(replies)
        self.requests: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.replies:
            raise AssertionError("fake LLM script exhausted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, cost=0.001)
        return SimpleNamespace(choices=[SimpleNamespace(message=reply)], usage=usage)


def final_json(**kw) -> str:
    base = {"recommendation": "Route for the required reviews.", "next_step": "Send the evidence package to the approvers.",
            "overlap_cleared": False, "overlap_reason": None, "injection_detected": False, "injection_note": None,
            "legal_issue_identified": False, "legal_issue_reason": None, "ambiguity_notes": [], "evidence_notes": [], "challenges": []}
    base.update(kw)
    return json.dumps(base)


def single_script(request_id: str, vendor: str, **final):
    """Typical agent A run: three data tools in parallel, the engine, then the final JSON."""
    return [
        message(tool_calls=[tool_call("get_request_context", {"request_id": request_id}, "a"),
                            tool_call("find_existing_software", {"request_id": request_id}, "b"),
                            tool_call("get_vendor_status", {"vendor_name": vendor}, "c")]),
        message(tool_calls=[tool_call("run_policy_checks", {"request_id": request_id}, "d")]),
        message(content=final_json(**final)),
    ]
