from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from django import forms
from wagtail import blocks
from wagtail.admin.telepath import register
from wagtail.blocks.struct_block import StructBlockAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence


class Match:
    """
    Describes which trigger field values cause a target to be shown.

    Each keyword argument maps a trigger field name to the values for
    which the target should be visible.
    """

    def __init__(self, **triggers: Sequence[str]) -> None:
        self.triggers = triggers


@dataclass
class ConditionalFieldVisibility:
    show: str | list[str]
    when: Match

    @property
    def target_path(self) -> list[str]:
        return [self.show] if isinstance(self.show, str) else list(self.show)

    @property
    def triggers(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.when.triggers.items()}


class ConditionalStructBlock(blocks.StructBlock):
    """
    StructBlock subclass with declarative conditional field visibility in the Wagtail admin.

    Subclasses declare ``conditional_rules`` at class level. The rules are passed
    to the client via a Telepath adapter, where a JS subclass of StructBlockDefinition
    annotates child elements with ``data-w-rules-*`` attributes so that Wagtail's
    built-in ``RulesController`` handles all show/hide logic.
    """

    conditional_rules: ClassVar[list[ConditionalFieldVisibility]] = []


class ConditionalStructBlockAdapter(StructBlockAdapter):
    js_constructor = 'kausal_common.blocks.ConditionalStructBlock'

    def js_args(self, block):
        args = super().js_args(block)
        if block.conditional_rules:
            meta = args[2]
            meta['conditionalRules'] = [
                {
                    'targetPath': r.target_path,
                    'triggers': r.triggers,
                }
                for r in block.conditional_rules
            ]
        return args

    @cached_property
    def media(self):
        return super().media + forms.Media(
            js=['kausal_common/js/conditional_struct_block.js'],
        )


register(ConditionalStructBlockAdapter(), ConditionalStructBlock)
