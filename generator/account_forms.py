from typing import Any

from allauth.account.forms import (
    AddEmailForm as AllauthAddEmailForm,
    ChangePasswordForm as AllauthChangePasswordForm,
    LoginForm as AllauthLoginForm,
    ResetPasswordForm as AllauthResetPasswordForm,
    ResetPasswordKeyForm as AllauthResetPasswordKeyForm,
    SetPasswordForm as AllauthSetPasswordForm,
    SignupForm as AllauthSignupForm,
)
from django import forms


class StyledAccountFormMixin:
    """Apply the dashboard's input styling to allauth's maintained forms."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                classes = "h-4 w-4 rounded border-slate-300 text-cyan-600"
            else:
                classes = (
                    "w-full rounded-md border border-slate-300 px-3 py-2 "
                    "text-sm text-slate-900 focus:border-cyan-500 focus:outline-none"
                )
                field.widget.attrs.setdefault("placeholder", field.label)
            field.widget.attrs["class"] = f"{existing_classes} {classes}".strip()


class LoginForm(StyledAccountFormMixin, AllauthLoginForm):
    pass


class SignupForm(StyledAccountFormMixin, AllauthSignupForm):
    pass


class AddEmailForm(StyledAccountFormMixin, AllauthAddEmailForm):
    pass


class ChangePasswordForm(StyledAccountFormMixin, AllauthChangePasswordForm):
    pass


class SetPasswordForm(StyledAccountFormMixin, AllauthSetPasswordForm):
    pass


class ResetPasswordForm(StyledAccountFormMixin, AllauthResetPasswordForm):
    pass


class ResetPasswordKeyForm(StyledAccountFormMixin, AllauthResetPasswordKeyForm):
    pass
