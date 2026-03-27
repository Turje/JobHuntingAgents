"""
Stable-anchor memory manager for Pylon.
Reads and updates memory/*.md files using append-after-header pattern.
Adapted from 21Agents KnowledgeManager.
"""

from __future__ import annotations

import logging
from pathlib import Path

_MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "memory"
_logger = logging.getLogger("knowledge")


class KnowledgeManager:
    """Manages stable-anchor memory files with safe append operations."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.memory_dir = memory_dir or _MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def read(self, filename: str) -> str:
        """Read a memory file's full contents."""
        path = self.memory_dir / filename
        if not path.exists():
            return ""
        return path.read_text()

    def read_section(self, filename: str, section_header: str) -> str:
        """Read content under a specific ## section header."""
        content = self.read(filename)
        if not content:
            return ""
        lines = content.split("\n")
        in_section = False
        section_lines: list[str] = []
        for line in lines:
            if line.strip().startswith("## ") and section_header in line:
                in_section = True
                continue
            elif in_section and line.strip().startswith("## "):
                break
            elif in_section:
                section_lines.append(line)
        return "\n".join(section_lines).strip()

    def append_to_section(self, filename: str, section_header: str, content: str) -> None:
        """Append content after a section header. Creates section if missing."""
        path = self.memory_dir / filename
        if not path.exists():
            path.write_text(f"## {section_header}\n{content}\n")
            _logger.info("Created %s with section '%s'", filename, section_header)
            return

        text = path.read_text()
        lines = text.split("\n")
        header_line = f"## {section_header}"

        for i, line in enumerate(lines):
            if line.strip() == header_line:
                lines.insert(i + 1, content)
                path.write_text("\n".join(lines))
                _logger.info("Appended to '%s' in %s", section_header, filename)
                return

        lines.append(f"\n{header_line}")
        lines.append(content)
        path.write_text("\n".join(lines))
        _logger.info("Added new section '%s' to %s", section_header, filename)

    def update_from_contract(self, kb_notes: str, evidence: str = "") -> None:
        """Update patterns.md from a RouterContract's kb_update_notes."""
        if not kb_notes:
            return
        entry = f"- {kb_notes}"
        if evidence:
            entry += f" (evidence: {evidence})"
        self.append_to_section("patterns.md", "Learned Patterns", entry)

    def record_progress(self, run_id: str, summary: str) -> None:
        """Record a pipeline run summary to progress.md."""
        entry = f"- [{run_id[:8]}] {summary}"
        self.append_to_section("progress.md", "Pipeline Runs", entry)
