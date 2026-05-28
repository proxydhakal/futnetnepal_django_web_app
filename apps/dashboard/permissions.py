from django.contrib.auth.mixins import UserPassesTestMixin


class StaffRequiredMixin(UserPassesTestMixin):
    login_url = '/iamadmin/login/'

    def test_func(self):
        return self.request.user.is_active and (
            self.request.user.is_staff or self.request.user.is_superuser
        )
