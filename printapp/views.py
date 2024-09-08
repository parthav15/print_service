from django.shortcuts import render
import jwt
from django.conf import settings
from .models import User, Otp
import random
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout

SECRET_KEY = settings.SECRET_KEY

def jwt_encode(email):
    encoded_token = jwt.encode({'email': email}, SECRET_KEY, algorithm='HS256')
    return encoded_token

def jwt_decode(token):
    decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    return decoded_token

def auth_user(token):
    decoded_token = jwt_decode(token)
    email = decoded_token['email']
    obj = User.objects.filter(email=email).first()
    if obj:
        return True
    else:
        return False
    
def generate_otp():
    return random.randint(100000, 999999)

def send_email_otp(email, otp_code):
    send_mail(
        'YOUR OTP CODE',
        f'Your otp code {otp_code}. Use this to complete the login or registeration.',
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
    
@csrf_exempt
def user_register_login(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)
        
        try:
            user = User.objects.get(email=email)
            is_new_user = False
        except User.DoesNotExist:
            user = User.objects.create(
                first_name=name,
                email=email,
                is_customer=False
            )
            is_new_user = True
            
        otp_code = generate_otp()
        Otp.objects.update_or_create(user=user, defaults={'otp': otp_code})
        
        send_email_otp(email, otp_code)
        
        action = 'Login' if not is_new_user else 'Register'
        return JsonResponse({
            'success': True,
            'message': f'{action} initiated, OTP sent to {email}.',
            'token': jwt_encode(user.email)
        }, status=200)
    return JsonResponse({'success': True, 'message': 'Invalid request method, Use POST!'}, status=405)

@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        
        if not email or not otp:
            return JsonResponse({'success': False, 'message': 'Email and OTP are required.'}, status=400)
                
        user = authenticate(request, email=email, otp=otp)
        
        if user is None:
            return JsonResponse({'success': False, 'message': 'Invalid OTP or User Does not exist.'}, status=400)
                
        login(request, user)
        
        user.is_customer = True
        user.save()
        
        token = jwt_encode(user.email)
        
        return JsonResponse({
            'success': True,
            'message': 'OTP verified successfully. User logged in.',
            'token': token
        }, status=200)
        
    return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)

@csrf_exempt
def user_logout(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'User is not logged in.'}, status=401)
        
        logout(request)
        return JsonResponse({'success': True, 'message': 'Logout Successful.'}, status=200)
    
    except Exception as e:
        return JsonResponse({'success': 'False', 'message': f'Error: {e}'}, status=400)
    

@csrf_exempt
def user_get_details(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST.'}, status=405)
    
    try:
        bearer = request.headers.get('Authorization')
        if not bearer:
            return JsonResponse({'success': False, 'message': 'Authentication header is required'}, status=401)
        
        # Extract the token from the Authorization header
        try:
            token = bearer.split()[1]
        except IndexError:
            return JsonResponse({'success': False, 'message': 'Invalid Authorization header format'}, status=401)

        # Validate the token
        if not auth_user(token):
            return JsonResponse({'success': False, 'message': 'Invalid Token'}, status=401)
        
        decoded_token = jwt_decode(token)
        user_email = decoded_token.get('email')
        
        if not user_email:
            return JsonResponse({'success': False, 'message': 'Invalid token data'}, status=401)
        
        # Fetch the user details
        try:
            user_obj = User.objects.get(email__iexact=user_email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)

        user_details = {
            'email': user_obj.email,
            'first_name': user_obj.first_name,
            'last_name': user_obj.last_name,
            'username': user_obj.username,
            'phone_number': user_obj.phone_number,  # Fixed typo from 'phone_numer'
            'address': user_obj.address,
            'two_factor': user_obj.two_factor
        }
        
        return JsonResponse({'success': True, 'message': 'User details fetched successfully.', 'user_details': user_details}, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {e}'}, status=400)