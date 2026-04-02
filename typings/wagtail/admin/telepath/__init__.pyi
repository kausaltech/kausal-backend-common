from _typeshed import Incomplete
from telepath import AdapterRegistry, JSContextBase

class WagtailJSContextBase(JSContextBase):
    @property
    def base_media(self): ...

class WagtailAdapterRegistry(AdapterRegistry):
    js_context_base_class = WagtailJSContextBase

registry: Incomplete
JSContext: Incomplete

def register(*args, **kwargs): ...
def adapter(js_constructor, base=...): ...
