from _typeshed import Incomplete

class BlockDefinitionLookup:
    '''
    A utility for constructing StreamField Block objects in migrations, starting from
    a compact representation that avoids repeating the same definition whenever a
    block is re-used in multiple places over the block definition tree.

    The underlying data is a dict of block definitions, such as:
    ```
    {
        0: ("wagtail.blocks.CharBlock", [], {"required": True}),
        1: ("wagtail.blocks.RichTextBlock", [], {}),
        2: ("wagtail.blocks.StreamBlock", [
            [
                ("heading", 0),
                ("paragraph", 1),
            ],
        ], {}),
    }
    ```

    where each definition is a tuple of (module_path, args, kwargs) similar to that
    returned by `deconstruct` - with the difference that any block objects appearing
    in args / kwargs may be substituted with an index into the lookup table that
    points to that block\'s definition. Any block class that wants to support such
    substitutions should implement a static/class method
    `construct_from_lookup(lookup, *args, **kwargs)`, where `lookup` is
    the `BlockDefinitionLookup` instance. The method should return a block instance
    constructed from the provided arguments (after performing any lookups).
    '''
    blocks: Incomplete
    block_classes: Incomplete
    def __init__(self, blocks) -> None: ...
    def get_block(self, index): ...

class BlockDefinitionLookupBuilder:
    """
    Helper for constructing the lookup data used by BlockDefinitionLookup
    """
    blocks: Incomplete
    block_indexes_by_type: Incomplete
    def __init__(self) -> None: ...
    def add_block(self, block):
        """
        Add a block to the lookup table, returning an index that can be used to refer to it
        """
    def get_lookup_as_dict(self): ...
