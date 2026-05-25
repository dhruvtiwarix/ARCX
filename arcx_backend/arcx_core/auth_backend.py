from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User as AuthUser
from arcx_core.models import User as ArcxUser

class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend to allow users to log in using their email.
    The frontend sends the email in the 'username' field to SimpleJWT.
    We look up the ARCX user by email, get their UUID, and use that to
    find the corresponding Django AuthUser.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
            
        try:
            # 1. Look up the ARCX business user by email
            arcx_user = ArcxUser.objects.get(
                email=username.lower().strip(), 
                deleted_at__isnull=True,
                is_active=True
            )
            
            # 2. Find the corresponding Django AuthUser (its username is the ARCX UUID)
            auth_user = AuthUser.objects.get(username=str(arcx_user.id))
            
            # 3. Check password
            if auth_user.check_password(password):
                return auth_user
        except (ArcxUser.DoesNotExist, AuthUser.DoesNotExist):
            return None
            
        return None
