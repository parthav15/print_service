from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from django.db.models import Sum, Count
from printapp.models import User, PrintJob, Payment, Transaction
from datetime import timedelta, datetime
from printapp.views import jwt_encode, jwt_decode, auth_user
import json
import calendar
from decimal import Decimal

@csrf_exempt
def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            return JsonResponse({'success': False, 'message': 'Email and password are required.'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid email or password'}, status=400)

        user = authenticate(request, username=user.email, password=password)
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                token = jwt_encode(user.email)
                return JsonResponse({'success': True, 'message': 'Login successful.', 'email': email, 'token': token}, status=200)
            else:
                return JsonResponse({'success': False, 'message': 'You do not have admin access.'}, status=403)
        else:
            return JsonResponse({'success': False, 'message': 'Invalid email or password'}, status=400)
        
    return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)

@csrf_exempt
def admin_logout(request):
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
def admin_dashboard(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
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
        if not user_obj.is_staff: 
            return JsonResponse({'success': False, 'message': 'You do not have admin access.'}, status=403)
    except ObjectDoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
    
    current_date = now().date()
    
    data = []
    previous_month_avg_revenue = None
    
    for i in range(6):
        first_day_of_current_month = current_date.replace(day=1)
        first_day_of_target_month = (first_day_of_current_month - timedelta(days=i * 30)).replace(day=1)
        last_day_of_target_month = calendar.monthrange(first_day_of_target_month.year, first_day_of_target_month.month)[1]
        month_start = first_day_of_target_month
        month_end = first_day_of_target_month.replace(day=last_day_of_target_month)
        
        month_name = month_start.strftime('%B %Y')
        
        total_customers = User.objects.filter(
            is_customer=True,
            date_joined__range=(month_start, month_end)
        ).count()
        
        total_bookings = PrintJob.objects.filter(
            is_printed=True,
            created_at__range=(month_start, month_end)
        ).count()
        
        total_revenue = Payment.objects.filter(
            status='Completed',
            created_at__range=(month_start, month_end)
        ).aggregate(total=Sum('amount'))['total'] or Decimal(0)
        
        avg_revenue_per_booking = (total_revenue / total_bookings) if total_bookings > 0 else Decimal(0)
            
        if previous_month_avg_revenue is not None and previous_month_avg_revenue > 0:
            performance_percentage = (avg_revenue_per_booking / previous_month_avg_revenue) * Decimal(100)
        else:
            performance_percentage = Decimal(100) 
        
        data.append({
            'month': month_name,
            'total_customers': total_customers,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'performance': {
                'value': avg_revenue_per_booking,
                'percentage': performance_percentage,
            }
        })
        
        previous_month_avg_revenue = avg_revenue_per_booking if total_bookings > 0 else None
     
    total_customers_all_time = User.objects.filter(is_customer=True).count()
    total_bookings_all_time = PrintJob.objects.filter(is_printed=True).count()
    total_revenue_all_time = Payment.objects.filter(status='Completed').aggregate(total=Sum('amount'))['total'] or Decimal(0)
    
    all_time_avg_revenue_per_booking = total_revenue_all_time / total_bookings_all_time if total_bookings_all_time > 0 else Decimal(0)
    target_avg_revenue = Decimal(20.0)
    all_time_performance_percentage = (all_time_avg_revenue_per_booking / target_avg_revenue) * Decimal(100) if target_avg_revenue > 0 else Decimal(0)
       
    pending_print_jobs = PrintJob.objects.filter(status='pending')
        
    return JsonResponse({
        'success': True,
        'total_customers_all_time': total_customers_all_time,
        'total_bookings_all_time': total_bookings_all_time,
        'total_revenue_all_time': total_revenue_all_time,
        'all_time_performance': {
            'value': all_time_avg_revenue_per_booking,
            'percentage': all_time_performance_percentage,
        },
        'data': data,
        'pending_print_jobs': [
            {
                'id': job.id,
                'document': job.document.url,
                'bw_pages': job.bw_pages,
                'color_pages': job.color_pages,
                'created_at': job.created_at,
                'status': job.status
            } for job in pending_print_jobs
        ]
    }, status=200)

@csrf_exempt
def print_jobs_list(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST!'}, status=405)
    
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
        if not user_obj.is_staff: 
            return JsonResponse({'success': False, 'message': 'You do not have admin access.'}, status=403)
    except ObjectDoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'}, status=404)

    print_jobs = PrintJob.objects.select_related('printer').prefetch_related('payment', 'payment__transaction').all()

    jobs_data = []
    for job in print_jobs:
        job_data = {
            'id': job.id,
            'document': job.document.url,
            'bw_pages': job.bw_pages,
            'color_pages': job.color_pages,
            'printer': job.printer.name if job.printer else None,
            'is_printed': job.is_printed,
            'is_payment': job.is_payment,
            'status': job.status,
            'created_at': job.created_at,
        }

        if hasattr(job, 'payment'):
            payment = job.payment
            job_data['payment'] = {
                'amount': payment.amount,
                'status': payment.status,
                'transaction_id': payment.transaction_id,
                'razorpay_payment_id': payment.transaction.razorpay_payment_id if payment.transaction else None,
                'razorpay_order_id': payment.transaction.razorpay_order_id if payment.transaction else None,
                'razorpay_signature': payment.transaction.razorpay_signature if payment.transaction else None,
            }
        else:
            job_data['payment'] = None 
        jobs_data.append(job_data)

    return JsonResponse({
        'success': True,
        'print_jobs': jobs_data,
    }, status=200)
