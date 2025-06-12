from __future__ import annotations

from itertools import groupby

from django import forms
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.formsets import BaseFormSetMixin

from .choosers import DatasetChooser
from .models import DATASET_PERMISSION_CODENAMES, DATASET_PERMISSION_TYPES, Dataset, GroupDatasetPermission


class DatasetPermissionsForm(forms.Form):
    """
    Form for the permissions for a dataset.

    Note 'Permissions' (plural). A single instance of this form defines the permissions
    that are assigned to an entity (i.e. group or user) for a specific dataset.

    Copied from Wagtail's PagePermissionsForm.
    """

    dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.all(),
        widget=DatasetChooser(),
    )
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            codename__in=DATASET_PERMISSION_CODENAMES,
        )
        .select_related('content_type')
        .order_by('codename'),
        # Use codename as the field to use for the option values rather than pk,
        # to minimise the changes needed since we moved to the Permission model
        # and to ease testing.
        # Django advises `to_field_name` to be a unique field. While `codename`
        # is not unique by itself, it is unique together with `content_type`, so
        # it is unique in the context of the above queryset.
        to_field_name='codename',
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class BaseGroupDatasetPermissionFormSet(BaseFormSetMixin, forms.BaseFormSet):
    """
    Formset for the GroupDatasetPermission model.

    Copied from Wagtail's BaseGroupPagePermissionFormSet.
    """

    # defined here for easy access from templates
    permission_types = DATASET_PERMISSION_TYPES

    def __init__(self, data=None, files=None, instance=None, prefix='dataset_permissions'):
        if instance is None:
            instance = Group()

        if instance.pk is None:
            full_dataset_permissions = []
        else:
            full_dataset_permissions = instance.dataset_permissions.select_related(
                'dataset', 'permission'
            ).order_by('dataset')

        self.instance = instance

        initial_data = []

        for dataset, dataset_permissions in groupby(
            full_dataset_permissions,
            lambda dsp: dsp.dataset,
        ):
            initial_data.append(
                {
                    'dataset': dataset,
                    'permissions': [dsp.permission for dsp in dataset_permissions],
                }
            )

        super().__init__(data, files, initial=initial_data, prefix=prefix)

    def clean(self):
        """Check that no two forms refer to the same dataset object."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return

        datasets = [
            form.cleaned_data['dataset']
            for form in self.forms
            # need to check for presence of 'dataset' in cleaned_data,
            # because a completely blank form passes validation
            if form not in self.deleted_forms and 'dataset' in form.cleaned_data
        ]
        if len(set(datasets)) != len(datasets):
            # datasets list contains duplicates
            raise forms.ValidationError(
                _('You cannot have multiple permission records for the same dataset.')
            )

    @transaction.atomic
    def save(self):
        if self.instance.pk is None:
            raise Exception(
                'Cannot save a GroupDatasetPermissionFormSet for an unsaved group instance'
            )

        # get a set of (dataset, permission) tuples for all ticked permissions
        forms_to_save = [
            form
            for form in self.forms
            if form not in self.deleted_forms and 'dataset' in form.cleaned_data
        ]

        final_permission_records = set()
        for form in forms_to_save:
            for permission in form.cleaned_data['permissions']:
                final_permission_records.add((form.cleaned_data['dataset'], permission))

        # fetch the group's existing dataset permission records, and from that, build a list
        # of records to be created / deleted
        permission_ids_to_delete = []
        permission_records_to_keep = set()

        for dsp in self.instance.dataset_permissions.all():
            if (dsp.dataset, dsp.permission) in final_permission_records:
                permission_records_to_keep.add((dsp.dataset, dsp.permission))
            else:
                permission_ids_to_delete.append(dsp.pk)

        self.instance.dataset_permissions.filter(pk__in=permission_ids_to_delete).delete()

        permissions_to_add = final_permission_records - permission_records_to_keep
        GroupDatasetPermission.objects.bulk_create(
            [
                GroupDatasetPermission(
                    group=self.instance,
                    dataset=dataset,
                    permission=permission,
                )
                for (dataset, permission) in permissions_to_add
            ]
        )

    def as_admin_panel(self):
        return render_to_string(
            'datasets/groups/includes/dataset_permissions_formset.html',
            {'formset': self},
        )


GroupDatasetPermissionFormSet = forms.formset_factory(
    DatasetPermissionsForm,
    formset=BaseGroupDatasetPermissionFormSet,
    extra=0,
    can_delete=True,
)
