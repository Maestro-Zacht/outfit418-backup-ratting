from django.urls import path

from . import views

app_name = 'outfit418backup'


urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('audit/', views.audit, name='audit'),
]
