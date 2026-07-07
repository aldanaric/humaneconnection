from enum import Enum

class DocumentType(Enum):
    PERSONALITY = "personality"
    JOB_FUNCTIONS = "job_functions"
    OBSERVATIONS = "observations"
    GROWTH_PLAN = "growth_plan"

    @property
    def filename(self) -> str:
        return f"{self.value}.md"

    @property
    def display_name(self) -> str:
        return self.value.replace("_"," ").title()
