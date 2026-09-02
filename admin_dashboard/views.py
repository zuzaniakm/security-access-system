import os
import threading
from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import AuthorizedUser, AuthorizedUserPhoto, AccessLog, hash_uid
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.http import JsonResponse, FileResponse, Http404
from security_access_system.face_encoding import encode_user, remove_user_encodings

encoding_status = {}  
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

def encode_user_async(user):
    encoding_status[user.id] = 'encoding'
    try:
        encode_user(user)
        encoding_status[user.id] = 'done'
    except Exception as e:
        encoding_status[user.id] = 'error'
        print(f"[ERROR] Ecoding failed: {e}")

def encoding_status_view(request, user_id):
    status = encoding_status.get(user_id, 'done')
    return JsonResponse({'status': status})

def validate_photos(photos):
    errors = []
    for photo in photos:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            errors.append(_("%(name)s is not a supported file type (allowed: JPG, PNG, WEBP).") % {"name": photo.name})
    return errors

# Create your views here.
def login_user(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            messages.success(request, _("Login successful."))
            return redirect('home')
        else:
            messages.warning(request, _('Incorrect username or password.'))
            return redirect('login')
    return render(request, 'login.html', {})

@login_required
def logout_user(request):
    logout(request)
    messages.success(request, _('You have been logged out!'))
    return redirect('home')

@login_required
def home(request):
    if request.user.is_authenticated:
        authorized_users = AuthorizedUser.objects.prefetch_related('photos').all()
        encoding_user_id = request.session.pop('encoding_user_id', None)
        return render(request, 'home.html', {
            'authorized_users': authorized_users,
            'encoding_user_id': encoding_user_id,
        })
    else:
        return redirect('login')
        
@login_required
def dataset(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    response = FileResponse(open(file_path, "rb"))
    response["Cache-Control"] = "private, max-age=3600" 
    return response

@login_required
def add_user(request):
    if request.method == 'POST':
        photos = request.FILES.getlist('photos')
        errors = {}

        photo_errors = validate_photos(photos)
        if photo_errors:
            errors['photos'] = ' '.join(photo_errors)

        if len(photos) < 1:
            errors['photos'] = _("Upload at least 1 photo.")
        elif len(photos) > 5:
            errors['photos'] = _("Upload a maximum of 5 photos.")

        if not errors:
            try:
                with transaction.atomic():
                    user = AuthorizedUser(
                        email=request.POST.get('email'),
                        uid=request.POST.get('uid'),
                        blocked='blocked' in request.POST,
                    )
                    user.full_clean()  
                    user.save()
                    for photo in photos:
                        photo_instance = AuthorizedUserPhoto(user=user, photo=photo)
                        photo_instance.full_clean()
                        photo_instance.save()

                thread = threading.Thread(target=encode_user_async, args=(user,))
                thread.daemon = True
                thread.start()
                request.session['encoding_user_id'] = user.id
                messages.success(request, _("User has been successfully added."))
                return redirect('home')
            except ValidationError as e:
                errors['photos'] = ' '.join(e.messages)
                #errors = e.message_dict

        return render(request, 'add_user.html', {'errors': errors, 'post': request.POST})

    return render(request, 'add_user.html', {})

@login_required
def edit_user(request, user_id):
    encoding_user_id = request.session.pop('encoding_user_id', None)
    user = get_object_or_404(AuthorizedUser, id=user_id)

    if request.method == 'POST':
        photos = request.FILES.getlist('photos')
        errors = {}

        photo_errors = validate_photos(photos)
        if photo_errors:
            errors['photos'] = ' '.join(photo_errors)

        current_photo_count = user.photos.count()
        if len(photos) + current_photo_count > 5:
            errors['photos'] = _("You can have a maximum of 5 photos (currently: %(count)s).") % {'count': current_photo_count}

        if not errors:
            try:
                with transaction.atomic():
                    user.email = request.POST.get('email', user.email)
                    user.blocked = 'blocked' in request.POST
                    new_uid = request.POST.get('uid', '').strip()
                    if new_uid:
                        user.uid = hash_uid(new_uid)  

                    user.full_clean()
                    user.save()
                    for photo in photos:
                        photo_instance = AuthorizedUserPhoto(user=user, photo=photo)
                        photo_instance.full_clean()
                        photo_instance.save()
                thread = threading.Thread(target=encode_user_async, args=(user,))
                thread.daemon = True
                thread.start()
                request.session['encoding_user_id'] = user.id
                messages.success(request, _("User has been successfully edited."))
                return redirect('home')
            except ValidationError as e:
                errors['photos'] = ' '.join(e.messages)
                #errors = e.message_dict
            except ValueError as e:
                errors['uid'] = str(e)

        return render(request, 'edit_user.html', {'au': user, 'errors': errors, 'post': request.POST})

    return render(request, 'edit_user.html', {'au': user, 'encoding_user_id': encoding_user_id,})

@login_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(AuthorizedUser, id=user_id)
        remove_user_encodings(user)
        user.delete()
        messages.success(request, _('User deleted successfully.'))
        return redirect('home')
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def delete_photo(request, photo_id):
    if request.method == 'POST':
        photo = get_object_or_404(AuthorizedUserPhoto, id=photo_id)
        user = photo.user

        if user.photos.count() <= 1:
            return JsonResponse({'error': _('At least 1 photo must remain.')}, status=400)

        photo.photo.delete() 
        photo.delete()
        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def toggle_blocked(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(AuthorizedUser, id=user_id)
        user.blocked = not user.blocked
        user.save(update_fields=['blocked'])
        return JsonResponse({'blocked': user.blocked})
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def logs(request):
    access_logs = AccessLog.objects.select_related('user').all()
    return render(request, 'logs.html', {'access_logs': access_logs})