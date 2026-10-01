# apps/backend/banking/management/commands/daily_reconciliation.py
from django.core.management.base import BaseCommand

from banking.services.banking_orchestrator import BankingOrchestrator


class Command(BaseCommand):
    help = 'Run daily banking reconciliation and reporting'
    
    def handle(self, *args, **options):
        orchestrator = BankingOrchestrator()
        
        self.stdout.write('Starting daily banking operations...')
        
        try:
            result = orchestrator.daily_banking_operations()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Daily operations completed: "
                    f"Reconciliation: {result['reconciliation'].status}, "
                    f"Reports: {result['regulatory_reports_generated']}"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Daily operations failed: {str(e)}')
            )
            # Alert operations team
            self._send_alert(f"Daily reconciliation failed: {str(e)}")