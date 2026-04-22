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
]