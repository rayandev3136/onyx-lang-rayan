# suggestions.py
# Smart suggestions using Levenshtein distance


def levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, c1 in enumerate(a):
        curr = [i + 1]
        for j, c2 in enumerate(b):
            insert = prev[j + 1] + 1
            delete = curr[j] + 1
            subst = prev[j] + (0 if c1 == c2 else 1)
            curr.append(min(insert, delete, subst))
        prev = curr
    return prev[-1]


def find_similar(name, candidates, max_distance=2, max_results=3):
    if not name or not candidates:
        return []
    scored = []
    for c in candidates:
        if c == name:
            continue
        d = levenshtein(name.lower(), c.lower())
        if 0 < d <= max_distance:
            scored.append((d, c))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [c for _, c in scored[:max_results]]


KEYWORDS = [
    "set", "const", "if", "else", "while", "for", "in",
    "break", "continue", "fn", "return", "true", "false",
    "None", "and", "or", "not", "use", "match",
]


def suggest_keyword(name):
    return find_similar(name, KEYWORDS, max_distance=2)


def format_suggestion(items, prefix="Did you mean"):
    if not items:
        return ""
    quoted = ", ".join("'" + x + "'" for x in items)
    return " -- " + prefix + ": " + quoted + "?"