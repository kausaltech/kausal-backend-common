from django.db.models import Model
from django.db.models.fields.related import ForeignKey, ManyToManyDescriptor, ManyToManyField

class ParentalKey[M: Model](ForeignKey[M, M]):  # pyright: ignore
    ...


class ParentalManyToManyField[M: Model, Through: Model](ManyToManyField[M, Through]):
    ...


class ParentalManyToManyDescriptor(ManyToManyDescriptor):
    ...
