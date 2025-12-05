import json
import os
import bcrypt
from datetime import datetime

os.makedirs("user_data/users", exist_ok=True)

new_password = "admin123"
hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

admin = {
    "username": "admin",
    "email": "admin@chess.local",
    "password_hash": hashed,
    "is_admin": True,
    "created_at": datetime.utcnow().isoformat(),
    "games_played": 0
}

with open("user_data/users/admin.json", 'w') as f:
    json.dump(admin, f, indent=2)

print(f"Admin user created with password: {new_password}")