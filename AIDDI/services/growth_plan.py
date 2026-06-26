from pathlib import Path
from typing import Dict, List, Tuple

GROWTH_PLAN_DIR = Path("data/GrowthPlan")
INPUT_DIR = GROWTH_PLAN_DIR / "Inputs"
OUTPUT_DIR = GROWTH_PLAN_DIR / "Outputs"
PROMPT_FILE = GROWTH_PLAN_DIR / "growth_plan_system_prompt.md"


def _split_last_first(folder_name: str) -> Tuple[str, str]:
    """Return (last, first) from a Last_First folder name."""
    parts = folder_name.split("_", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Growth Plan input folders must be named Last_First.")
    return parts[0], parts[1]


def list_person_folders() -> List[str]:
    """List available data/GrowthPlan/Inputs/Last_First folders."""
    if not INPUT_DIR.exists():
        return []

    excluded = {"outputs", "Outputs", "inputs", "Inputs", "prompts", "Prompts"}
    return sorted(
        p.name for p in INPUT_DIR.iterdir()
        if p.is_dir() and p.name not in excluded and "_" in p.name
    )


def _first_existing(label: str, candidates: List[Path]) -> Path:
    """
    Return the first existing candidate path.

    If none exist, return the preferred first candidate so the UI shows the
    intended canonical filename.
    """
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def expected_input_files(folder_name: str) -> Dict[str, Path]:
    """Build expected input paths for the selected Last_First folder."""
    last, first = _split_last_first(folder_name)
    folder = INPUT_DIR / folder_name

    # Canonical name is first. Backward-compatible variants cover the typo
    # "Peronality" and the earlier 12_ prefix mentioned in the spec.
    personality_candidates = [
        folder / f"2_Personality_Assessment_{first}_{last}.md",
        folder / f"2_Peronality_Assessment_{first}_{last}.md",
        folder / f"12_Personality_Assessment_{first}_{last}.md",
        folder / f"12_Peronality_Assessment_{first}_{last}.md",
    ]

    return {
        "Personality Assessment": _first_existing("Personality Assessment", personality_candidates),
        "Job Functions": folder / f"Job_Functions_{first}_{last}.md",
        "Observations": folder / f"Observations_{first}_{last}.md",
    }


def validate_inputs(folder_name: str) -> Tuple[bool, Dict[str, Path], List[str]]:
    """Check whether all required markdown inputs exist."""
    files = expected_input_files(folder_name)
    missing = [label for label, path in files.items() if not path.exists()]
    return len(missing) == 0, files, missing


def read_required_inputs(folder_name: str) -> Dict[str, str]:
    """Read all required markdown input files."""
    ok, files, missing = validate_inputs(folder_name)
    if not ok:
        raise FileNotFoundError(f"Missing Growth Plan input files: {', '.join(missing)}")

    return {label: path.read_text(encoding="utf-8") for label, path in files.items()}


def load_system_prompt() -> str:
    """Load the static Growth Plan system prompt."""
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_user_prompt(folder_name: str) -> str:
    """Combine selected person inputs into the user prompt sent to the model."""
    last, first = _split_last_first(folder_name)
    inputs = read_required_inputs(folder_name)

    return f"""
Create a Growth Plan for {first} {last} using the three markdown inputs below.

# Personality Assessment

```markdown
{inputs["Personality Assessment"]}
```

# Job Functions

```markdown
{inputs["Job Functions"]}
```

# Observations

```markdown
{inputs["Observations"]}
```
""".strip()


def output_path(folder_name: str) -> Path:
    """Return output path data/GrowthPlan/Outputs/GrowthPlan_Last_First.md."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / f"GrowthPlan_{folder_name}.md"


def save_growth_plan(folder_name: str, content: str) -> Path:
    """Save model output as markdown and return the path."""
    path = output_path(folder_name)
    path.write_text(content, encoding="utf-8")
    return path
