
from kausal_common.graphene import DjangoNode


class PersonNode(DjangoNode):

    class Meta:
        abstract = True
