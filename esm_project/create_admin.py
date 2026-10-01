import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esm_core.settings')
django.setup()

from django.contrib.auth.models import User

# Delete existing admin user if it exists
User.objects.filter(username='admin').delete()

# Create new admin superuser
admin = User.objects.create_superuser('admin', 'admin@esm.local', 'admin123')
print(f'Admin superuser created: {admin.username}')
print(f'Is staff: {admin.is_staff}')
print(f'Is superuser: {admin.is_superuser}')
