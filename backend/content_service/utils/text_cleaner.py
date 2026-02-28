"""
text_cleaner.py
===============
Generic PDF text cleaning utilities.
Removes common PDF artifacts: page numbers, form-feeds, excessive whitespace,
and short repeated header/footer lines — works for any textbook, any publisher.
"""
import re


# ── Patterns to strip completely ────────────────────────────────────────────

# Standalone page numbers (e.g. "12", "— 12 —", "Page 12", "12 |")
PAGE_NUMBER_RE = re.compile(
    r"(?m)^[\s\-–—|]*(?:Page\s+)?\d{1,4}[\s\-–—|]*$",
    re.IGNORECASE
)

# Form-feed / PDF artifact characters
FORM_FEED_RE = re.compile(r"\x0c")

# Three or more consecutive newlines → collapse to two
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Two or more consecutive spaces/tabs → single space
MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def _is_repeated_header(line: str, seen_lines: set, min_len: int = 4) -> bool:
    """Return True if a short line has already appeared (likely a repeating header/footer)."""
    stripped = line.strip()
    if len(stripped) < min_len or len(stripped) > 80:
        return False
    if stripped in seen_lines:
        return True
    seen_lines.add(stripped)
    return False


def normalize_text(text: str) -> str:
    """
    Clean raw PDF text for storage in the database.
    - Remove form-feed characters.
    - Remove standalone page numbers.
    - Collapse excessive whitespace and blank lines.
    - Remove repeated short header/footer lines.
    Returns cleaned text, or empty string if nothing meaningful remains.
    """
    # Step 1: Remove PDF form-feed artifacts
    text = FORM_FEED_RE.sub(" ", text)

    # Step 2: Remove standalone page-number lines
    text = PAGE_NUMBER_RE.sub("", text)

    # Step 3: Re-split into lines and remove repeated short header/footer lines
    lines = text.split("\n")
    seen: set = set()
    cleaned_lines = [
        line for line in lines
        if not _is_repeated_header(line, seen)
    ]
    text = "\n".join(cleaned_lines)

    # Step 4: Collapse multiple blank lines
    text = MULTI_NEWLINE_RE.sub("\n\n", text)

    # Step 5: Collapse multiple spaces/tabs
    text = MULTI_SPACE_RE.sub(" ", text)

    return text.strip()
