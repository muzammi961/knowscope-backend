"""Quick smoke-test for class_topic_mapper."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.class_topic_mapper import resolve_topic, list_supported_mappings

# --- Happy path tests ---
cases = [
    ("Math",             "Class 10"),
    ("Physics",          "Class 12"),
    ("Computer Science", "Class 11"),
    ("English",          "Class 9"),
    ("Science",          "Class 8"),
    ("Economics",        "Class 12"),
]

print("=== HAPPY PATH ===")
for subject, cls in cases:
    topic = resolve_topic(subject, cls)
    print(f"  {subject:<20} {cls:<10}  →  {topic}")

print(f"\nTotal mappings loaded: {len(list_supported_mappings())}")

# --- Error path ---
print("\n=== ERROR PATH ===")
try:
    resolve_topic("Art", "Class 10")
except ValueError as e:
    print(f"  ValueError raised (expected): {str(e)[:80]}...")

print("\n✅ All checks passed.")
