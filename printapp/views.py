from django.shortcuts import render, get_object_or_404
import jwt
from django.conf import settings
from .models import User, Otp, PrintJob, Payment, Transaction
import random
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import default_storage
from payments.views import calculate_print_job_price
import json
from printapp.utils import send_to_printer

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
        document_path = default_storage.save(f'uploads/{document.name}', document)
        
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
   
@csrf_exempt    
def pay_at_the_counter(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
    print_job_id = request.POST.get('print_job_id')
    
    if not print_job_id:
        return JsonResponse({'success': False, 'message': 'Print Job ID is required.'}, status=400)

    try:
        print_job = PrintJob.objects.get(id=print_job_id)
        
        total_price = calculate_print_job_price(print_job.bw_pages, print_job.color_pages)
        
        print_job.is_payment = False
        print_job.save()
        
        owner_email = 'parthavsabrwal@gmail.com'
        subject = f"Payment request for Print Job {print_job.id}"
        message = f"A user has requested to pay at the counter for Print Job {print_job.id}. Please approve the request in the admin panel."
        
        send_mail(subject, message, settings.EMAIL_HOST_USER, [owner_email])
        
        return JsonResponse({'success': True, 'message': 'Payment request sent. Awaiting Owner Approval', 'total_price': str(total_price)}, status=200)
    
    except PrintJob.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Print Job not found.'}, status=404)
   
@csrf_exempt 
def approve_decline_payment(request):
    if request.method != 'POST':
        return JsonResponse({'success': True, 'message': 'Invalid request method. Use POST!'}, status=405)
    
    print_job_id = request.POST.get('print_job_id')
    if not print_job_id:
        return JsonResponse({'success': False, 'message': 'Print Job ID is required.'}, status=400)
    
    try:
        print_job = PrintJob.objects.get(id=print_job_id)
        
        if 'approve' in request.POST:
            print_job.is_payment = True
            print_job.status = 'approved'
            print_job.save()
            
            success, message = send_to_printer(print_job)
            if success:
                print_job.status = 'printed'
                print_job.save()
                return JsonResponse({'success': True, 'message': 'Payment approved and print job sent to printer.'}, status=200)
            else:
                return JsonResponse({'success': False, 'message': f'Payment approved, but printing failed: {message}'}, status=500)
        
        elif 'decline' in request.POST:
            print_job.status = 'declined'
            print_job.save()
            return JsonResponse({'success': True, 'message': 'Payment declined successfully.'}, status=200)
        
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action. Use "approve" or "decline".'}, status=400)
    
    except PrintJob.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Print Job not found.'}, status=404)

@csrf_exempt
def get_booking_detail(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
    print_job_id = request.POST.get('print_job_id')
    if not print_job_id:
        return JsonResponse({'success': False, 'message': 'Print Job ID is required.'}, status=400)
    
    print_job = get_object_or_404(PrintJob, id=print_job_id)
    
    try:
        payment = Payment.objects.filter(print_job=print_job).first()
        transaction = Transaction.objects.filter(payment=payment).first()
        
        document_url = print_job.document.url if print_job.document else None
        
        booking_details = {
            'print_job': {
                'id': print_job.id,
                'bw_pages': print_job.bw_pages,
                'color_pages': print_job.color_pages,
                'is_printed': print_job.is_printed,
                'is_payment': print_job.is_payment,
                'document_url': document_url,
            },
            'payment': {
                'amount': payment.amount if payment else None,
                'status': payment.status if payment else None,
                'transaction_id': payment.transaction_id if payment else None,
            },
            'transaction': {
                'razorpay_order_id': transaction.razorpay_order_id if transaction else None,
                'razorpay_payment_id': transaction.razorpay_payment_id if transaction else None,
            }
        }
        
        return JsonResponse({'success': True, 'data': booking_details}, status=200)
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error fetching booking details: {str(e)}'}, status=400)