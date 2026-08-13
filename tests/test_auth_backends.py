from unittest.mock import Mock

import pytest

from kausal_common.auth.backends import AzureADAuth

pytestmark = pytest.mark.django_db


def get_social_auth_strategy(settings_by_name: dict[str, str], request_data: dict[str, str] | None = None) -> Mock:
    def get_setting(name, default=None, **_kwargs):
        return settings_by_name.get(name, default)

    strategy = Mock()
    strategy.request_data.return_value = request_data or {}
    strategy.absolute_uri.side_effect = lambda uri: uri
    strategy.setting.side_effect = get_setting
    return strategy


def test_azure_ad_uses_common_openid_metadata_for_organizations():
    backend = AzureADAuth(get_social_auth_strategy({'KEY': 'client-id'}))

    assert backend.base_url == 'https://login.microsoftonline.com/organizations'
    assert backend.openid_configuration_url() == (
        'https://login.microsoftonline.com/common/.well-known/openid-configuration?appid=client-id'
    )


def test_azure_ad_forwards_email_as_login_hint():
    backend = AzureADAuth(get_social_auth_strategy({}, {'email': 'user@example.com'}))

    assert backend.auth_extra_arguments()['login_hint'] == 'user@example.com'


def test_azure_ad_uses_object_id_as_user_id():
    backend = AzureADAuth(get_social_auth_strategy({}))
    response = {'oid': 'object-id', 'sub': 'pairwise-id'}

    assert backend.get_user_id({}, response) == 'object-id'
    assert response['sub'] == 'object-id'
