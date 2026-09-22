"""Domain-based scenario generation for RadField-Bench.

Scenarios are organized by real-world business domains (nuclear plant patrol,
source search, security screening, waste management), each with families at
simple/medium/hard difficulty. See ``domains.py`` for the templates and
``generator.py`` for the deterministic generator.
"""
from .domains import DIFFICULTIES, FAMILIES, FAMILY_INDEX, DOMAIN_DESCRIPTIONS
from .generator import (
    generate_all,
    generate_scenario,
    scenario_to_dict,
    write_scenario,
    family_summary,
)

__all__ = [
    "DIFFICULTIES",
    "FAMILIES",
    "FAMILY_INDEX",
    "DOMAIN_DESCRIPTIONS",
    "generate_all",
    "generate_scenario",
    "scenario_to_dict",
    "write_scenario",
    "family_summary",
]
