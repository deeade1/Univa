# apps/backend/banking/management/commands/setup_banks.py
from django.core.management.base import BaseCommand
from banking.utils.bank_setup import BankSetupManager

class Command(BaseCommand):
    help = 'Initialize all Nigerian banks in database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-usage',
            action='store_true',
            help='Reset daily usage counters for all partner banks',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Initializing Nigerian banks...')
        
        # Initialize banks
        result = BankSetupManager.initialize_all_banks()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully initialized {result["total"]} banks: '
            f'{result["created"]} created, {result["updated"]} updated'
        ))
        
        # Reset daily usage if requested
        if options['reset_usage']:
            reset_count = BankSetupManager.reset_all_daily_usage()
            self.stdout.write(self.style.SUCCESS(
                f'Reset daily usage for {reset_count} partner banks'
            ))
        
        # Show partner banks
        partner_banks = BankSetupManager.get_partner_banks()
        if partner_banks:
            self.stdout.write('\nPartner Banks for Virtual Accounts:')
            for bank in partner_banks:
                self.stdout.write(f'  • {bank.get_name_display()} ({bank.code}) - '
                                f'Provider: {bank.virtual_account_provider} - '
                                f'Capacity: {bank.daily_capacity if bank.daily_capacity > 0 else "Unlimited"}')