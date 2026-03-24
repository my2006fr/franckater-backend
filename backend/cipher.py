# cipher.py — Franckate Cipher Engine v2
# Original algorithm by Franck, enhanced for API use

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "1234567890"
FIGURES = "!@#$%^&*()_+-=`~<>,.?{}[]| "

# Map char → (category_code, index)
def _encode_char(ch):
    for seq, code in [(UPPER, "U"), (LOWER, "L"), (DIGITS, "D"), (FIGURES, "F")]:
        idx = seq.find(ch)
        if idx != -1:
            return code, idx
    return None, None   # unsupported char — pass through

def _decode_token(token):
    """Decode a single token like 'U0', 'L4', 'F27'."""
    if not token:
        return ""
    code = token[0].upper()
    try:
        idx = int(token[1:])
    except ValueError:
        return token  # malformed token, return as-is
    mapping = {"U": UPPER, "L": LOWER, "D": DIGITS, "F": FIGURES}
    seq = mapping.get(code)
    if seq is None or idx >= len(seq):
        return token
    return seq[idx]


def Franckate(text: str) -> str:
    """Encrypt text using the Franckate cipher."""
    result = []
    for ch in text:
        code, idx = _encode_char(ch)
        if code is not None:
            result.append(f"{code}{idx}.")
        else:
            result.append(f"{ch}.")  # unknown chars passed through with delimiter
    return "".join(result)


def Defranckate(text: str) -> str:
    """Decrypt Franckate ciphertext back to plaintext."""
    decrypted = []
    token = ""
    for ch in text:
        if ch != ".":
            token += ch
        else:
            decrypted.append(_decode_token(token))
            token = ""
    # Handle any trailing content without a final dot
    if token:
        decrypted.append(_decode_token(token))
    return "".join(decrypted)


def FranckateSteps(text: str) -> list:
    """Return step-by-step encryption breakdown for educational use."""
    steps = []
    running = ""
    for i, ch in enumerate(text):
        code, idx = _encode_char(ch)
        if code is not None:
            token = f"{code}{idx}."
            category_names = {
                "U": "uppercase",
                "L": "lowercase",
                "D": "digit",
                "F": "special/space",
            }
            running += token
            steps.append({
                "position": i,
                "character": ch,
                "category": category_names[code],
                "category_code": code,
                "index_in_category": idx,
                "token": token,
                "running_output": running,
                "explanation": (
                    f"'{ch}' is a {category_names[code]} character at index {idx} "
                    f"in its category → encoded as '{token}'"
                ),
            })
        else:
            token = f"{ch}."
            running += token
            steps.append({
                "position": i,
                "character": ch,
                "category": "unknown",
                "category_code": None,
                "index_in_category": None,
                "token": token,
                "running_output": running,
                "explanation": f"'{ch}' is not in any category — passed through as '{token}'",
            })
    return steps


def DefranckateSteps(text: str) -> list:
    """Return step-by-step decryption breakdown for educational use."""
    steps = []
    token = ""
    position = 0
    char_idx = 0
    category_names = {
        "U": "uppercase",
        "L": "lowercase",
        "D": "digit",
        "F": "special/space",
    }
    for ch in text:
        if ch != ".":
            token += ch
        else:
            decoded = _decode_token(token)
            code = token[0].upper() if token else "?"
            category = category_names.get(code, "unknown")
            steps.append({
                "position": char_idx,
                "token": token + ".",
                "category_code": code if code in category_names else None,
                "category": category,
                "decoded_character": decoded,
                "explanation": (
                    f"Token '{token}.' → category '{code}' index {token[1:]} → '{decoded}'"
                    if code in category_names
                    else f"Token '{token}.' → passed through as '{decoded}'"
                ),
            })
            char_idx += 1
            token = ""
    if token:
        decoded = _decode_token(token)
        steps.append({
            "position": char_idx,
            "token": token,
            "category_code": None,
            "category": "unknown",
            "decoded_character": decoded,
            "explanation": f"Trailing token '{token}' → '{decoded}'",
        })
    return steps


def analyze_text(text: str) -> dict:
    """Return character category distribution of a plaintext string."""
    counts = {"uppercase": 0, "lowercase": 0, "digits": 0, "special": 0, "unknown": 0}
    char_details = []
    for ch in text:
        for seq, label in [
            (UPPER, "uppercase"),
            (LOWER, "lowercase"),
            (DIGITS, "digits"),
            (FIGURES, "special"),
        ]:
            if ch in seq:
                counts[label] += 1
                char_details.append({"char": ch, "category": label})
                break
        else:
            counts["unknown"] += 1
            char_details.append({"char": ch, "category": "unknown"})

    total = len(text)
    percentages = {
        k: round(v / total * 100, 1) if total else 0 for k, v in counts.items()
    }
    return {
        "length": total,
        "counts": counts,
        "percentages": percentages,
        "unique_characters": len(set(text)),
        "categories": {
            "uppercase": f"{counts['uppercase']} chars → {counts['uppercase']} tokens (U0.–U25.)",
            "lowercase": f"{counts['lowercase']} chars → {counts['lowercase']} tokens (L0.–L25.)",
            "digits": f"{counts['digits']} chars → {counts['digits']} tokens (D0.–D9.)",
            "special": f"{counts['special']} chars → {counts['special']} tokens (F0.–F27.)",
        },
    }
