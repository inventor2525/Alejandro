from typing import Dict, List

# Define equivalent word groups
WORD_GROUPS = [
    ["0", "zero"],
    ["1", "one"],
    ["2", "two"],
    ["3", "three"],
    ["4", "four"],
    ["5", "five"],
    ["6", "six"],
    ["7", "seven"],
    ["8", "eight"],
    ["9", "nine"],
    ["10", "ten"]
]

# Build mapping where each word maps to all equivalent forms
WORD_MAP: Dict[str, List[str]] = {}
for group in WORD_GROUPS:
    for word in group:
        WORD_MAP[word] = [w for w in group if w != word]
        WORD_MAP[word].append(word)  # Include self in equivalents
