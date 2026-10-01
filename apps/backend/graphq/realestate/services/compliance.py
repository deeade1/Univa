# compliance.py
class ComplianceChecker:
    def check_listing(self, listing):
        """Check if listing meets all regulatory requirements"""
        issues = []
        
        # Check required fields
        if not listing.address:
            issues.append('Missing address')
        if not listing.price:
            issues.append('Missing price')
        
        # Check fair housing compliance
        if any(word in listing.description.lower() for word in self._protected_terms()):
            issues.append('Potential fair housing violation in description')
        
        # State-specific requirements
        if listing.address.state == 'NY':
            if not hasattr(listing, 'lead_paint_disclosure'):
                issues.append('Missing NY lead paint disclosure')
        
        return issues
    
    def _protected_terms(self):
        return [
            'religion', 'race', 'color', 'national origin',
            'familial status', 'disability', 'sex'
        ]
        
        
