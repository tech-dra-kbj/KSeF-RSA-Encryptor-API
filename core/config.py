import os
import re

# ==============================
# Database
# ==============================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.getenv("KEY_DB_PATH", os.path.join(INSTANCE_DIR, "keys.db"))

# ==============================
# Key settings
# ==============================

DEFAULT_TTL_SECONDS = 86400
KEY_TTL_SECONDS = int(os.getenv("KEY_TTL_SECONDS", DEFAULT_TTL_SECONDS))

RSA_KEY_SIZE = 2048

# ==============================
# Cleanup
# ==============================

CLEANUP_GRACE_SECONDS = 120  # dodatkowy bufor przy kasowaniu wygasłych kluczy

# ==============================
# SID validation
# ==============================

SID_REGEX = re.compile(r"^[A-Z0-9]{6}$")