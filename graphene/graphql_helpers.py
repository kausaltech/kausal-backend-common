from __future__ import annotations

import typing
from typing import Self

import graphene
from graphene_django.forms.mutation import DjangoModelFormMutation

if typing.TYPE_CHECKING:
    from django.db.models import Model


class AuthenticatedUserNode(graphene.ObjectType):
    pass


class CreateModelInstanceMutation(DjangoModelFormMutation, AuthenticatedUserNode):
    # Provide form_class in Meta class of subclass
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, *args, **kwargs) -> None:
        # Exclude `id`, otherwise we could change an existing instance by specifying an ID
        kwargs['exclude_fields'] = ['id']
        super().__init_subclass_with_meta__(*args, **kwargs)


class UpdateModelInstanceMutation(DjangoModelFormMutation, AuthenticatedUserNode):
    # Provide form_class in Meta class of subclasses
    class Meta:
        abstract = True

    @classmethod
    def perform_mutate(cls, form, info) -> Self:
        # Require id in `input` argument, otherwise we could create instances with this mutation
        if form.instance.id is None:
            raise ValueError("ID not specified")
        return super().perform_mutate(form, info)


class DeleteModelInstanceMutation(graphene.Mutation, AuthenticatedUserNode):
    class Arguments:
        id = graphene.ID()

    model: type[Model]
    ok = graphene.Boolean()

    @classmethod
    def __init_subclass_with_meta__(cls, *args, **kwargs) -> None:
        cls.model = kwargs.pop('model')
        super().__init_subclass_with_meta__(*args, **kwargs)

    @classmethod
    def mutate(cls, root, info, id: str) -> Self:  # noqa: ARG003
        obj = cls.model._default_manager.get(pk=id)
        obj.delete()
        return cls(ok=True)
