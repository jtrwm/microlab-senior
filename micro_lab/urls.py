# micro_lab/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('booking/', views.booking_view, name='booking'),
    path('api/get-booked-slots/', views.api_get_booked_slots, name='api_get_booked_slots'),
    path('booking-complete/<str:booking_id>/', views.booking_complete, name='booking_complete'),
]