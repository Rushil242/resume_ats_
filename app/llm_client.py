
"""
LLM client using the NEW google-genai SDK (google.genai).
The old google.generativeai is deprecated and must not be used.
"""
import json
import re
import io

from google import genai
from google.genai import types
from app.config import settings

_client = genai.Client(api_key=settings.GEMINI_API_KEY)
_MODEL = "gemini-3-flash-preview"

VALID_ESCAPES = set('"\\/bfnrtu')


def _extract_json_candidate(raw: str) -> str:
    s = raw.strip()
    # Strip markdown fences
    s = re.sub(r'^```[a-zA-Z]*\s*', '', s, flags=re.MULTILINE)
    s = re.sub(r'\s*```\s*$', '', s, flags=re.MULTILINE)
    s = s.strip()
    # Find first { or [
    ob = s.find('{')
    ab = s.find('[')
    starts = [i for i in (ob, ab) if i != -1]
    if starts:
        s = s[min(starts):]
    # Trim after last } or ]
    rb = s.rfind('}')
    rb2 = s.rfind(']')
    end = max(rb, rb2)
    if end != -1:
        s = s[:end + 1]
    return s.strip()


def _repair_invalid_escapes(s: str) -> str:
    """Remove invalid JSON escape sequences like \& \_ \# \$ \~ etc."""
    out = []
    in_string = False
    i = 0
    while i < len(s):
        ch = s[i]
        prev = s[i - 1] if i > 0 else ''
        if ch == '"' and prev != '\\':
            in_string = not in_string
            out.append(ch)
            i += 1
            continue
        if ch == '\\' and in_string:
            nxt = s[i + 1] if i + 1 < len(s) else ''
            if nxt in VALID_ESCAPES:
                out.append('\\')
                out.append(nxt)
                i += 2
            elif nxt == '':
                i += 1
            else:
                # Drop the backslash, keep the character
                out.append(nxt)
                i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _parse_json_safe(raw: str) -> dict:
    candidate = _extract_json_candidate(raw)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        repaired = _repair_invalid_escapes(candidate)
        return json.loads(repaired)


def call_vision(prompt: str, image_bytes: bytes, resume_text: str = "") -> dict:
    full_prompt = prompt.replace('{resume_text}', resume_text[:3000])
    parts = [full_prompt]
    if image_bytes:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        parts = [
            types.Part.from_bytes(data=buf.getvalue(), mime_type='image/png'),
            full_prompt,
        ]

    response = _client.models.generate_content(
        model=_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
        ),
    )
    raw = response.text
    print(f"[llm_vision] raw[:500]:\n{raw[:500]}\n")
    return _parse_json_safe(raw)


def call_text(system: str, user: str) -> str:
    response = _client.models.generate_content(
        model=_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text


def call_text_json(system: str, user: str) -> dict:
    response = _client.models.generate_content(
        model=_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type='application/json',
        ),
    )
    raw = response.text
    print(f"[llm_text] raw[:500]:\n{raw[:500]}\n")
    try:
        return _parse_json_safe(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"LLM returned invalid JSON after repair: {e}\n"
            f"Raw head: {raw[:600]}"
        )
