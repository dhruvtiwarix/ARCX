from django.contrib.auth.hashers import make_password, check_password
from rest_framework.exceptions import ValidationError
from arcx_core.models import Wallet, BusinessAlias, User

class B2BService:
    @staticmethod
    def set_transaction_pin(user, new_pin: str) -> None:
        """
        Sets a new UPI-style transaction PIN for the user's wallet.
        """
        if not new_pin.isdigit() or len(new_pin) != 6:
            raise ValidationError({"pin": "Transaction PIN must be exactly 6 digits."})
        
        user_id = user.username if hasattr(user, 'username') else user.id
        try:
            wallet = Wallet.objects.get(user_id=user_id)
        except Wallet.DoesNotExist:
            raise ValidationError({"pin": "Wallet not found for this user."})
            
        wallet.transaction_pin = make_password(new_pin)
        wallet.save(update_fields=['transaction_pin', 'updated_at'])

    @staticmethod
    def validate_transaction_pin(user, pin: str) -> bool:
        """
        Validates the provided PIN against the stored hashed PIN.
        """
        user_id = user.username if hasattr(user, 'username') else user.id
        try:
            wallet = Wallet.objects.get(user_id=user_id)
        except Wallet.DoesNotExist:
            raise ValidationError({"pin": "Wallet not found for this user."})
            
        if not wallet.transaction_pin:
            raise ValidationError({"pin": "Transaction PIN not set. Please set a PIN first."})
        
        if not check_password(pin, wallet.transaction_pin):
            raise ValidationError({"pin": "Invalid transaction PIN."})
        
        return True

    @staticmethod
    def resolve_alias_to_email(alias: str) -> str:
        """
        Resolves a BusinessAlias (e.g., 'vendor@arcx') to the underlying user's email.
        """
        try:
            business_alias = BusinessAlias.objects.select_related('user').get(alias=alias)
            return business_alias.user.email
        except BusinessAlias.DoesNotExist:
            raise ValidationError({"alias": "The provided business alias does not exist."})
