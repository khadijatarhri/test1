from django.urls import path  
from .views import UploadCSVView, ProcessCSVView  
  
app_name = 'csv_anonymizer'  
  
urlpatterns = [  
    path('upload/', UploadCSVView.as_view(), name='upload'),  
    path('process/<int:job_id>/', ProcessCSVView.as_view(), name='process'),  
]