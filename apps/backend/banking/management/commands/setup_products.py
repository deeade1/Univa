from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from ...models.bill_payments import BillerCategory, Biller
from ...models.cards import CardBrand
from ...models.investments import InvestmentProduct

class Command(BaseCommand):
    help = 'Setup initial products and services'
    
    def handle(self, *args, **options):
        self.setup_biller_categories()
        self.setup_billers()
        self.setup_card_brands()
        self.setup_investment_products()
        self.stdout.write(self.style.SUCCESS('Products setup completed'))
    
    def setup_biller_categories(self):
        categories = [
            {'name': 'Electricity', 'slug': 'electricity'},
            {'name': 'Airtime', 'slug': 'airtime'},
            {'name': 'Data Bundle', 'slug': 'data'},
            {'name': 'Cable TV', 'slug': 'cable-tv'},
            {'name': 'Internet', 'slug': 'internet'},
            {'name': 'Water', 'slug': 'water'},
            {'name': 'Government', 'slug': 'government'},
            {'name': 'Insurance', 'slug': 'insurance'},
            {'name': 'Education', 'slug': 'education'},
        ]
        
        for cat in categories:
            BillerCategory.objects.get_or_create(
                slug=cat['slug'],
                defaults={'name': cat['name'], 'is_active': True}
            )
        
        self.stdout.write('Biller categories created')
    
    def setup_billers(self):
        # Electricity providers
        electricity_cat = BillerCategory.objects.get(slug='electricity')
        billers = [
            {
                'name': 'Ikeja Electric',
                'slug': 'ikeja-electric',
                'category': electricity_cat,
                'biller_type': 'ELECTRICITY',
                'code': 'IKEJA',
                'customer_id_label': 'Account Number',
                'convenience_fee': Decimal('100'),
                'min_amount': Decimal('1000'),
                'max_amount': Decimal('500000'),
                'api_provider': 'BILLS_PAYMENT_API'
            },
            {
                'name': 'Eko Electric',
                'slug': 'eko-electric',
                'category': electricity_cat,
                'biller_type': 'ELECTRICITY',
                'code': 'EKO',
                'customer_id_label': 'Account Number',
                'convenience_fee': Decimal('100'),
                'min_amount': Decimal('1000'),
                'max_amount': Decimal('500000'),
                'api_provider': 'BILLS_PAYMENT_API'
            },
            # Add more billers...
        ]
        
        for biller_data in billers:
            Biller.objects.get_or_create(
                code=biller_data['code'],
                defaults=biller_data
            )
        
        self.stdout.write('Billers created')
    
    def setup_card_brands(self):
        brands = [
            {'name': 'Visa', 'code': 'VISA'},
            {'name': 'Mastercard', 'code': 'MASTERCARD'},
            {'name': 'Verve', 'code': 'VERVE'},
        ]
        
        for brand in brands:
            CardBrand.objects.get_or_create(
                code=brand['code'],
                defaults={'name': brand['name'], 'is_active': True}
            )
        
        self.stdout.write('Card brands created')
    
    def setup_investment_products(self):
        products = [
            {
                'name': 'Fixed Deposit - 90 Days',
                'slug': 'fixed-deposit-90',
                'product_type': 'FIXED_DEPOSIT',
                'description': 'Fixed deposit with 90 days tenure',
                'risk_level': 'VERY_LOW',
                'min_investment': Decimal('10000'),
                'max_investment': Decimal('10000000'),
                'min_tenure_days': 90,
                'max_tenure_days': 90,
                'default_tenure_days': 90,
                'interest_rate': Decimal('10.00'),
                'interest_frequency': 'AT_MATURITY',
                'management_fee': Decimal('0.50'),
                'early_withdrawal_fee': Decimal('5.00'),
                'is_active': True,
                'is_available': True,
                'available_from': timezone.now(),
            },
            {
                'name': 'Treasury Bills - 364 Days',
                'slug': 'treasury-bills-364',
                'product_type': 'TREASURY_BILLS',
                'description': 'Government treasury bills',
                'risk_level': 'VERY_LOW',
                'min_investment': Decimal('50000'),
                'max_investment': Decimal('100000000'),
                'min_tenure_days': 364,
                'max_tenure_days': 364,
                'default_tenure_days': 364,
                'interest_rate': Decimal('12.50'),
                'interest_frequency': 'AT_MATURITY',
                'management_fee': Decimal('0.00'),
                'early_withdrawal_fee': Decimal('10.00'),
                'is_active': True,
                'is_available': True,
                'available_from': timezone.now(),
            },
        ]
        
        for product_data in products:
            InvestmentProduct.objects.get_or_create(
                slug=product_data['slug'],
                defaults=product_data
            )
        
        self.stdout.write('Investment products created')