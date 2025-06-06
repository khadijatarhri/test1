from django.db import models

class AnonymizationJob(models.Model):
    user_email = models.CharField(max_length=255)  
    original_filename = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')  # pending, processing, completed
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"
    
    class Meta:
        app_label = 'csv_anonymizer'