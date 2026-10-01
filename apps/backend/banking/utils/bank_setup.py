class BankSetupManager:
    """Utility class for initializing banks in database"""
    
    @staticmethod
    def initialize_all_banks():
        """Initialize ALL Nigerian banks in database"""
        banks_config = [
            # Traditional Banks
            {"name": "ACCESS", "code": "044", "is_partner_bank": False},
            {"name": "ACCESS_D", "code": "063", "is_partner_bank": False},
            {"name": "CITIBANK", "code": "023", "is_partner_bank": False},
            {"name": "ECOBANK", "code": "050", "is_partner_bank": False},
            {"name": "FIDELITY", "code": "070", "is_partner_bank": False},
            {"name": "FIRSTBANK", "code": "011", "is_partner_bank": False},
            {"name": "FCMB", "code": "214", "is_partner_bank": False},
            {"name": "GTBANK", "code": "058", "is_partner_bank": False},
            {"name": "HERITAGE", "code": "030", "is_partner_bank": False},
            {"name": "KEYSTONE", "code": "082", "is_partner_bank": False},
            {"name": "POLARIS", "code": "076", "is_partner_bank": False},
            {"name": "PROVIDUS", "code": "101", "is_partner_bank": True, "virtual_account_provider": "MONNIFY", "daily_capacity": 15000},
            {"name": "STANBIC", "code": "039", "is_partner_bank": False},
            {"name": "STANDARD", "code": "068", "is_partner_bank": False},
            {"name": "STERLING", "code": "232", "is_partner_bank": False},
            {"name": "SUNTRUST", "code": "100", "is_partner_bank": False},
            {"name": "UBA", "code": "033", "is_partner_bank": False},
            {"name": "UNION", "code": "032", "is_partner_bank": False},
            {"name": "UNITY", "code": "215", "is_partner_bank": True, "virtual_account_provider": "PAYSTACK", "daily_capacity": 10000},
            {"name": "WEMA", "code": "035", "is_partner_bank": True, "virtual_account_provider": "PAYSTACK", "daily_capacity": 5000},
            {"name": "ZENITH", "code": "057", "is_partner_bank": False},
            
            # Fintechs & Digital Banks
            {"name": "KUDA", "code": "50211", "is_partner_bank": False},
            {"name": "OPAY", "code": "100004", "is_partner_bank": False},
            {"name": "PALMPAY", "code": "100033", "is_partner_bank": False},
            {"name": "MONIEPOINT", "code": "50515", "is_partner_bank": False},
            {"name": "FAIRMONEY", "code": "51318", "is_partner_bank": False},
            {"name": "CARBON", "code": "51304", "is_partner_bank": False},
            
            # Virtual Account Providers
            {"name": "PAYSTACK_WEMA", "code": "paystack-wema", "is_virtual_provider": True, "is_partner_bank": False},
            {"name": "MONNIFY_PROVIDUS", "code": "monnify-providus", "is_virtual_provider": True, "is_partner_bank": False},
            {"name": "FLUTTERWAVE_ACCESS", "code": "flutterwave-access", "is_virtual_provider": True, "is_partner_bank": False},
        ]
        
        created_count = 0
        updated_count = 0
        
        for config in banks_config:
            defaults = {
                'code': config['code'],
                'is_active': True,
                'supports_transfers': True,
                'supports_airtime': config.get('supports_airtime', False),
                'supports_bills': config.get('supports_bills', False),
                'is_partner_bank': config.get('is_partner_bank', False),
                'virtual_account_provider': config.get('virtual_account_provider', ''),
                'daily_capacity': config.get('daily_capacity', 0),
                'is_virtual_provider': config.get('is_virtual_provider', False),
            }
            
            bank, created = Bank.objects.update_or_create(
                name=config['name'],
                defaults=defaults
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return {
            'total': len(banks_config),
            'created': created_count,
            'updated': updated_count,
        }
    
    @staticmethod
    def get_partner_banks():
        """Get all active partner banks"""
        return Bank.objects.filter(
            is_active=True,
            is_partner_bank=True
        ).order_by('name')
    
    @staticmethod
    def reset_all_daily_usage():
        """Reset daily usage for all partner banks"""
        banks = Bank.objects.filter(is_partner_bank=True)
        for bank in banks:
            bank.reset_daily_usage()
        return banks.count()