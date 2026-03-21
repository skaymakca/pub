#!/usr/bin/env python3
"""
Import World Cup planning docs from the AssistantClaudeCode task output
into the Hugo site's content/world-cup-2026/ directory.

What it does:
  1. Maps each source file (01-overview.md, etc.) to a Hugo target filename
  2. Strips the H1 title line (Hugo renders title from frontmatter)
  3. Prepends YAML frontmatter with title + weight
  4. Converts cross-references from NN-name.md#anchor to ../hugo-slug/#anchor
  5. Converts backtick code references like `03-dallas.md` to links

Usage: python3 scripts/import-planning-docs.py [SOURCE_DIR]
"""

import os
import re
import sys

DEFAULT_SRC = "/Users/sukru/code/AssistantClaudeCode/tasks/20260313-2026-world-cup-games/planning"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.join(SCRIPT_DIR, "..", "content", "world-cup-2026")

# (source_filename, hugo_filename, title, weight)
FILE_MAP = [
    ("01-overview.md", "overview.md", "Planning Overview", 1),
    ("02-match-analysis.md", "match-analysis.md", "Match Analysis — Group Stage Games", 2),
    ("03-dallas.md", "dallas-research.md", "Dallas — Family Trip Research", 3),
    ("04-toronto.md", "toronto-research.md", "Toronto — Family Trip Research", 4),
    ("05-philadelphia.md", "philadelphia-research.md", "Philadelphia — Trip Research", 5),
    ("06-city-comparison.md", "comparison.md", "City Comparison", 6),
    ("07-family-decision-guide.md", "dallas-vs-philly.md", "Dallas vs. Philadelphia — Family Decision Guide", 7),
    ("08-dallas-vs-toronto-decision.md", "dallas-vs-toronto-decision.md", "Should Sukru + Maja Join Dallas, or Just Meet in Toronto?", 8),
    ("09-flight-fares.md", "flight-fares.md", "Flight Research — All Legs", 9),
    ("10-hotel-pricing.md", "hotel-pricing.md", "Hotel Pricing — Actual Rates", 10),
    ("11-cost-analysis.md", "cost-analysis.md", "Cost Analysis — Scenario A vs Scenario B", 11),
    ("12-tickets-and-resale.md", "tickets-and-resale.md", "Tickets & Resale Strategy", 12),
    ("13-match74-gillette.md", "match74-gillette.md", "Match 74 — Round of 32 at Gillette", 13),
    ("14-scenario-a-summary.md", "scenario-a-summary.md", "Scenario A — Full Family to Dallas", 14),
    ("15-scenario-b-summary.md", "scenario-b-summary.md", "Scenario B — Skip Dallas, All 4 to Toronto", 15),
    ("16-booked-inventory.md", "booked-inventory.md", "Booked Inventory", 16),
    ("17-dallas-resale-action-plan.md", "dallas-resale-action-plan.md", "Dallas Ticket Resale — Action Plan", 17),
    ("18-jetblue-trueblue-strategy.md", "jetblue-trueblue-strategy.md", "JetBlue TrueBlue Points Strategy — LA Baby Shower vs World Cup Philly", 18),
]

# Build link mapping: source filename -> Hugo slug (for cross-references)
LINK_MAP = {src: hugo.replace(".md", "") for src, hugo, _, _ in FILE_MAP}


def strip_h1_and_leading_blanks(content: str) -> str:
    """Remove the first H1 line and any blank lines immediately after it."""
    lines = content.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    # Strip leading blank lines
    while lines and lines[0].strip() == "":
        lines = lines[1:]
    return "\n".join(lines)


def convert_links(content: str) -> str:
    """Convert cross-references from source format to Hugo format."""
    for src_name, hugo_slug in LINK_MAP.items():
        # Escape dots in filename for regex
        escaped = re.escape(src_name)
        # With anchor: (NN-name.md#something) -> (../hugo-slug/#something)
        content = re.sub(
            rf"\({escaped}#([^)]+)\)",
            rf"(../{hugo_slug}/#\1)",
            content,
        )
        # Without anchor: (NN-name.md) -> (../hugo-slug/)
        content = re.sub(
            rf"\({escaped}\)",
            rf"(../{hugo_slug}/)",
            content,
        )
    return content


def convert_backtick_refs(content: str) -> str:
    """Convert backtick code references to Hugo links."""
    replacements = {
        "`dallas-research.md`": "[Dallas](../dallas-research/)",
        "`toronto-research.md`": "[Toronto](../toronto-research/)",
        "`philadelphia-research.md`": "[Philadelphia](../philadelphia-research/)",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def process_file(src_dir: str, dest_dir: str, src_name: str, hugo_name: str, title: str, weight: int):
    src_path = os.path.join(src_dir, src_name)
    dest_path = os.path.join(dest_dir, hugo_name)

    if not os.path.exists(src_path):
        print(f"  SKIP (not found): {src_name}")
        return False

    with open(src_path, "r") as f:
        content = f.read()

    content = strip_h1_and_leading_blanks(content)
    content = convert_links(content)
    content = convert_backtick_refs(content)

    # Ensure content ends with a single newline
    content = content.rstrip("\n") + "\n"

    frontmatter = f'---\ntitle: "{title}"\nweight: {weight}\n---\n\n'

    with open(dest_path, "w") as f:
        f.write(frontmatter + content)

    print(f"  {src_name} -> {hugo_name} (weight: {weight})")
    return True


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    dest_dir = os.path.abspath(DEST_DIR)

    if not os.path.isdir(src_dir):
        print(f"Error: Source directory not found: {src_dir}")
        sys.exit(1)
    if not os.path.isdir(dest_dir):
        print(f"Error: Destination directory not found: {dest_dir}")
        sys.exit(1)

    print(f"Source:      {src_dir}")
    print(f"Destination: {dest_dir}")
    print()
    print("Processing files...")

    count = 0
    for src_name, hugo_name, title, weight in FILE_MAP:
        if process_file(src_dir, dest_dir, src_name, hugo_name, title, weight):
            count += 1

    print(f"\nDone. {count} files processed.")
    print("Run 'make dev' to preview, or 'git diff' to review changes.")


if __name__ == "__main__":
    main()
