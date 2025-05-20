from django.db import models

# Create your models here.
from django.db import models  
from django.contrib.auth.models import User  
  
class AnonymizationJob(models.Model):  
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  
    original_filename = models.CharField(max_length=255)  
    upload_date = models.DateTimeField(auto_now_add=True)  
    status = models.CharField(max_length=20, default='pending')  # pending, processing, completed  
      
    def __str__(self):  
        return f"{self.original_filename} - {self.status}"  
      
    class Meta:  
        app_label = 'csv_anonymizer'