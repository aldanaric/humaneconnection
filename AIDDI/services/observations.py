from models.observation import Observation

def parse_observations(markdown: str) -> list[Observation]:
    """
    Parse an observations markdown document into Observation objects.
    """

    if not markdown.strip():
        return []

    observations = []

    # Split into sections, one per observation
    sections = markdown.split("## Area")

    for section in sections:
        section = section.strip()

        if not section:
            continue

        try:
            area, rest = section.split("### Observation", 1)
            observation, impact = rest.split("### Impact", 1)

            observations.append(
                Observation(
                    area=area.strip(),
                    observation=observation.strip(),
                    impact=impact.strip(),
                )
            )

        except ValueError:
            # Skip malformed sections
            continue

    return observations

def observations_to_markdown(
    observations: list[Observation]
) -> str:
    """ Convert Observations objects back to markdown"""

    sections = []

    for obs in observations:

        sections.append(
            f"""## Area
            {obs.area}

            ### Observation
            {obs.observation}

            ### Impact
            {obs.impact}
            """
        )

    return "\n".join(sections).strip() + "\n"
