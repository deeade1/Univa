# calculators.py
class MortgageCalculator:
    def __init__(self, principal, annual_rate, years):
        self.principal = principal
        self.monthly_rate = annual_rate / 12 / 100
        self.payments = years * 12
        
    def monthly_payment(self):
        if self.monthly_rate == 0:
            return self.principal / self.payments
        return (self.principal * self.monthly_rate * 
               (1 + self.monthly_rate)**self.payments) / \
               ((1 + self.monthly_rate)**self.payments - 1)
    
    def total_interest(self):
        return (self.monthly_payment() * self.payments) - self.principal
    
    def amortization_schedule(self):
        balance = self.principal
        schedule = []
        for month in range(1, self.payments + 1):
            interest = balance * self.monthly_rate
            principal = self.monthly_payment() - interest
            balance -= principal
            schedule.append({
                'month': month,
                'payment': self.monthly_payment(),
                'principal': principal,
                'interest': interest,
                'balance': max(balance, 0)
            })
        return schedule
    
    
# calculators.py
class InvestmentROICalculator:
    def __init__(self, purchase_price, down_payment, interest_rate, loan_term,
                 monthly_rent, annual_appreciation, expenses_percent):
        self.purchase_price = purchase_price
        self.down_payment = down_payment
        self.interest_rate = interest_rate
        self.loan_term = loan_term
        self.monthly_rent = monthly_rent
        self.annual_appreciation = annual_appreciation
        self.expenses_percent = expenses_percent
        
    def calculate_roi(self, years=5):
        mortgage = MortgageCalculator(
            self.purchase_price - self.down_payment,
            self.interest_rate,
            self.loan_term
        )
        
        monthly_expenses = self.monthly_rent * (self.expenses_percent / 100)
        monthly_cash_flow = self.monthly_rent - mortgage.monthly_payment() - monthly_expenses
        
        future_value = self.purchase_price * ((1 + (self.annual_appreciation / 100)) ** years)
        equity = future_value - (mortgage.payments - years * 12) * mortgage.monthly_payment()
        
        return {
            'annual_cash_flow': monthly_cash_flow * 12,
            'total_equity': equity,
            'annualized_roi': ((equity + (monthly_cash_flow * 12 * years) - self.down_payment) / 
                              self.down_payment) / years * 100
        }