"""Configuration: env vars and CLI args, validated up front.

Why env-first: the demo, tests, eval, and CLI all share one config path.
Mock mode is the default so everything runs offline with zero keys.
"""
from __future__ import annotations

import argparse
import os


class Config:
    def __init__(self):
        self.mock = os.getenv("VITALIS_MOCK", "true").lower() in ("1", "true", "yes")
        self.api_key = os.getenv("VITALIS_API_KEY", "")
        self.model = os.getenv("VITALIS_MODEL", "gpt-4o-mini")
        self.api_base = os.getenv("VITALIS_API_BASE",
                                  "https://api.openai.com/v1").rstrip("/")
        # Abstention gates
        self.min_extraction_confidence = float(
            os.getenv("VITALIS_MIN_CONFIDENCE", "0.5"))
        self.timeout = float(os.getenv("VITALIS_TIMEOUT", "30"))

    @staticmethod
    def from_args(argv=None) -> "Config":
        p = argparse.ArgumentParser(description="Vitalis report agent")
        p.add_argument("--real", action="store_true",
                       help="use real LLM instead of mock")
        p.add_argument("--model", default=None)
        p.add_argument("--report", default=None,
                       help="report id to analyze (default: first)")
        args = p.parse_args(argv)
        cfg = Config()
        if args.real:
            cfg.mock = False
        if args.model:
            cfg.model = args.model
        cfg.report_arg = args.report
        return cfg

    def validate(self):
        if not self.mock and not self.api_key:
            raise ValueError("VITALIS_API_KEY required when mock is off")
