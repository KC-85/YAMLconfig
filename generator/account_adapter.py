from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def get_password_change_redirect_url(self, request) -> str:
        return reverse("generator:project_list")
