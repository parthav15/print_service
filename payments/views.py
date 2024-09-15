from django.shortcuts import render
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from printapp.models import PrintJob, Payment, Transaction
from decimal import Decimal

def calculate_print_job_price(bw_pages, color_pages):
    bw_price_per_page = Decimal('2.00')
    color_price_per_page = Decimal('5.00')
    
    total_price = (bw_pages * bw_price_per_page) + (color_pages * color_price_per_page)
    
    return total_price
    
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@csrf_exempt
def create_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST.'}, status=405)
    
    print_job_id = request.POST.get('print_job_id')
    if not print_job_id:
        return JsonResponse({'success': False, 'message': 'Print Job ID is required'}, status=400)
    
    print_job = get_object_or_404(PrintJob, id=print_job_id)
    
    total_amount = calculate_print_job_price(print_job.bw_pages, print_job.color_pages) * 100
    
    try:
        order_data = {
            'amount': int(total_amount),
            'currency': 'INR',
            'receipt': f'print_job_{print_job.id}',
            'payment_capture': 1
        }
        razorpay_order = razorpay_client.order.create(data=order_data)
        
        payment = Payment.objects.create(
            print_job=print_job,
            amount=total_amount / 100,
            status='Pending',
        )
        
        Transaction.objects.create(
            payment=payment,
            razorpay_order_id=razorpay_order['id']
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Order created successfully.',
            'order_id': razorpay_order['id'],
            'amount': total_amount,
            'currency': 'INR',
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error creating order: {str(e)}'}, status=400)
    
@csrf_exempt
def verify_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method. Use POST.'}, status=405)
    
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_signature_id = request.POST.get('razorpay_signature')
    
    try:
        transaction = Transaction.objects.get(razorpay_order_id=razorpay_order_id)
        payment = transaction.payment
        
        razorpay_client_utility.verify_payment_signature({
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature_id,
        })
        
        payment.transaction_id = razorpay_payment_id
        payment.status = 'Completed'
        payment.save()
        
        print_job = payment.print_job
        print_job.is_payment = True
        print_job.save()
        
        success, message = send_to_printer(print_job)
        
        if success:
            return JsonResponse({'success': True, 'message': 'Payment verified and document sent to printer successfully.'}, status=200)
        else:
            return JsonResponse({'success': False, 'message': f'Payment verified but failed to send document to printer: {message}'}, status=500)
            
    except razorpay.errors.SignatureVerificationError:
        if payment:
            payment.status = 'Failed'
            payment.save()
        return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)
    
    except Transaction.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Transaction not found.'}, status=404)
        