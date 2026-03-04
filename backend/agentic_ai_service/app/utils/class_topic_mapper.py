# app/utils/class_topic_mapper.py
"""
Maps (subject, class_level) -> topic_id based on a standard school curriculum.
Covers classes 6-12 for common subjects.
"""

from typing import Dict, Tuple

# Key: (subject_lower, class_level_lower)  e.g. ("math", "class 10")
# Value: topic_id string used downstream as the RAG and question-node topic
CLASS_TOPIC_MAP: Dict[Tuple[str, str], str] = {

    # ── MATH ────────────────────────────────────────────────────────────────
    ("maths", "class 6"):  "basic_arithmetic_and_fractions",
    ("maths", "class 7"):  "rational_numbers_and_algebra",
    ("maths", "class 8"):  "linear_equations_and_mensuration",
    ("maths", "class 9"):  "number_systems_and_coordinate_geometry",
    ("maths", "class 10"): "quadratic_equations_and_trigonometry",
    ("maths", "class 11"): "sets_relations_and_functions",
    ("maths", "class 12"): "calculus_and_linear_programming",

    ("mathematics", "class 6"):  "basic_arithmetic_and_fractions",
    ("mathematics", "class 7"):  "rational_numbers_and_algebra",
    ("mathematics", "class 8"):  "linear_equations_and_mensuration",
    ("mathematics", "class 9"):  "number_systems_and_coordinate_geometry",
    ("mathematics", "class 10"): "quadratic_equations_and_trigonometry",
    ("mathematics", "class 11"): "sets_relations_and_functions",
    ("mathematics", "class 12"): "calculus_and_linear_programming",

    # ── SCIENCE (general — classes 6-10) ────────────────────────────────────
    ("science", "class 6"):  "food_materials_and_living_world",
    ("science", "class 7"):  "nutrition_and_heat_and_acids",
    ("science", "class 8"):  "crop_production_and_microorganisms",
    ("science", "class 9"):  "matter_and_motion_and_atoms",
    ("science", "class 10"): "chemical_reactions_and_life_processes",

    # ── PHYSICS ─────────────────────────────────────────────────────────────
    ("physics", "class 11"): "mechanics_and_thermodynamics",
    ("physics", "class 12"): "electrostatics_and_optics_and_modern_physics",

    # ── CHEMISTRY ───────────────────────────────────────────────────────────
    ("chemistry", "class 11"): "atomic_structure_and_chemical_bonding",
    ("chemistry", "class 12"): "electrochemistry_and_organic_chemistry",

    # ── BIOLOGY ─────────────────────────────────────────────────────────────
    ("biology", "class 11"): "cell_biology_and_plant_physiology",
    ("biology", "class 12"): "genetics_and_evolution_and_ecology",

    # ── ENGLISH ─────────────────────────────────────────────────────────────
    ("english", "class 6"):  "prose_poetry_and_grammar_basics",
    ("english", "class 7"):  "reading_comprehension_and_writing_skills",
    ("english", "class 8"):  "literature_and_advanced_grammar",
    ("english", "class 9"):  "prose_poetry_and_letter_writing",
    ("english", "class 10"): "literature_and_formal_writing",
    ("english", "class 11"): "prose_and_creative_writing",
    ("english", "class 12"): "literature_and_functional_english",

    # ── SOCIAL SCIENCE ──────────────────────────────────────────────────────
    ("social science", "class 6"):  "history_geography_and_civics_basics",
    ("social science", "class 7"):  "medieval_history_and_physical_features",
    ("social science", "class 8"):  "modern_history_and_resources_and_development",
    ("social science", "class 9"):  "french_revolution_and_physical_geography",
    ("social science", "class 10"): "nationalism_and_economic_development",

    # ── HISTORY ─────────────────────────────────────────────────────────────
    ("history", "class 11"): "early_societies_and_empires",
    ("history", "class 12"): "indian_freedom_struggle_and_partition",

    # ── GEOGRAPHY ───────────────────────────────────────────────────────────
    ("geography", "class 11"): "physical_geography_and_atmosphere",
    ("geography", "class 12"): "human_geography_and_resources",

    # ── ECONOMICS ───────────────────────────────────────────────────────────
    ("economics", "class 11"): "introduction_to_microeconomics",
    ("economics", "class 12"): "macroeconomics_and_money_and_banking",

    # ── POLITICAL SCIENCE / CIVICS ──────────────────────────────────────────
    ("political science", "class 11"): "constitution_and_political_theory",
    ("political science", "class 12"): "contemporary_world_politics",
    ("civics", "class 6"):  "local_government_and_democracy",
    ("civics", "class 7"):  "state_government_and_federalism",
    ("civics", "class 8"):  "parliament_and_fundamental_rights",
    ("civics", "class 9"):  "democracy_and_electoral_politics",
    ("civics", "class 10"): "power_sharing_and_political_parties",

    # ── COMPUTER SCIENCE ────────────────────────────────────────────────────
    ("computer science", "class 9"):  "introduction_to_programming",
    ("computer science", "class 10"): "data_structures_and_sql",
    ("computer science", "class 11"): "python_programming_and_data_handling",
    ("computer science", "class 12"): "networking_and_database_management",

    # ── ACCOUNTANCY ─────────────────────────────────────────────────────────
    ("accountancy", "class 11"): "accounting_principles_and_journal_entries",
    ("accountancy", "class 12"): "partnership_accounts_and_financial_statements",

    # ── BUSINESS STUDIES ────────────────────────────────────────────────────
    ("business studies", "class 11"): "nature_of_business_and_forms_of_organisation",
    ("business studies", "class 12"): "management_principles_and_marketing",
}


def resolve_topic(subject: str, class_level: str) -> str:
    """
    Resolve a topic_id from a subject and class level string.

    Args:
        subject:     e.g. "Math", "Physics", "Computer Science"
        class_level: e.g. "Class 10", "class 12", "Class 9"

    Returns:
        A topic_id string (e.g. "quadratic_equations_and_trigonometry")

    Raises:
        ValueError: if the (subject, class_level) combination is not supported.
    """
    key = (subject.strip().lower(), class_level.strip().lower())

    topic_id = CLASS_TOPIC_MAP.get(key)
    if not topic_id:
        supported = sorted(
            {f"{s.title()} — {c.title()}" for s, c in CLASS_TOPIC_MAP}
        )
        raise ValueError(
            f"Unsupported combination: subject='{subject}', class_level='{class_level}'. "
            f"Supported combinations include: {', '.join(supported[:10])} … "
            f"(total {len(CLASS_TOPIC_MAP)} entries)."
        )
    return topic_id


def list_supported_mappings() -> list[dict]:
    """Return all supported (subject, class_level, topic_id) triples sorted."""
    return sorted(
        [
            {"subject": s.title(), "class_level": c.title(), "topic_id": t}
            for (s, c), t in CLASS_TOPIC_MAP.items()
        ],
        key=lambda x: (x["subject"], x["class_level"]),
    )
