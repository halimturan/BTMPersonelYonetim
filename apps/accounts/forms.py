from django.contrib.auth.forms import PasswordChangeForm


class UserPasswordChangeForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["old_password"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Mevcut parolanızı girin",
            "autocomplete": "current-password",
        })

        self.fields["new_password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Yeni parolanızı girin",
            "autocomplete": "new-password",
        })

        self.fields["new_password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Yeni parolanızı tekrar girin",
            "autocomplete": "new-password",
        })
