import re

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountWorkflowTests(TestCase):
    password = "CorrectHorseBatteryStaple!42"

    def create_verified_user(
        self,
        *,
        username: str = "account-user",
        email: str = "account@example.com",
    ):
        user = get_user_model().objects.create_user(
            username=username,
            email=email,
            password=self.password,
        )
        EmailAddress.objects.create(
            user=user,
            email=email,
            verified=True,
            primary=True,
        )
        return user

    def test_account_pages_use_project_templates(self):
        expected_content = {
            "account_login": "Sign in",
            "account_signup": "Create your account",
            "account_reset_password": "Reset password",
        }

        for url_name, expected_text in expected_content.items():
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)
                self.assertContains(response, "YAMLconfig")

    def test_authenticated_account_management_pages_render(self):
        user = self.create_verified_user()
        self.client.force_login(user)
        expected_content = {
            "account_email": "Email addresses",
            "account_change_password": "Change password",
            "account_logout": "Are you sure you want to sign out?",
        }

        for url_name, expected_text in expected_content.items():
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)

    def test_signup_requires_email_confirmation_and_confirmation_logs_in(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "new-user",
                "email": "new@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )

        self.assertRedirects(
            response,
            reverse("account_email_verification_sent"),
        )
        user = get_user_model().objects.get(username="new-user")
        email_address = EmailAddress.objects.get(user=user)
        self.assertFalse(email_address.verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("_auth_user_id", self.client.session)

        confirmation = EmailConfirmationHMAC(email_address)
        confirmation_url = reverse(
            "account_confirm_email",
            args=[confirmation.key],
        )
        confirmation_page = self.client.get(confirmation_url)
        self.assertContains(confirmation_page, "Confirm email address")

        response = self.client.post(confirmation_url)

        self.assertRedirects(response, reverse("generator:project_list"))
        email_address.refresh_from_db()
        self.assertTrue(email_address.verified)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_verified_user_can_login_with_email_and_logout_by_post(self):
        user = self.create_verified_user()

        response = self.client.post(
            reverse("account_login"),
            {
                "login": user.email,
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("generator:project_list"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

        response = self.client.post(reverse("account_logout"))

        self.assertRedirects(response, reverse("account_login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unverified_user_cannot_complete_login(self):
        user = get_user_model().objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password=self.password,
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=False,
            primary=True,
        )

        response = self.client.post(
            reverse("account_login"),
            {
                "login": user.email,
                "password": self.password,
            },
        )

        self.assertRedirects(
            response,
            reverse("account_email_verification_sent"),
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_can_change_password(self):
        user = self.create_verified_user()
        self.client.force_login(user)
        new_password = "AnEvenBetterPassword!43"

        response = self.client.post(
            reverse("account_change_password"),
            {
                "oldpassword": self.password,
                "password1": new_password,
                "password2": new_password,
            },
        )

        self.assertRedirects(response, reverse("generator:project_list"))
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))

    def test_password_reset_email_link_changes_password(self):
        user = self.create_verified_user()
        new_password = "ResetPasswordWorks!44"

        response = self.client.post(
            reverse("account_reset_password"),
            {"email": user.email},
        )

        self.assertRedirects(response, reverse("account_reset_password_done"))
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(
            r"https?://testserver(?P<path>/accounts/password/reset/key/[^\s]+)",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)

        token_response = self.client.get(match.group("path"))
        self.assertEqual(token_response.status_code, 302)
        safe_reset_url = token_response["Location"]

        response = self.client.post(
            safe_reset_url,
            {
                "password1": new_password,
                "password2": new_password,
            },
        )

        self.assertRedirects(
            response,
            reverse("account_reset_password_from_key_done"),
        )
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
