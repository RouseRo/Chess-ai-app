import json
import os
import bcrypt

# Path to admin user file
admin_file = "user_data/users/admin.json"

if os.path.exists(admin_file):
    with open(admin_file, 'r') as f:
        admin = json.load(f)
    
    # Set new password
    new_password = "admin123"  # Change this to your desired password
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    
    admin['password_hash'] = hashed
    if 'password' in admin:
        del admin['password']
    
    with open(admin_file, 'w') as f:
        json.dump(admin, f, indent=2)
    
    print(f"Admin password reset to: {new_password}")
else:
    print("Admin user file not found")