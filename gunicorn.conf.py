# gunicorn ye file khud load karta hai, Start Command: gunicorn app:app
import os
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1
threads = 4
timeout = 120   # default 30s tha -> lambe AI jawab pe worker kill ho raha tha
