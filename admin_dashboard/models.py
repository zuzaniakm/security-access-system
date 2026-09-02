import re
import os
import hashlib
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

def normalize_uid(uid: str) -> str:
    normalized = re.sub(r'[^0-9A-Fa-f]', '', uid).upper()
    if len(normalized) != 14:
        raise ValueError("Enter valid UID.")
    return normalized


def hash_uid(uid: str) -> str:
    normalized = normalize_uid(uid)
    return hashlib.sha256((settings.SECRET_KEY + normalized).encode()).hexdigest()

class AuthorizedUser(models.Model):
    create_at = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(null=False, unique=True)
    uid = models.CharField(max_length=64, unique=True, db_index=True, null=False)
    blocked = models.BooleanField(default=False)

    def clean(self):
        try:
            if not self.pk:
                self.uid = hash_uid(self.uid)
        except ValueError as e:
            raise ValidationError({'uid': str(e)})
    
    def delete(self, *args, **kwargs):
        storage = self.photos.first().photo.storage
        for photo in self.photos.all():
            photo.photo.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.id} {self.email}"



def user_photo_path(instance, filename):
    return f'{instance.user.id}/{filename}'

def validate_image_type(value):
    allowed = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f"Unsupported file format. Allowed: JPG, PNG, WEBP.")

class AuthorizedUserPhoto(models.Model):
    user = models.ForeignKey(
        AuthorizedUser,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    photo = models.ImageField(upload_to=user_photo_path, validators=[validate_image_type])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo {self.id} for {self.user.email}"



class AccessLog(models.Model):
    class Result(models.TextChoices):
        ACCESS_GRANTED = 'ACCESS_GRANTED', 'Acces granted'
        DENIED_BLOCKED = 'DENIED_BLOCKED', 'Access denied: blocked user'
        DENIED_UNKNOWN = 'DENIED_UNKNOWN', 'Access denied: unknown card'
        DENIED_FACE = 'DENIED_FACE', 'Access denied: face not recognized'
        DENIED_SPOOF = 'DENIED_SPOOF', 'Access denied: face spoofing detected'

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        AuthorizedUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='access_logs'
    )
    uid_hash = models.CharField(max_length=64)
    result = models.CharField(max_length=20, choices=Result.choices)
    device = models.CharField(max_length=128, default='Unknown device')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.result}"