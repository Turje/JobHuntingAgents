"""
Evaluation dataset loading for DSPy optimization.
Reads JSONL files from data/eval/ and converts them to dspy.Example objects.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import dspy

_logger = logging.getLogger("dspy_.datasets")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_EVAL_DIR = _PROJECT_ROOT / "data" / "eval"


def load_examples(agent_name: str) -> list[dspy.Example]:
    """Load evaluation examples from data/eval/{agent_name}_examples.jsonl.

    Each line is a JSON object with input fields and optional expected output.
    Returns list of dspy.Example with appropriate input_keys set.
    """
    path = _EVAL_DIR / f"{agent_name}_examples.jsonl"
    if not path.exists():
        _logger.warning("No examples found at %s", path)
        return []

    examples: list[dspy.Example] = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ex = dspy.Example(**data)
                # Mark input fields (everything except fields ending in _expected)
                input_keys = [k for k in data if not k.endswith("_expected")]
                ex = ex.with_inputs(*input_keys)
                examples.append(ex)
            except (json.JSONDecodeError, Exception) as exc:
                _logger.warning("Skipping line %d in %s: %s", line_num, path, exc)
                continue

    _logger.info("Loaded %d examples for %s", len(examples), agent_name)
    return examples


def bootstrap_from_pipeline_run(context_dict: dict[str, Any]) -> dict[str, dspy.Example]:
    """Convert a pipeline run context dict into DSPy examples for each agent.

    Args:
        context_dict: Serialized PipelineContext as a dict

    Returns:
        Dict mapping agent_name -> dspy.Example
    """
    examples: dict[str, dspy.Example] = {}

    query = context_dict.get("query", "")
    candidates = context_dict.get("candidates", [])
    profiles = context_dict.get("profiles", [])
    skills = context_dict.get("skills", [])
    contacts = context_dict.get("contacts", [])
    resumes = context_dict.get("resumes", [])
    drafts = context_dict.get("drafts", [])

    if candidates:
        examples["discovery"] = dspy.Example(
            query=query,
            companies_json=json.dumps(candidates),
        ).with_inputs("query")

    if profiles:
        examples["research"] = dspy.Example(
            query=query,
            companies_json=json.dumps(candidates),
            profiles_json=json.dumps(profiles),
        ).with_inputs("query", "companies_json")

    if skills:
        examples["skills"] = dspy.Example(
            query=query,
            profiles_json=json.dumps(profiles),
            analyses_json=json.dumps(skills),
        ).with_inputs("query", "profiles_json")

    if contacts:
        examples["contact"] = dspy.Example(
            query=query,
            companies_json=json.dumps(candidates),
            contacts_json=json.dumps(contacts),
        ).with_inputs("query", "companies_json")

    if resumes:
        examples["resume"] = dspy.Example(
            query=query,
            companies_json=json.dumps(candidates),
            resumes_json=json.dumps(resumes),
        ).with_inputs("query", "companies_json")

    if drafts:
        examples["outreach"] = dspy.Example(
            query=query,
            contacts_json=json.dumps(contacts),
            drafts_json=json.dumps(drafts),
        ).with_inputs("query", "contacts_json")

    return examples
