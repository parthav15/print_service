from django.urls import path, include
from . import views

urlpatterns = [
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    path('admin_get_details/', views.admin_get_details, name='admin_get_details'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve_decline/', views.approve_decline_payment, name='approve_decline_payment'),
    path('print_jobs_list/', views.print_jobs_list, name='print_jobs_list'),
]