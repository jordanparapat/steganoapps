from django.urls import path
from steganoModule import views

app_name = 'steganoModule'
urlpatterns = [
    path('', views.index),
    path('encodePage', views.encodePage),
    path('decodePage', views.decodePage),
    path('resultPage', views.resultPage)
]