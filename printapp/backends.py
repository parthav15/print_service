from django.contrib.auth.backends import BaseBackend
from .models import User, Otp

class OTPBackend(BaseBackend):
    def authenticate(self, request, email=None, otp=None):
        try:
            user = User.objects.get(email=email)
            otp_record = Otp.objects.filter(user=user).first()
                        
            if otp_record and otp_record.otp == otp:
                return user
            
        except (User.DoesNotExist, ValueError) as e:
            return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
