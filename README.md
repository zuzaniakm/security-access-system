# Security Access System

A two-factor physical access control system built on the Raspberry Pi 5, combining **NFC/RFID card identification** with **biometric face recognition** and anti-spoofing protection from [Silent-Face-Anti-Spoofing-onnx](https://github.com/QingHeYang/Silent-Face-Anti-Spoofing-onnx) to secure restricted spaces. Authorized users and access history are managed through a **Django** web admin panel. Developed as a [master's thesis](https://opac.crzp.sk/?fn=detailBiblioForm&sid=70D560FC111767F5326C7EEF9293) at the University of Žilina, Faculty of Management Science and Informatics.

## Overview

The system requires a user to present a valid RFID/NFC card _and_ pass a live face-recognition check before an electric lock is unlocked. All authentication logic runs locally on the device, so it does not depend on an internet connection to grant or deny access. The system includes a Django-based web dashboard for administrators to manage authorized users, view access logs, and receive email alerts when a blocked person attempts entry.

**Features:**

- Two-factor authentication: RFID/NFC card + face recognition
- Face anti-spoofing check to reject photo/video spoofing attempts
- Web-based admin dashboard (add/edit/remove/block users, manage photos)
- Full access logging
- Automatic email alerts when a blocked user attempts access

## Required Hardware

| Component  | Model                                                                            |
| ---------- | -------------------------------------------------------------------------------- |
| Main board | Raspberry Pi 5 (4 GB or more)                                                    |
| Camera     | Any camera module connected via CSI (USB cameras should work with minor changes) |
| NFC reader | PN532 NFC module (I²C mode)                                                      |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/zuzaniakm/security-access-system.git
cd security-access-system
```

### 2. Create and activate a virtual environment

```bash
python -m venv sas
source sas/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `face_recognition` requires `dlib`, which must be compiled from source on Raspberry Pi. This can take 30–60 minutes.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-django-secret-key
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
DEVICE_NAME=Main Entrance
SITE_URL=http://your-pi-ip:8000
```

### 5. Apply migrations and create admin user

```bash
cd security_access_system
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run

```bash
python manage.py runserver 0.0.0.0:8000
```

## Project Structure

```
.
├── manage.py                      # Django management entry point
├── db.sqlite3                     # SQLite database (users, photos, access logs)
├── encodings.pickle               # Cached face-encoding vectors
├── dataset/                       # Photos of authorized users
├── anti_spoofing/                 # Pretrained ONNX anti-spoofing models
├── admin_dashboard/                # Django app – admin web interface
│   ├── templates/                 # HTML templates (login, home, logs, forms...)
│   ├── static/{css,js}/           # Frontend assets
│   ├── locale/                    # Translation files (sk/en)
│   ├── admin.py / apps.py / urls.py / views.py
│   └── tests.py
└── security_access_system/        # Project configuration package
    ├── settings.py                # Django settings
    ├── urls.py                    # Root URL routing
    ├── access_control.py          # Core access-control loop (NFC + face recognition)
    ├── face_encoding.py           # Face-encoding generation/management
    ├── asgi.py / wsgi.py
```

## Data Models

### AuthorizedUser

| Field        | Description                                               |
| ------------ | --------------------------------------------------------- |
| `email`      | Unique email address                                      |
| `uid`        | SHA-256 hash of the NFC card UID (salted with SECRET_KEY) |
| `blocked`    | Whether the person is blocked from entry                  |
| `created_at` | Creation timestamp                                        |

### AuthorizedUserPhoto

| Field         | Description          |
| ------------- | -------------------- |
| `user`        | FK to AuthorizedUser |
| `photo`       | Image file           |
| `uploaded_at` | Upload timestamp     |

### AccessLog

| Field       | Description                                                            |
| ----------- | ---------------------------------------------------------------------- |
| `user`      | FK to AuthorizedUser (nullable for unknown cards)                      |
| `uid_hash`  | Hashed UID of the presented card                                       |
| `result`    | GRANTED / DENIED_BLOCKED / DENIED_UNKNOWN / DENIED_FACE / DENIED_SPOOF |
| `device`    | Name of the device where the attempt occurred                          |
| `timestamp` | Auto-set timestamp                                                     |

## How Access Control Works

1. The PN532 reader waits for an NFC/RFID card and reads its UID.
2. The UID is normalized and hashed, then checked against the `AuthorizedUser` table.
   - Unknown card: access denied and logged.
   - Blocked user: access denied, logged, and an email alert (with photo, time, and user details) is sent to the administrator.
3. If the card is valid, the camera starts and captures frames for a limited timeout window.
4. Each frame is checked for a matching face against the cached encodings from `encodings.pickle`.
5. On a match, an anti-spoofing check runs on the frame to rule out photos/screens.
6. If the face check and liveness check both pass, the lock is unlocked; otherwise access is denied.
7. The attempt (successful or not) is written to `AccessLog`.

## Admin Web Interface

- Login-protected dashboard with a card grid of authorized users (photo, email, hashed UID, blocked status, photo count)
- Add/edit users with server-side validation (email format, UID format, photo type/count limits)
- One-click block/unblock toggle
- Face-encoding generation runs asynchronously in a background thread after any user/photo change
- Access log view with color-coded results (green = granted, yellow = denied/unknown, red = blocked/spoof)
- Language switcher (Slovak/English) built on Django's localization framework
