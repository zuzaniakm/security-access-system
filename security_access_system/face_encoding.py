import os
import pickle
import cv2
import face_recognition
from django.conf import settings

def encode_user(user):  
    if os.path.exists(settings.ENCODINGS_PATH):
        with open(settings.ENCODINGS_PATH, 'rb') as f:
            data = pickle.loads(f.read())
        knownEncodings = data['encodings']
        knownNames = data['names']
    else:
        knownEncodings = []
        knownNames = []

    filtered = [
        (enc, name)
        for enc, name in zip(knownEncodings, knownNames)
        if name != str(user.id)
    ]
    knownEncodings = [e for e, _ in filtered]
    knownNames = [n for _, n in filtered]

    for photo in user.photos.all():
        image_path = os.path.join(settings.MEDIA_ROOT, photo.photo.name)
        image = cv2.imread(image_path)

        if image is None:
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model='hog')
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(str(user.id))

    data = {'encodings': knownEncodings, 'names': knownNames}
    with open(settings.ENCODINGS_PATH, 'wb') as f:
        f.write(pickle.dumps(data))

    print(f"[INFO] Encodings for user {user.id} ({user.email}) saved.")

def remove_user_encodings(user):
    if not os.path.exists(settings.ENCODINGS_PATH):
        return

    with open(settings.ENCODINGS_PATH, 'rb') as f:
        data = pickle.loads(f.read())

    filtered = [
        (enc, name)
        for enc, name in zip(data['encodings'], data['names'])
        if name != str(user.id)
    ]

    data['encodings'] = [e for e, _ in filtered]
    data['names'] = [n for _, n in filtered]

    with open(settings.ENCODINGS_PATH, 'wb') as f:
        f.write(pickle.dumps(data))

    print(f"[INFO] Encodings for user {user.id} removed.")