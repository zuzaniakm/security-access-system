from django.contrib import admin
from .models import AuthorizedUser, AuthorizedUserPhoto, AccessLog

# Register your models here.
admin.site.register(AuthorizedUser)
admin.site.register(AuthorizedUserPhoto)
admin.site.register(AccessLog)