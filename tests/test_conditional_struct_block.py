from __future__ import annotations

from wagtail import blocks

import pytest

from kausal_common.blocks.conditional_struct_block import (
    ConditionalFieldVisibility,
    ConditionalStructBlock,
    ConditionalStructBlockAdapter,
    Match,
)

pytestmark = pytest.mark.django_db


class MyConditionalBlock(ConditionalStructBlock):
    conditional_rules = [
        ConditionalFieldVisibility(show='details', when=Match(layout=('advanced',))),
    ]

    layout = blocks.ChoiceBlock(choices=[('simple', 'Simple'), ('advanced', 'Advanced')])
    title = blocks.CharBlock()
    details = blocks.CharBlock(required=False)


class MyBlockWithTargetPath(ConditionalStructBlock):
    conditional_rules = [
        ConditionalFieldVisibility(
            show=['settings', 'nested_field'],
            when=Match(layout=('fancy',)),
        ),
    ]

    layout = blocks.ChoiceBlock(choices=[('plain', 'Plain'), ('fancy', 'Fancy')])
    settings = blocks.StructBlock([('nested_field', blocks.CharBlock(required=False))])


class MyBlockWithMultipleTriggers(ConditionalStructBlock):
    conditional_rules = [
        ConditionalFieldVisibility(
            show='details',
            when=Match(layout=('advanced',), mode=('expert',)),
        ),
    ]

    layout = blocks.ChoiceBlock(choices=[('simple', 'Simple'), ('advanced', 'Advanced')])
    mode = blocks.ChoiceBlock(choices=[('normal', 'Normal'), ('expert', 'Expert')])
    title = blocks.CharBlock()
    details = blocks.CharBlock(required=False)


class MyPlainBlock(ConditionalStructBlock):
    """A ConditionalStructBlock with no rules defined."""

    title = blocks.CharBlock()
    body = blocks.CharBlock()


@pytest.fixture
def adapter():
    return ConditionalStructBlockAdapter()


class TestConditionalStructBlockAdapter:
    def test_js_constructor(self, adapter):
        assert adapter.js_constructor == 'kausal_common.blocks.ConditionalStructBlock'

    def test_media_includes_js(self, adapter):
        js_files = adapter.media._js
        assert any('conditional_struct_block.js' in path for path in js_files)

    def test_js_args_includes_rules_with_target_path_and_triggers(self, adapter):
        block = MyConditionalBlock()
        args = adapter.js_args(block)

        meta = args[2]
        assert 'conditionalRules' in meta

        rules = meta['conditionalRules']
        assert len(rules) == 1
        assert rules[0]['targetPath'] == ['details']
        assert rules[0]['triggers'] == {'layout': ['advanced']}

    def test_js_args_nested_target_path(self, adapter):
        block = MyBlockWithTargetPath()
        args = adapter.js_args(block)

        meta = args[2]
        rules = meta['conditionalRules']
        assert len(rules) == 1
        assert rules[0]['targetPath'] == ['settings', 'nested_field']
        assert rules[0]['triggers'] == {'layout': ['fancy']}

    def test_js_args_multiple_triggers(self, adapter):
        block = MyBlockWithMultipleTriggers()
        args = adapter.js_args(block)

        meta = args[2]
        rules = meta['conditionalRules']
        assert len(rules) == 1
        assert rules[0]['targetPath'] == ['details']
        assert rules[0]['triggers'] == {
            'layout': ['advanced'],
            'mode': ['expert'],
        }

    def test_js_args_omits_rules_when_none_defined(self, adapter):
        block = MyPlainBlock()
        args = adapter.js_args(block)

        meta = args[2]
        assert 'conditionalRules' not in meta


class TestMatch:
    def test_stores_triggers(self):
        m = Match(layout=('advanced',))
        assert m.triggers == {'layout': ('advanced',)}

    def test_multiple_triggers(self):
        m = Match(layout=('advanced',), mode=('expert',))
        assert m.triggers == {'layout': ('advanced',), 'mode': ('expert',)}


class TestConditionalFieldVisibility:
    def test_string_show_wraps_to_list(self):
        vis = ConditionalFieldVisibility(show='details', when=Match(layout=('advanced',)))
        assert vis.target_path == ['details']

    def test_list_show_preserves_path(self):
        vis = ConditionalFieldVisibility(
            show=['settings', 'nested_field'],
            when=Match(layout=('fancy',)),
        )
        assert vis.target_path == ['settings', 'nested_field']

    def test_triggers_converted_to_lists(self):
        vis = ConditionalFieldVisibility(
            show='details',
            when=Match(layout=('advanced',), mode=('expert',)),
        )
        assert vis.triggers == {
            'layout': ['advanced'],
            'mode': ['expert'],
        }
