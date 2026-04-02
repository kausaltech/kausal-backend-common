from django.forms import MediaDefiningClass
from django.utils.functional import cached_property as cached_property

from _typeshed import Incomplete

DICT_RESERVED_KEYS: Incomplete
STRING_REF_MIN_LENGTH: int

class UnpackableTypeError(TypeError): ...

class Node:
    """
    Intermediate representation of a packed value. Subclasses represent a particular value
    type, and implement emit_verbose (returns a dict representation of a value that can have
    an _id attached) and emit_compact (returns a compact representation of the value, in any
    JSON-serialisable type).

    If this node is assigned an id, emit() will return the verbose representation with the
    id attached on first call, and a reference on subsequent calls. To disable this behaviour
    (e.g. for small primitive values where the reference representation adds unwanted overhead),
    set self.use_id = False.
    """
    id: Incomplete
    seen: bool
    use_id: bool
    def __init__(self) -> None: ...
    def emit(self): ...

class ValueNode(Node):
    """Represents a primitive value; int, bool etc"""
    value: Incomplete
    use_id: bool
    def __init__(self, value) -> None: ...
    def emit_verbose(self): ...
    def emit_compact(self): ...

class StringNode(Node):
    value: Incomplete
    use_id: Incomplete
    def __init__(self, value) -> None: ...
    def emit_verbose(self): ...
    def emit_compact(self): ...

class ListNode(Node):
    value: Incomplete
    def __init__(self, value) -> None: ...
    def emit_verbose(self): ...
    def emit_compact(self): ...

class DictNode(Node):
    value: Incomplete
    def __init__(self, value) -> None: ...
    def emit_verbose(self): ...
    def emit_compact(self): ...

class ObjectNode(Node):
    constructor: Incomplete
    args: Incomplete
    def __init__(self, constructor, args) -> None: ...
    def emit_verbose(self): ...
    def emit_compact(self): ...

class BaseAdapter:
    """Handles serialisation of a specific object type"""
    def build_node(self, obj, context):
        """
        Translates obj into a node that we can call emit() on to obtain the final serialisable
        form. Any media declarations that will be required for deserialisation of the object should
        be passed to context.add_media().

        This base implementation handles simple JSON-serialisable values such as integers, and
        wraps them as a ValueNode.
        """

class StringAdapter(BaseAdapter):
    def build_node(self, obj, context): ...

class DictAdapter(BaseAdapter):
    """Handles serialisation of dicts"""
    def build_node(self, obj, context): ...

class Adapter(BaseAdapter, metaclass=MediaDefiningClass):
    """
    Handles serialisation of custom types.
    Subclasses should define:
    - js_constructor: namespaced identifier for the JS constructor function that will unpack this
        object
    - js_args(obj): returns a list of (telepath-packable) arguments to be passed to the constructor
    - get_media(obj) or class Media: media definitions necessary for unpacking

    The adapter should then be registered with register(adapter, cls).
    """
    def get_media(self, obj): ...
    def pack(self, obj, context): ...
    def build_node(self, obj, context): ...

class AutoAdapter(Adapter):
    """
    Adapter for objects that define their own telepath_pack method that we can simply delegate to.
    """
    def pack(self, obj, context): ...

class JSContextBase:
    """
    Base class for JSContext classes obtained through AdapterRegistry.js_context_class.
    Subclasses of this are assigned the following class attributes:
    registry - points to the associated AdapterRegistry
    telepath_js_path - path to telepath.js (as per standard Django staticfiles conventions)

    A JSContext handles packing a set of values to be used in the same request; calls to
    JSContext.pack will return the packed representation and also update the JSContext's media
    property to include all JS needed to unpack the values seen so far.
    """
    media: Incomplete
    media_fragments: Incomplete
    def __init__(self) -> None: ...
    @property
    def base_media(self): ...
    def add_media(self, media=None, js=None, css=None) -> None: ...
    def pack(self, obj): ...

class AdapterRegistry:
    """
    Manages the mapping of Python types to their corresponding adapter implementations.
    """
    js_context_base_class = JSContextBase
    telepath_js_path: Incomplete
    adapters: Incomplete
    def __init__(self, telepath_js_path: str = 'telepath/js/telepath.js') -> None: ...
    def register(self, *args, **kwargs): ...
    def find_adapter(self, cls): ...
    @cached_property
    def js_context_class(self): ...

class ValueContext:
    """
    A context instantiated for each top-level value that JSContext.pack is called on. Results from
    this context's build_node method will be kept in a lookup table. If, over the course of
    building the node tree for the top level value, we encounter multiple references to the same
    value, a reference to the existing node will be generated rather than building it again. Calls
    to add_media are passed back to the parent context so that multiple calls to pack() will have
    their media combined in a single bundle.
    """
    parent_context: Incomplete
    registry: Incomplete
    raw_values: Incomplete
    nodes: Incomplete
    next_id: int
    def __init__(self, parent_context) -> None: ...
    def add_media(self, *args, **kwargs) -> None: ...
    def build_node(self, val): ...

registry: Incomplete
JSContext: Incomplete
register: Incomplete
