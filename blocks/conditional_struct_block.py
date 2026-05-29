from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import ClassVar

from wagtail import blocks


@dataclass
class ConditionalFieldRule:
    trigger: str
    target: str
    show_for: list[str] = field(default_factory=list)
    target_path: list[str] = field(default_factory=list)


_REGISTRY: list[type[ConditionalStructBlock]] = []


class ConditionalStructBlock(blocks.StructBlock):
    """
    StructBlock subclass with declarative conditional field visibility in the Wagtail admin.

    Subclasses declare `conditional_rules` at class level. A generic JS utility reads
    the rules config injected by the Wagtail hook in kausal_common.wagtail_hooks and
    applies show/hide logic via data-contentpath selectors.
    """

    conditional_rules: ClassVar[list[ConditionalFieldRule]] = []

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.conditional_rules:
            _REGISTRY.append(cls)


def get_conditional_rules_config() -> str:
    """
    Return a JSON string mapping block fingerprints to their rule lists.

    The fingerprint is the sorted JSON of declared field names, which uniquely
    identifies a block type in practice. The JS side computes the same fingerprint
    from the direct data-contentpath children of each .struct-block element.
    """
    config: dict[str, list[dict[str, object]]] = {}
    for cls in _REGISTRY:
        fingerprint = json.dumps(sorted(cls.declared_blocks.keys()), separators=(',', ':'))
        config[fingerprint] = [
            {
                'trigger': r.trigger,
                'target': r.target,
                'showFor': r.show_for,
                **(({'targetPath': r.target_path}) if r.target_path else {}),
            }
            for r in cls.conditional_rules
        ]
    return json.dumps(config, separators=(',', ':'))
