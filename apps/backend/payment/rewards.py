# apps/backend/payment/rewards.py

class UnivaRewards:
    def __init__(self, user):
        self.user = user
        
    def process_transaction_reward(self, transaction_amount, transaction_id):
        """Give 2% cashback for Univa payments"""
        cashback_percentage = 2  # 2% as requested
        cashback_amount = (cashback_percentage / 100) * transaction_amount
        
        # Add cashback to user's Univa wallet
        self.add_to_wallet(self.user, cashback_amount)
        
        # Log reward for user
        self.log_reward(transaction_id, cashback_amount)
        
        return {
            'cashback_earned': cashback_amount,
            'message': f'You earned {cashback_amount} cashback!'
        }