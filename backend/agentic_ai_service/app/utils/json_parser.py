import json


def safe_json_parse(content: str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("LLM returned invalid JSON")