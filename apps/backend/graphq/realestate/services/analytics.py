class CMAReport:
    def __init__(self, subject_property):
        self.subject = subject_property
    
    def generate(self):
        comparables = self._find_comparables()
        adjustments = self._calculate_adjustments(comparables)
        valuation = self._calculate_valuation(comparables, adjustments)
        
        return {
            'subject_property': self._property_data(self.subject),
            'comparables': [self._property_data(p) for p in comparables],
            'adjustments': adjustments,
            'valuation_range': valuation
        }
    
    def _find_comparables(self):
        """Find similar properties sold recently in the area"""
        from datetime import timedelta

        from django.contrib.gis.db.models.functions import Distance
        
        return Listing.objects.filter(
            address__location__distance_lte=(
                self.subject.address.location,
                D(km=1.5)  # 1.5km radius
            ),
            property_status='sold',
            sold_date__gte=timezone.now() - timedelta(days=90),
            listing_type=self.subject.listing_type,
            square_feet__range=(
                self.subject.square_feet * 0.8,
                self.subject.square_feet * 1.2
            )
        ).annotate(
            distance=Distance('address__location', self.subject.address.location)
        ).order_by('sold_date')[:5]
    
    def _calculate_adjustments(self, comparables):
        """Calculate value adjustments for differences"""
        adjustments = []
        for comp in comparables:
            adj = {
                'property_id': comp.id,
                'price_per_sqft': comp.price / comp.square_feet,
                'adjustments': {}
            }
            
            # Square footage adjustment
            sqft_diff = self.subject.square_feet - comp.square_feet
            adj['adjustments']['square_feet'] = sqft_diff * adj['price_per_sqft']
            
            # Add more adjustments (age, condition, amenities, etc.)
            # ...
            
            adjustments.append(adj)
        return adjustments
    
    def _calculate_valuation(self, comparables, adjustments):
        """Calculate estimated value range"""
        adjusted_values = []
        for comp, adj in zip(comparables, adjustments):
            total_adjustment = sum(adj['adjustments'].values())
            adjusted_values.append(comp.price + total_adjustment)
        
        if not adjusted_values:
            return None
            
        return {
            'low': min(adjusted_values),
            'high': max(adjusted_values),
            'avg': sum(adjusted_values) / len(adjusted_values)
        }
        