from __future__ import annotations

import io
import logging
import uuid
from abc import abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modeltrans.fields import TranslationField
from wagtail.search import index

import willow  # type: ignore
from image_cropping import ImageRatioField

from users.models import User

if TYPE_CHECKING:
    from django.http import HttpRequest

    from kausal_common.models.types import FK, OneToOne
    from kausal_common.users import UserOrAnon

    from orgs.models import Organization

logger = logging.getLogger(__name__)

DEFAULT_AVATAR_SIZE = 360


def image_upload_path(instance: BasePerson, filename: str) -> str:
    f_path = Path(filename)
    file_extension = f_path.suffix
    return 'images/%s/%s%s' % (instance._meta.model_name, instance.pk, file_extension)


class BasePerson(index.Indexed, ClusterableModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    first_name = models.CharField(max_length=100, verbose_name=_('first name'))
    last_name = models.CharField(max_length=100, verbose_name=_('last name'))
    email = models.EmailField(verbose_name=_('email address'))
    title = models.CharField(
        max_length=100, null=True, blank=True,
        verbose_name=pgettext_lazy("person's role", 'title'),
    )
    postal_address = models.TextField(max_length=100, verbose_name=_('postal address'), null=True, blank=True)
    organization: FK[Organization] = models.ForeignKey(
        'orgs.Organization', related_name='people', on_delete=models.CASCADE, verbose_name=_('organization'),
        help_text=_("What is this person's organization"),
    )
    user: OneToOne[User | None] = models.OneToOneField(
        User, null=True, blank=True, related_name='person', on_delete=models.SET_NULL,
        editable=False, verbose_name=_('user'),
        help_text=_('Set if the person has an user account'),
    )

    image = models.ImageField(
        blank=True, upload_to=image_upload_path, verbose_name=_('image'),
        height_field='image_height', width_field='image_width',
    )
    image_cropping = ImageRatioField('image', '1280x720', verbose_name=_('image cropping'))  # pyright: ignore
    image_height = models.PositiveIntegerField(null=True, editable=False)
    image_width = models.PositiveIntegerField(null=True, editable=False)
    avatar_updated_at = models.DateTimeField(null=True, editable=False)

    created_by: FK[User | None] = models.ForeignKey(
        User, related_name='created_persons', blank=True, null=True, on_delete=models.SET_NULL,
        verbose_name=_('created by'),
    )
    i18n = TranslationField(fields=('title',), default_language_field='organization__primary_language_lowercase')

    # objects: ClassVar[PersonManager] = PersonManager()  # pyright: ignore

    search_fields = [
        index.FilterField('id'),
        index.AutocompleteField('first_name'),
        index.AutocompleteField('last_name'),
        index.AutocompleteField('title'),
        index.RelatedFields('organization', [
            index.AutocompleteField('distinct_name'),
            index.AutocompleteField('abbreviation'),
        ]),
    ]

    public_fields = [
        'id', 'uuid', 'first_name', 'last_name', 'email', 'title', 'organization',
    ]

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('people')
        ordering = ('last_name', 'first_name')
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # FIXME: This is hacky
        field: ImageRatioField = self._meta.get_field('image_cropping')  # type: ignore
        field.width = DEFAULT_AVATAR_SIZE
        field.height = DEFAULT_AVATAR_SIZE

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude)

        qs = self.__class__.objects.all()

        if self.email:
            qs = qs.filter(email__iexact=self.email)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({
                'email': _('Person with this email already exists'),
            })

    def set_avatar(self, photo):
        update_fields = ['avatar_updated_at']
        try:
            if not self.image or self.image.read() != photo:
                self.image.save('avatar.jpg', io.BytesIO(photo))  # type: ignore
                update_fields += ['image', 'image_height', 'image_width', 'image_cropping']
        except ValueError:
            pass
        self.avatar_updated_at = timezone.now()
        self.save(update_fields=update_fields)

    @abstractmethod
    def download_avatar(self):
        raise NotImplementedError('This method should be implemented by subclasses')

    def should_update_avatar(self):
        if not self.avatar_updated_at:
            return True
        return (timezone.now() - self.avatar_updated_at) > timedelta(minutes=60)

    def update_focal_point(self):
        if not self.image:
            return
        with self.image.open() as f:
            image = willow.Image.open(f)
            faces = image.detect_faces()

        if not faces:
            logger.warning('No faces detected for %s' % self)
            return

        left = min(face[0] for face in faces)
        top = min(face[1] for face in faces)
        right = max(face[2] for face in faces)
        bottom = max(face[3] for face in faces)
        self.image_cropping = ','.join([str(x) for x in (left, top, right, bottom)])

    @abstractmethod
    def get_avatar_url(self, request: HttpRequest, size: str | None = None) -> str | None:
        raise NotImplementedError('This method should be implemented by subclasses')

    def save(self, *args, **kwargs):
        old_cropping = self.image_cropping
        ret = super().save(*args, **kwargs)
        if self.image and not old_cropping:
            self.update_focal_point()
            if self.image_cropping != old_cropping:
                super().save(update_fields=['image_cropping'])
        user = self.create_corresponding_user()
        if self.user != user:
            if self.user:
                # Deactivate `self.user` as we'll replace it with `user`
                # FIXME: We don't have access to any user to set as the deactivating user. There might not be a
                # deactivating user at all because we're not in a view. Setting `User.deactivated_by` to None may cause
                # problems.
                deactivating_user = None
                self.user.deactivate(deactivating_user)
            self.user = user
            super().save(update_fields=['user'])

        return ret


    def get_corresponding_user(self):
        if self.user:
            return self.user

        return User.objects.filter(email__iexact=self.email).first()

    @abstractmethod
    def create_corresponding_user(self):
        raise NotImplementedError('This method should be implemented by subclasses')


    def delete_and_deactivate_corresponding_user(self, acting_admin_user):
        target_user = getattr(self, 'user', None)
        if target_user:
            target_user.deactivate(acting_admin_user)
        self.delete()

    @abstractmethod
    def visible_for_user(self, user: UserOrAnon, **kwargs) -> bool:
        """
        Determine if this person is visible to the given user.

        Args:
            user: The user requesting access
            **kwargs: Additional context (e.g., plan, organization, etc.)

        Returns:
            bool: True if visible, False otherwise
        """
        raise NotImplementedError("This method should be implemented by subclasses")


class ObjectRole(models.TextChoices):
    VIEWER = 'viewer'
    EDITOR = 'editor'
    ADMIN = 'admin'


# Workaround for https://code.djangoproject.com/ticket/33174
# Once this has been fixed in Django, we can probably use the code in the `if` branch below unconditionally and
# merge _ObjectRoleBase into ObjectRoleBase.
class _ObjectRoleBase(models.Model):
    role = models.CharField(choices=ObjectRole.choices)

    class Meta:
        abstract = True

if TYPE_CHECKING:
    class ObjectRoleBase[M: models.Model](_ObjectRoleBase):  # noqa: DJ008
        object: FK[M]
else:
    ObjectRoleBase = _ObjectRoleBase


if TYPE_CHECKING:
    class ObjectGroupPermissionBase[M: models.Model](ObjectRoleBase[M]):
        group = models.ForeignKey('people.PersonGroup', on_delete=models.CASCADE)

        object: FK[M]
        objects: models.Manager[f'{M.__name__}GroupPermission']  # pyright: ignore

        class Meta:  # pyright: ignore
            abstract = True
else:
    class ObjectGroupPermissionBase(ObjectRoleBase):
        group = models.ForeignKey('people.PersonGroup', on_delete=models.CASCADE)

        class Meta:  # pyright: ignore
            abstract = True


if TYPE_CHECKING:
    class ObjectPersonPermissionBase[M: models.Model](ObjectRoleBase[M]):
        person = models.ForeignKey('people.Person', on_delete=models.CASCADE)

        object: FK[M]
        objects: models.Manager[f'{M.__name__}PersonPermission']  # pyright: ignore

        class Meta:  # pyright: ignore
            abstract = True
else:
    class ObjectPersonPermissionBase(ObjectRoleBase):
        person = models.ForeignKey('people.Person', on_delete=models.CASCADE)

        class Meta:  # pyright: ignore
            abstract = True


def create_permission_membership_models[M: models.Model](
    model: type[M]
) -> tuple[type[ObjectGroupPermissionBase[M]], type[ObjectPersonPermissionBase[M]]]:
    GroupPermissionMeta = type('Meta', (),{  # noqa: N806
        'unique_together': (('group', 'object'),),
    })
    GroupPermission = type(  # noqa: N806
        '%sGroupPermission' % model.__name__,
        (ObjectGroupPermissionBase,),
        {
            '__module__': 'people.models',
            'object': ParentalKey(model, on_delete=models.CASCADE, related_name='group_permissions'),
            'Meta': GroupPermissionMeta,
        },
    )
    PersonPermissionMeta = type('Meta', (),{  # noqa: N806
        'unique_together': (('person', 'object'),),
    })
    PersonPermission = type(  # noqa: N806
        '%sPersonPermission' % model.__name__,
        (ObjectPersonPermissionBase,),
        {
            '__module__': 'people.models',
            'object': ParentalKey(model, on_delete=models.CASCADE, related_name='person_permissions'),
            'Meta': PersonPermissionMeta,
        },
    )
    return GroupPermission, PersonPermission
