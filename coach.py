#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from datetime import date


DEFAULT_MD_FILES = ["goals.md", "skills.md", "injuries.md", "availability.md"]

PROMPT_TEMPLATE = """SYSTEM / ROLE

You are my Gym Coach AI Agent. You generate training sessions that prioritize health, strength, flexibility, and endurance. You must respect my constraints and avoid sudden spikes in workload.

DATA SOURCES (READ FIRST)

1) Read these Markdown (source of truth):

- data/goals.md
- data/skills.md
- data/injuries.md
- data/availability.md

1) Read and analyze all YAML that are in the prompt

Use them to learn my personal trainer’s session style and formatting patterns (exercise order, blocks, typical rep ranges, typical loads, rounding, warm-up structure). Keep continuity with my trainer’s approach.

RULES

- Output must be 5 WEEK plan for my available days (Mon, Tue, Wed, Thu, Sun).
- Each session must fit within 60 minutes including warm-up.
- Each sessions must include 9 excersises in total divided into 3 blocks of 3 exercises each.
- Each block must have a short title (e.g., "Strength Upper Body", "Core + Mobility", "Endurance Run").
- Each exercise must have Load, Reps, Rounds, and Notes fields.
- Use only exercises that I can do with my available equipment and mobility.
- Prioritize my known exercises unless the YAML history strongly indicates other staples.
- Running volume must increase gradually; protect my ankle (past sprain, occasional mild pain ~2/7). Avoid sudden increases in impact or intensity.
- I swim at least once per week; I am starting to run.
- I have: barbell + plates, dumbbells, stability ball, plyometric box.
- I have no mobility limitations (but include mobility work as supportive).
- Prefer exercises I already know (Deadlift, Bench Press, Single-Arm Dumbbell Row, Barbell Row) unless the YAML history strongly indicates other staples.

AUTO-PROGRESSION:

- Review the training history to establish a baseline.
- Weeks 1–3 of the new block should progress gradually from that baseline.
- Week 4 may be the highest load/volume.
- Week 5 should be a deload (10–20% volume reduction).
- Do not exceed safe progression rules for running, strength, or swimming.
- Each day should work different training cores. 
- Should have at least one swimming training on wednesday.

OUTPUT FORMAT
Return ONLY:

1) Create an excel with the information for 5 weeks (one spreadsheet per week).
2) A short line with the week title (example: "Week Plan — Week of YYYY-MM-DD").
NO extra commentary. NO markdown tables. NO bullets. No explanations.

Spreadsheet columns must be exactly:
Day,Session Title,Exercise,Block, Load,Reps,Notes

Definitions:

- Day: Monday/Tuesday/Wednesday/Thursday/Sunday
- Session Title: short session name (e.g., "Strength Lower + Core")
- Exercise: exercise name in English and spanish
- Load: write as kg (e.g., "40 kg")
- Reps: reps per round or time (e.g., "10-12" or "25 min")
- Block: separate blocks of 3 exercises each (e.g., "Block 1", "Block 2", "Block 3")
- Notes: brief cues or rest times

QUALITY CHECK BEFORE OUTPUT

- Ensure every row has ALL columns filled
- Ensure YouTubeURL and PhotoURL are valid https URLs
- Ensure session duration fits 60 minutes
- Ensure gradual running progression and ankle protection

========================
MARKDOWN CONTEXT
========================
{markdown_context}

========================
YAML TRAINING HISTORY (REFERENCE ONLY)
========================
{yaml_context}
"""

def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_markdown_context(data_dir: Path, md_files: list[str]) -> str:
    chunks: list[str] = []
    for name in md_files:
        p = data_dir / name
        if not p.exists():
            # Don't hard-fail; include a clear marker for the LLM + user
            chunks.append(f"--- {name} (MISSING: {p}) ---\n")
            continue
        chunks.append(f"--- {name} ---\n{read_text_file(p)}\n")
    return "\n".join(chunks).strip()


def load_yaml_context(yaml_dir: Path, max_files: int = 50, max_chars_per_file: int = 12000) -> str:
    if not yaml_dir.exists() or not yaml_dir.is_dir():
        return "(No YAML folder found. Skipping.)"

    yaml_files = sorted(list(yaml_dir.glob("*.yml")) + list(yaml_dir.glob("*.yaml")))
    if not yaml_files:
        return "(No YAML files found. Skipping.)"

    chunks: list[str] = []
    for p in yaml_files[:max_files]:
        text = read_text_file(p)
        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file] + "\n... (truncated)\n"
        chunks.append(f"--- {p.name} ---\n{text}\n")
    if len(yaml_files) > max_files:
        chunks.append(f"... ({len(yaml_files) - max_files} more YAML files not included)\n")
    return "\n".join(chunks).strip()


def build_prompt(markdown_context: str, yaml_context: str) -> str:
    return PROMPT_TEMPLATE.format(
        markdown_context=markdown_context,
        yaml_context=yaml_context,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Ollama prompt from your vault files.")
    parser.add_argument("--data-dir", default="data", help="Folder containing Markdown files (default: data)")
    parser.add_argument("--yaml-dir", default="gym-data", help="Folder containing YAML trainer sessions (default: gym-data)")
    parser.add_argument("--out", default="prompt.txt", help="Output prompt file (default: prompt.txt)")
    parser.add_argument("--model", default="llama3.1:8b", help="Model name to print example ollama command")
    parser.add_argument("--max-yaml-files", type=int, default=50, help="Max YAML files to include (default: 50)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    yaml_dir = Path(args.yaml_dir)
    out_path = Path(args.out)

    markdown_context = load_markdown_context(data_dir, DEFAULT_MD_FILES)
    yaml_context = load_yaml_context(yaml_dir, max_files=args.max_yaml_files)

    prompt = build_prompt(markdown_context, yaml_context)

    out_path.write_text(prompt, encoding="utf-8")
    print(f"[OK] Wrote prompt to: {out_path.resolve()}")
    print(f"[Info] Prompt length: {len(prompt)} characters")
    print()
    print("Run Ollama manually like this:")
    print(f'  ollama run {args.model} < "{out_path}"')
    print()
    print("Tip: Save the model output to a CSV file:")
    print(f'  ollama run {args.model} < "{out_path}" > week_plan.csv')
    print("Then open week_plan.csv in Excel, or import it.")


if __name__ == "__main__":
    main()
