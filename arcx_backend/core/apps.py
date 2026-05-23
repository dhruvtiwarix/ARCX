# arcx_backend/core/apps.py

from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    # Change this from 'core' to 'arcx_backend.core'
    name = 'core'