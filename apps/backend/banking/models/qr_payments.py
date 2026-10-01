import hashlib
import qrcode
import io
import base64
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.conf import settings
from .core import Account

class QRCode(models.Model):
    """OPay-style QR codes for payments"""
    QR_TYPES = [
        ('STATIC', 'Static - Fixed amount'),
        ('DYNAMIC', 'Dynamic - Any amount'),
        ('MERCHANT', 'Merchant QR'),
        ('PERSONAL', 'Personal QR'),
    ]
    
    # QR Code details
    qr_id = models.CharField(max_length=50, unique=True, db_index=True)
    qr_type = models.CharField(max_length=20, choices=QR_TYPES, default='STATIC')
    
    # Creator/Owner
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='created_qrcodes'
    )
    
    # For merchant QRs
    merchant = models.ForeignKey(
        'Merchant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qrcodes'
    )
    
    # Payment details
    fixed_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Usage limits
    max_uses = models.IntegerField(default=1)  # 0 = unlimited
    current_uses = models.IntegerField(default=0)
    max_amount_per_use = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=500000.00
    )
    
    # Validity
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # QR Image
    qr_image = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    qr_data = models.TextField()  # Raw QR data
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['qr_id', 'is_active']),
            models.Index(fields=['creator', 'qr_type']),
            models.Index(fields=['expires_at', 'is_active']),
        ]
    
    def __str__(self):
        return f"QR {self.qr_id} - {self.get_qr_type_display()}"
    
    def generate_qr_data(self):
        """Generate QR code payload in OPay format"""
        base_url = "https://api.yourbank.com/qr/pay"
        
        payload = {
            'qr_id': self.qr_id,
            'type': self.qr_type,
            'ref': self.reference,
            'desc': self.description[:100] if self.description else "",
        }
        
        if self.fixed_amount:
            payload['amt'] = str(self.fixed_amount)
        
        if self.merchant:
            payload['merchant_id'] = self.merchant.merchant_id
            payload['merchant_name'] = self.merchant.business_name[:50]
        
        # Convert to URL
        import urllib.parse
        qr_string = f"{base_url}?{urllib.parse.urlencode(payload)}"
        
        # Generate QR image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        # Save image
        from django.core.files.base import ContentFile
        self.qr_image.save(
            f"qr_{self.qr_id}.png",
            ContentFile(buffer.getvalue()),
            save=False
        )
        
        self.qr_data = qr_string
        return qr_string
    
    def is_valid(self):
        """Check if QR code is still valid"""
        if not self.is_active:
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        
        return True
    
    def increment_usage(self):
        """Increment usage count"""
        self.current_uses += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['current_uses', 'last_used_at', 'updated_at'])

class QRTransaction(models.Model):
    """Transactions via QR code scanning"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'QR Expired'),
        ('INVALID', 'Invalid QR'),
    ]
    
    # QR Reference
    qr_code = models.ForeignKey(
        QRCode,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    journal = models.ForeignKey(
        "banking.AccountingJournal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="qr_transactions",
        help_text="Ledger journal that posted the QR payment.",
    )
    # Payer & Payee
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='qr_payments_made'
    )
    payer_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='qr_debits'
    )
    
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='qr_payments_received'
    )
    payee_account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='qr_credits'
    )
    
    # Transaction details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # QR scan metadata
    scanned_at = models.DateTimeField()
    scanned_location = models.CharField(max_length=255, blank=True)
    device_id = models.CharField(max_length=100, blank=True)
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['qr_code', 'status']),
            models.Index(fields=['payer', 'created_at']),
            models.Index(fields=['reference']),            
            models.Index(
                fields=["journal"],
                name="banking_qr_journal_idx",
            ),
        ]
    
    def __str__(self):
        return f"QR TX {self.reference} - ₦{self.amount}"