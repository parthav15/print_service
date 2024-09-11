from django.shortcuts import render
import jwt
from django.conf import settings
from .models import User, Otp, PrintJob
import random
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import default_storage

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
def user_register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')

        if not name or not email:
            return JsonResponse({'success': False, 'message': 'Name and Email are required.'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email is already registered.'}, status=400)

        user = User.objects.create(
            first_name=name,
            email=email,
            is_customer=False
        )

        otp_code = generate_otp()
        Otp.objects.update_or_create(user=user, defaults={'otp': otp_code})

        send_email_otp(email, otp_code)

        return JsonResponse({
            'success': True,
            'message': f'Registration initiated, OTP sent to {email}.',
            # 'token': jwt_encode(user.email)  # Uncomment if using JWT
        }, status=200)

    return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found. Please sign up first.'}, status=400)

        otp_code = generate_otp()
        Otp.objects.update_or_create(user=user, defaults={'otp': otp_code})

        send_email_otp(email, otp_code)

        return JsonResponse({
            'success': True,
            'message': f'Login initiated, OTP sent to {email}.',
            # 'token': jwt_encode(user.email)  # Uncomment if using JWT
        }, status=200)

    return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)

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
        
        try:
            token = bearer.split()[1]
        except IndexError:
            return JsonResponse({'success': False, 'message': 'Invalid Authorization header format'}, status=401)

        if not auth_user(token):
            return JsonResponse({'success': False, 'message': 'Invalid Token'}, status=401)
        
        decoded_token = jwt_decode(token)
        user_email = decoded_token.get('email')
        
        if not user_email:
            return JsonResponse({'success': False, 'message': 'Invalid token data'}, status=401)
        
        try:
            user_obj = User.objects.get(email__iexact=user_email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)

        user_details = {
            'email': user_obj.email,
            'first_name': user_obj.first_name,
            'last_name': user_obj.last_name,
            'username': user_obj.username,
            'phone_number': user_obj.phone_number,
            'address': user_obj.address,
            'two_factor': user_obj.two_factor
        }
        
        return JsonResponse({'success': True, 'message': 'User details fetched successfully.', 'user_details': user_details}, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {e}'}, status=400)
    
@csrf_exempt    
def user_edit(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST.'}, status=405)
    
    bearer = request.headers.get('Authorization')
    if not bearer:
        return JsonResponse({'success': False, 'message': 'Authorization header is required.'}, status=401)
    
    token = bearer.split()[1]
    if not auth_user(token):
        return JsonResponse({'success': False, 'message': 'Invalid Token'}, status=401)
    
    decoded_token = jwt_decode(token)
    user_email = decoded_token.get('email')
    
    if not user_email:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)
    
    try:
        user_obj = User.objects.get(email__iexact=user_email)
    except ObjectDoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
    
    data = request.POST
    valid_keys = [
        'first_name', 'last_name', 'username', 'phone_number', 'address'
    ]
    
    for key in valid_keys:
        value = data.get(key)
        if value:
            setattr(user_obj, key, value)
            
    if 'profile_picture' in request.FILES:
        profile_picture = request.FILES['profile_picture']
        filename = f'profile_pictures/customer_profile_{user_obj.id}_picture.jpg'
        user_obj.profile_picture = default_storage.save(filename, profile_picture)
        
        user_obj.save()
        
    return JsonResponse({'success': True, 'message': 'User profile updated successfully.'}, status=200)

@csrf_exempt
def upload_print_job(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST.'}, status=405)
    
    bearer = request.headers.get('Authorization')
    if not bearer:
        return JsonResponse({'success': False, 'message': 'Authentication header is required.'}, status=401)
    
    try:
        token = bearer.split()[1]
    except IndexError:
        return JsonResponse({'success': False, 'message': 'Invalid Authorization header format.'}, status=401)
    
    if not auth_user(token):
        return JsonResponse({'success': False, 'message': 'Invalid Token'}, status=401)
    
    decoded_token = jwt_decode(token)
    user_email = decoded_token.get('email')
    
    if not user_email:
        return JsonResponse({'success': False, 'message': 'Invalid token data.'}, status=401)
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)
    
    document = request.FILES.get('document')
    if not document:
        return JsonResponse({'success': False, 'message': 'Document is required.'}, status=400)
    
    bw_pages = request.POST.get('bw_pages', 0)
    color_pages = request.POST.get('color_pages', 0)
    
    try:
        bw_pages = int(bw_pages)
        color_pages = int(color_pages)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'bw_pages and color_pages must be integers.'}, status=400)
    
    try:
        filename = f'uploads/user_{user.id}_document_{document.name}'
        document_path = default_storage.save(filename, document)
        
        print_job = PrintJob.objects.create(
            user=user,
            document=document_path,
            bw_pages=bw_pages,
            color_pages=color_pages,
            is_printed=False
        )
        
        return JsonResponse({'success': True, 'message': 'Print Job created successfully.', 'print_job_id': print_job.id}, status=201)
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error creating print job: {str(e)}'}, status=400)