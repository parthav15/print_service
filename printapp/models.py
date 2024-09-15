from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image

ROLE = {
    (1, 'Administrator'),
    (2, 'Moderator'),
    (3, 'Customer Support Staff')
}

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, default="")
    last_name = models.CharField(max_length=150, default="")
    username = models.CharField(max_length=150, default="", blank=True)
    phone_number = models.CharField(max_length=150, default="")
    address = models.TextField(blank=True, null=True)
    is_admin = models.BooleanField('Is admin', default=False)
    is_customer = models.BooleanField('Is customer', default=False)
    is_email = models.BooleanField('Is email', default=False)
    is_staff = models.BooleanField('Is staff', default=False)
    is_role = models.PositiveIntegerField(choices=ROLE, default=0)
    password = models.CharField(max_length=225, null=True, blank=True)
    two_factor = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/', default="", blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            if img.height > 200 or img.width > 200:
                output_size = (200, 200)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path)
                
    def __str__(self):
        return self.email

class Otp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class PrintJob(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=True, blank=True)
    document = models.FileField(upload_to='uploads/')
    bw_pages = models.IntegerField(default=0)
    color_pages = models.IntegerField(default=0)
    printer = models.ForeignKey('Printer', on_delete=models.SET_NULL, null=True, blank=True)
    is_printed = models.BooleanField(default=False)
    is_payment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Print Job {self.id} - {self.document.name}"
    
class Payment(models.Model):
    print_job = models.OneToOneField(PrintJob, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')])
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"
    
class Printer(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Offline', 'Offline')])
    paper_status = models.CharField(max_length=20, choices=[('Full', 'Full'), ('Low', 'Low'), ('Empty', 'Empty')], default='Full')
    
    def __str__(self):
        return self.name
    
class PrintJobLog(models.Model):
    print_job = models.ForeignKey(PrintJob, on_delete=models.CASCADE)
    log_message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Log for Print Job {self.print_job.id}"
    
class Pricing(models.Model):
    document_type = models.ForeignKey('DocumentType', on_delete=models.CASCADE)
    price_per_page = models.DecimalField(max_digits=5, decimal_places=2)
    color_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.5)
    
    def __str__(self):
        return f"Pricing for {self.document_type.name}"
    
class DocumentType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
class Transaction(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Transaction {self.razorpay_payment_id}"