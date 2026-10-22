"""LLM client: deterministic mock (default) + real OpenAI-compatible endpoint.

Why mock-first: the demo, tests, and eval must run offline, free, and
reproducibly. Mock mode exercises the whole graph; real mode only swaps
the text generator for the Counselor's prose. Safety-critical flag math
stays rule-based in BOTH modes — an LLM never guesses a reference range.
"""
from __future__ import annotations

import json
import urllib.request


class LLMClient:
    def __init__(self, config):
        self.cfg = config

    def complete(self, system: str, user: str) -> str:
        if self.cfg.mock:
            return self._mock(system, user)
        return self._real(system, user)

    def _mock(self, system: str, user: str) -> str:
        # Deterministic counseling prose from the structured brief the
        # Counselor passes in. No hallucination surface: numbers come
        # from the brief, never from the model.
        try:
            brief = json.loads(user)
        except Exception:
            return "Summary unavailable in mock mode."
        abn = brief.get("abnormal", [])
        n = brief.get("total", 0)
        if not abn:
            core = (f"All {n} markers are within their reference ranges. "
                    f"No abnormal values were found in this report.")
        else:
            items = "; ".join(
                f"{a['name']} {a['value']} {a['unit']} "
                f"({a['flag']}; ref {a['ref_low']}-{a['ref_high']})"
                for a in abn)
            core = (f"{len(abn)} of {n} markers are outside their reference "
                    f"ranges: {items}.")
        follow = ("Consider discussing these results with your clinician, "
                  "who can interpret them in the context of your history. "
                  "If any value is marked critical, seek prompt care.")
        return f"{core} {follow}"

    def _real(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": self.cfg.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.2,
        }).encode()
        req = urllib.request.Request(
            f"{self.cfg.api_base}/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.cfg.api_key}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout) as r:
                data = json.loads(r.read().decode())
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            # Fail soft: fall back to mock prose rather than crashing the demo.
            return self._mock(system, user) + f"\n[LLM fallback: {exc}]"
