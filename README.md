\# LGS Test Suite — SP-21 Reference



Reference pytest implementation for SP-21, demonstrating seven test types

used across LGS applications.



\## Test Types



| Type | Location | Count |

|------|----------|-------|

| Unit | `tests/test\_unit\_password\_validator.py` | 7 |

| Validation | `tests/test\_validation\_user\_registration.py` | 13 |

| Regression | `tests/test\_regression\_discount\_calculator.py` | 14 |

| Edge Case | `tests/test\_edge\_order\_processor.py` | 15 |

| Backend | `tests/test\_backend\_claims\_service.py` | 14 |

| GET API | `tests/test\_get\_policy\_api.py` | 13 |

| PUT API | `tests/test\_put\_user\_profile\_api.py` | 18 |



\## Setup



&#x20;   python -m venv .venv

&#x20;   .venv\\Scripts\\activate.bat

&#x20;   pip install pytest pytest-cov fastapi "uvicorn\[standard]" httpx freezegun



\## Run



&#x20;   pytest -v

&#x20;   pytest --cov=src --cov=app --cov-report=term-missing

