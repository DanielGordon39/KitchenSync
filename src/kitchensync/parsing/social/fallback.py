"""Concrete completeness warnings for review and fallback orchestration."""

from .models import LineAnalysis, SocialRecipeCandidate
from .patterns import EXTERNAL_FULL_RECIPE_CUE


def candidate_warnings(
    candidate: SocialRecipeCandidate,
    line_analyses: list[LineAnalysis],
) -> list[str]:
    """Describe missing fields that require review or external fallback."""

    warnings = []
    if not candidate.name:
        warnings.append("No reliable recipe name was found.")
    if not candidate.raw_ingredients:
        warnings.append("No ingredient section was found.")
    if not candidate.steps:
        source_text = "\n".join(line.text for line in line_analyses)
        if EXTERNAL_FULL_RECIPE_CUE.search(source_text):
            warnings.append(
                "The source points to a full printable recipe. Ask the user to open it "
                "and provide its URL before accepting this incomplete recipe."
            )
        else:
            warnings.append("No instruction section was found.")
    return warnings
