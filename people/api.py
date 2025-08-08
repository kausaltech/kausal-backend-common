from collections import Counter

from rest_framework import exceptions, serializers

from kausal_common.api.bulk import BulkListSerializer, BulkSerializerValidationInstanceMixin
from kausal_common.model_images import ModelWithImageSerializerMixin
from kausal_common.models.general import public_fields

from people.models import Person

from django.utils.translation import gettext_lazy as _


class PersonSerializer(
    BulkSerializerValidationInstanceMixin,
    serializers.ModelSerializer,
    ModelWithImageSerializerMixin,
):
    uuid = serializers.UUIDField(required=False)
    avatar_url = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('authorized_for_instance') is None:
            self.fields.pop('email')

    def get_avatar_url(self, obj: Person) -> str | None:
        return obj.get_avatar_url(self.context['request'])

    def validate_email(self, value):
        qs = Person.objects.filter(email__iexact=value)
        if self._instance is not None:
            qs = qs.exclude(pk=self._instance.pk)
        if qs.exists():
            raise serializers.ValidationError(_('Person with this email already exists'))
        return value

    def validate(self, data):
        for d in self.initial_data:
            if 'email' not in d:
                raise exceptions.ValidationError(_("Not all objects have an email address"))
        emails = Counter(data['email'] for data in self.initial_data)
        duplicates = [email for email, n in emails.most_common() if n > 1]
        if duplicates:
            # TODO: This should better be in validate_email to highlight the faulty table cells
            raise exceptions.ValidationError(_("Duplicate email addresses: %s") % ', '.join(duplicates))
        return data

    class Meta:
        model = Person
        list_serializer_class = BulkListSerializer
        fields = public_fields(Person, add_fields=['avatar_url'])
