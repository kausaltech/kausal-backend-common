from __future__ import annotations

import re


def camelcase_to_underscore(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def underscore_to_camelcase(value: str) -> str:
    output = ""
    for word in value.split("_"):
        if not word:
            output += "_"
            continue
        output += word.capitalize()
    return output

