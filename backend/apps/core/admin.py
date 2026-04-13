from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Railway booking administration")
admin.site.site_title = _("Railway booking administration")

admin.site.unregister(User)
admin.site.unregister(Group)
