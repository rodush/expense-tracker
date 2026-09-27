from __future__ import annotations

import os


def pytest_configure() -> None:
    os.environ["CATEGORIES"] = "Food,Transport,Utilities,Shopping,Other"
    os.environ["GEMINI_API_KEY"] = ""
