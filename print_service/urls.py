"""
URL configuration for print_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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
