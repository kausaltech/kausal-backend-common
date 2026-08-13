from __future__ import annotations

from typing import override

from social_core.backends.azuread_tenant import AzureADTenantOAuth2


class AzureADAuth(AzureADTenantOAuth2):
    name = 'azure_ad'
    DEFAULT_SCOPE = ['openid', 'profile', 'email', 'User.Read']

    @property
    @override
    def tenant_id(self) -> str:
        return 'organizations'

    @override
    def openid_configuration_url(self) -> str:
        if self.tenant_id != 'organizations':
            return super().openid_configuration_url()

        # Microsoft does not publish v1 OpenID metadata for the
        # ``organizations`` pseudo-tenant. The v1 ``common`` metadata uses the
        # same signing keys and contains a tenant-specific issuer template.
        metadata_base_url = self.BASE_URL.format(authority_host=self.authority_host, tenant_id='common')
        return self.OPENID_CONFIGURATION_URL.format(base_url=metadata_base_url, appid=self._appid())

    @override
    def auth_complete_params(self, state=None):
        params = super().auth_complete_params(state)
        params['resource'] = 'https://graph.microsoft.com/'
        return params

    @override
    def get_user_id(self, details, response):
        """Use the stable object ID claim as the unique user ID."""
        oid = response['oid']
        response['sub'] = oid
        return oid

    @override
    def get_user_details(self, response):
        details = super().get_user_details(response)
        details['uuid'] = response.get('oid')
        return details

    @override
    def auth_extra_arguments(self):
        extra_arguments = super().auth_extra_arguments()
        email = self.strategy.request_data().get('email')
        if email:
            extra_arguments['login_hint'] = email
        return extra_arguments
