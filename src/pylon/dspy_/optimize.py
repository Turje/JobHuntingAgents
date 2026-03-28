"""
MIPROv2 optimization runner for CastNet DSPy modules.

CLI usage:
    python -m pylon.dspy_.optimize --agent discovery --output-dir data/optimized
    python -m pylon.dspy_.optimize --agent all --output-dir data/optimized
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import dspy

from pylon.dspy_.datasets import load_examples
from pylon.dspy_.lm import configure_dspy
from pylon.dspy_.metrics import (
    contact_metric,
    discovery_metric,
    outreach_metric,
    research_metric,
    resume_metric,
    skills_metric,
)
from pylon.dspy_.modules import (
    ContactModule,
    DiscoveryModule,
    OutreachModule,
    ResearchModule,
    ResumeModule,
    SkillsModule,
)

_logger = logging.getLogger("dspy_.optimize")

AGENT_REGISTRY: dict[str, dict] = {
    "discovery": {"module_cls": DiscoveryModule, "metric": discovery_metric},
    "research": {"module_cls": ResearchModule, "metric": research_metric},
    "skills": {"module_cls": SkillsModule, "metric": skills_metric},
    "contact": {"module_cls": ContactModule, "metric": contact_metric},
    "resume": {"module_cls": ResumeModule, "metric": resume_metric},
    "outreach": {"module_cls": OutreachModule, "metric": outreach_metric},
}


def optimize_agent(agent_name: str, output_dir: str) -> None:
    """Run MIPROv2 optimization for a single agent."""
    if agent_name not in AGENT_REGISTRY:
        _logger.error("Unknown agent: %s. Available: %s", agent_name, list(AGENT_REGISTRY))
        return

    entry = AGENT_REGISTRY[agent_name]
    examples = load_examples(agent_name)
    if len(examples) < 5:
        _logger.error(
            "Need at least 5 examples for %s, found %d. "
            "Add examples to data/eval/%s_examples.jsonl",
            agent_name, len(examples), agent_name,
        )
        return

    # 80/20 train/val split
    split = int(len(examples) * 0.8)
    train_set = examples[:split]
    val_set = examples[split:]
    _logger.info(
        "Optimizing %s: %d train, %d val examples", agent_name, len(train_set), len(val_set)
    )

    module = entry["module_cls"]()
    metric = entry["metric"]

    optimizer = dspy.MIPROv2(
        metric=metric,
        auto="medium",
    )

    optimized = optimizer.compile(
        module,
        trainset=train_set,
        valset=val_set,
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    save_path = out_path / f"{agent_name}.json"
    optimized.save(str(save_path))
    _logger.info("Saved optimized %s to %s", agent_name, save_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize DSPy modules with MIPROv2")
    parser.add_argument(
        "--agent",
        required=True,
        help="Agent to optimize (discovery, research, skills, contact, resume, outreach, or 'all')",
    )
    parser.add_argument(
        "--output-dir",
        default="data/optimized",
        help="Directory to save optimized module state (default: data/optimized)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(levelname)s | %(message)s")

    configure_dspy()

    if args.agent == "all":
        for name in AGENT_REGISTRY:
            _logger.info("=== Optimizing %s ===", name)
            optimize_agent(name, args.output_dir)
    else:
        optimize_agent(args.agent, args.output_dir)


if __name__ == "__main__":
    main()
