import json
import logging
import re

logger = logging.getLogger(__name__)


def repair_json(raw_text: str) -> list[dict]:
    """Parse JSON from potentially messy LLM output.
    Attempts multiple fallback strategies.
    """
    if not str(raw_text).strip():
        raise ValueError("Received empty or missing response from LLM.")

    # Strategy 1: Direct parsing
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Remove markdown code fences
    cleaned = re.sub(r"```json\s*", "", raw_text)
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find the first '[' and last ']'
    start_idx = raw_text.find("[")
    end_idx = raw_text.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        bracketed_text = raw_text[start_idx : end_idx + 1]
        try:
            return json.loads(bracketed_text)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Extract JSON objects manually
    extracted_objects = []
    object_matches = re.findall(r"\{[^{}]*\}", raw_text)

    for match in object_matches:
        match = re.sub(r",\s*([\]}])", r"\1", match)
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict) and "Date" in parsed:
                extracted_objects.append(parsed)
        except json.JSONDecodeError:
            continue

    if extracted_objects:
        return extracted_objects

    raise ValueError(
        f"Could not extract any standard JSON dictionary.\nRaw Response: {raw_text[:300]}..."
    )
