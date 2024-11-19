import graphene

class PydanticObjectType(graphene.ObjectType):
    @classmethod
    def resolve_placeholders(cls) -> None: ...
    @classmethod
    def is_type_of(cls, root, info) -> bool: ...
