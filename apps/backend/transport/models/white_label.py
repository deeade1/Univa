# apps/backend/transport/models/white_label.py
from django.core.validators import URLValidator
from django.db import models


class WhiteLabelClient(models.Model):
    """White-label client configuration"""
    
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=200, validators=[URLValidator()])
    
    # Branding
    logo = models.ImageField(upload_to='white_label/logos/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#3B82F6')  # Hex code
    secondary_color = models.CharField(max_length=7, default='#1E40AF')
    font_family = models.CharField(max_length=100, default='Inter')
    
    # Customization
    custom_css = models.TextField(blank=True)
    custom_js = models.TextField(blank=True)
    favicon = models.ImageField(upload_to='white_label/favicons/', null=True, blank=True)
    
    # Content
    company_name = models.CharField(max_length=100)
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=20, blank=True)
    terms_of_service = models.URLField(blank=True)
    privacy_policy = models.URLField(blank=True)
    
    # Features
    enabled_features = models.JSONField(default=dict)
    custom_features = models.JSONField(default=dict)
    
    # API
    api_key = models.CharField(max_length=100, unique=True)
    webhook_url = models.URLField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "White-label Client"
        verbose_name_plural = "White-label Clients"
    
    def __str__(self):
        return self.name

class WhiteLabelConfiguration(models.Model):
    """Per-client white-label configuration"""
    
    client = models.OneToOneField(
        WhiteLabelClient,
        on_delete=models.CASCADE,
        related_name='configuration'
    )
    
    # UI/UX Configuration
    theme_mode = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto'),
        ],
        default='light'
    )
    
    # Feature flags
    enable_ride_sharing = models.BooleanField(default=True)
    enable_sustainability_tracking = models.BooleanField(default=True)
    enable_accessibility_features = models.BooleanField(default=True)
    enable_analytics_dashboard = models.BooleanField(default=True)
    
    # Payment configuration
    payment_gateway = models.CharField(
        max_length=50,
        choices=[
            ('stripe', 'Stripe'),
            ('paypal', 'PayPal'),
            ('custom', 'Custom'),
        ],
        default='stripe'
    )
    
    # Custom domains
    custom_domains = models.JSONField(default=list)
    
    # Analytics configuration
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = "White-label Configuration"
        verbose_name_plural = "White-label Configurations"

# apps/backend/transport/services/white_label_service.py
class WhiteLabelService:
    """Service for white-label functionality"""
    
    def __init__(self):
        self.client_cache = {}
    
    def get_client_configuration(self, domain=None, api_key=None):
        """Get white-label configuration for client"""
        cache_key = domain or api_key
        
        if cache_key in self.client_cache:
            return self.client_cache[cache_key]
        
        try:
            if domain:
                client = WhiteLabelClient.objects.get(domain=domain, is_active=True)
            elif api_key:
                client = WhiteLabelClient.objects.get(api_key=api_key, is_active=True)
            else:
                return None
            
            config = {
                'client': client,
                'configuration': client.configuration,
                'branding': self.get_branding_data(client),
                'features': self.get_enabled_features(client),
            }
            
            self.client_cache[cache_key] = config
            return config
            
        except WhiteLabelClient.DoesNotExist:
            return None
    
    def get_branding_data(self, client):
        """Get branding data for client"""
        return {
            'name': client.company_name,
            'logo_url': client.logo.url if client.logo else None,
            'primary_color': client.primary_color,
            'secondary_color': client.secondary_color,
            'font_family': client.font_family,
            'favicon_url': client.favicon.url if client.favicon else None,
            'support_email': client.support_email,
            'support_phone': client.support_phone,
        }
    
    def get_enabled_features(self, client):
        """Get enabled features for client"""
        base_features = {
            'ride_booking': True,
            'ride_tracking': True,
            'payment_processing': True,
            'user_management': True,
        }
        
        # Merge with client-specific features
        if client.configuration:
            base_features.update({
                'ride_sharing': client.configuration.enable_ride_sharing,
                'sustainability_tracking': client.configuration.enable_sustainability_tracking,
                'accessibility_features': client.configuration.enable_accessibility_features,
                'analytics_dashboard': client.configuration.enable_analytics_dashboard,
            })
        
        # Add custom features
        if client.custom_features:
            base_features.update(client.custom_features)
        
        return base_features
    
    def generate_white_label_css(self, client):
        """Generate custom CSS for white-label client"""
        css_template = f"""
        :root {{
            --primary-color: {client.primary_color};
            --secondary-color: {client.secondary_color};
            --font-family: {client.font_family}, sans-serif;
        }}
        
        .brand-primary {{
            background-color: {client.primary_color};
            border-color: {client.primary_color};
        }}
        
        .brand-secondary {{
            background-color: {client.secondary_color};
            border-color: {client.secondary_color};
        }}
        
        .text-brand-primary {{
            color: {client.primary_color};
        }}
        
        .text-brand-secondary {{
            color: {client.secondary_color};
        }}
        
        body {{
            font-family: {client.font_family}, sans-serif;
        }}
        
        {client.custom_css}
        """
        
        return css_template
    
    def validate_client_domain(self, domain, api_key):
        """Validate client domain and API key"""
        try:
            client = WhiteLabelClient.objects.get(
                domain=domain,
                api_key=api_key,
                is_active=True
            )
            return True, client
        except WhiteLabelClient.DoesNotExist:
            return False, None
    
    def create_white_label_client(self, client_data):
        """Create new white-label client"""
        try:
            client = WhiteLabelClient.objects.create(
                name=client_data['name'],
                domain=client_data['domain'],
                primary_color=client_data.get('primary_color', '#3B82F6'),
                secondary_color=client_data.get('secondary_color', '#1E40AF'),
                font_family=client_data.get('font_family', 'Inter'),
                company_name=client_data['company_name'],
                support_email=client_data['support_email'],
                api_key=secrets.token_urlsafe(32),
                enabled_features=client_data.get('enabled_features', {}),
            )
            
            # Create configuration
            WhiteLabelConfiguration.objects.create(
                client=client,
                **client_data.get('configuration', {})
            )
            
            return client
            
        except Exception as e:
            logger.error(f"Error creating white-label client: {str(e)}")
            raise