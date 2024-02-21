from .views import *
from rest_framework import routers
from django.urls import path, include


urlpatterns = [
    path('clinicaltrialsinfo', ClinicalTrialsLLMView.as_view(), name='clinical-trial-info')]