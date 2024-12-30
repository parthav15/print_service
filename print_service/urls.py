from django.contrib import admin
from django.urls import path, include
from printapp import views 
from django.conf import settings
from django.conf.urls.static import static
from payments import urls as payments_urls
from admin import urls as admin_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.user_login, name='user_login'),
    path('register/', views.user_register, name='user_register'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('logout/', views.user_logout, name='logout'),
    path('user_get_details/', views.user_get_details, name='user_get_details'),
    path('user_edit/', views.user_edit, name='user_edit'),
    path('upload_print_job/', views.upload_print_job, name='upload_print_job'),
    path('pay_at_counter/', views.pay_at_the_counter, name='pay_at_the_counter'),
    path('get_booking_detail/', views.get_booking_detail, name='get_booking_detail'),
    path('payments/', include(payments_urls)),
    path('admin_panel/', include(admin_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
