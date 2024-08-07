from django.db.models import Manager, Model, QuerySet

class MultilingualQuerySet[M: Model](QuerySet[M]): ...
class MultilingualManager[M: Model](Manager[M]): ...
