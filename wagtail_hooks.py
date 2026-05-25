from django.templatetags.static import static
from django.utils.safestring import mark_safe
from wagtail import hooks

from kausal_common.blocks.conditional_struct_block import get_conditional_rules_config


@hooks.register('insert_editor_js')
def conditional_struct_block_editor_js():
    rules_json = get_conditional_rules_config()
    # rules_json comes from json.dumps of Python class definitions (not user input),
    # so marking it safe for embedding in a <script> block is appropriate here.
    js_url = static('kausal_common/js/conditional_struct_block.js')
    return mark_safe(
        f'<script>window.KAUSAL_CONDITIONAL_RULES={rules_json};</script>'
        f'<script src="{js_url}"></script>'
    )
