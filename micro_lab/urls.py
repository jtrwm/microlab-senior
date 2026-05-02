from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('booking/', views.booking_view, name='booking'),
    path('api/get-booked-slots/', views.api_get_booked_slots, name='api_get_booked_slots'),
    path('booking-complete/<str:booking_id>/', views.booking_complete, name='booking_complete'),
    path('login/', auth_views.LoginView.as_view(template_name='micro_lab/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('all-slides/', views.all_slides_view, name='all_slides'),
    path('api/calendar-events/', views.calendar_events, name='calendar_events'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('labadmin/', views.admin_dashboard, name='labadmin'), 
    path('labadmin/cancel/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('labadmin/edit_booking/<str:booking_id>/', views.admin_edit_booking, name='edit_booking'),
    path('labadmin/cancel/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('labadmin/admin_slides/', views.admin_slides, name='admin_slides'),
    path('labadmin/slide/save/', views.save_slide, name='save_slide'),
    path('labadmin/slide/delete/<str:slide_id>/', views.delete_slide, name='delete_slide'),
    path('ai-dashboard/', views.ai_dashboard, name='ai_dashboard'),
    path('run-ai/', views.run_ai, name='run_ai'),
]