from pathlib import Path
from models.profile import Profile
from repositories.profile_repository import ProfileRepository

from pathlib import Path

# --- Paths (Matching Growth Plan Architecture) ---
DIAGNOSTIC_DIR = Path("data/DiagnosticSummary")
OUTPUT_DIR = DIAGNOSTIC_DIR / "Outputs"

# Point to the prompt file living inside the diagnostic directory
PROMPT_FILE = DIAGNOSTIC_DIR / "Intelligence-Summary-Prompt.md"

def load_system_prompt() -> str:
    """Load the static Diagnostic Intelligence Summary system prompt."""
    if not PROMPT_FILE.exists():
        # Added .absolute() to the error message so if it fails, it tells you exactly where it looked!
        raise FileNotFoundError(f"Prompt file not found at: {PROMPT_FILE.absolute()}")
    return PROMPT_FILE.read_text(encoding="utf-8")

def build_user_prompt(intake_data: str, context_data: str, rag_context: str = "") -> str:
    """Combine intake data, analyst context, and RAG interventions into the user prompt."""
    prompt = f"Here is the raw client intake data:\n\n{intake_data}\n\n"
    
    if context_data and context_data.strip():
        prompt += f"Additional Analyst Context to consider:\n\n{context_data}\n\n"
        
    if rag_context and rag_context.strip():
        prompt += (
            "--- SUPPORTING INTERVENTION DOCUMENTS ---\n"
            "Use the following internal documentation to inform the "
            "'Preliminary Intervention Pathway Recommendations' section:\n\n"
            f"{rag_context}\n\n"
        )
        
    return prompt.strip()

def output_path(profile: Profile) -> Path:
    """Return output path data/DiagnosticSummary/Outputs/Diagnostic_Summary_Last_First.md."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Using a safe fallback if first/last name aren't strictly defined
    first = getattr(profile, 'first_name', 'Client')
    last = getattr(profile, 'last_name', 'Profile')
    return OUTPUT_DIR / f"Diagnostic_Summary_{last}_{first}.md"

def save_diagnostic_summary(profile: Profile, content: str) -> Path:
    """Save model output as markdown and return the path."""
    path = output_path(profile)
    path.write_text(content, encoding="utf-8")
    return path