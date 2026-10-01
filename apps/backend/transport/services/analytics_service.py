# services/analytics.py
"""
Analytics service for transport data - Consolidated from analytics_service.py.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from django.db.models import Avg, Count, Sum, Q, F, Value, Case, When
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, TruncWeek
from django.utils import timezone

from .base import BaseService

logger = logging.getLogger(__name__)


class AnalyticsService(BaseService):
    """Service for transport analytics and reporting."""
    
    def __init__(self):
        super().__init__(config_prefix='analytics')
        self._metrics_cache = {}
    
    def initialize(self) -> bool:
        """Initialize analytics service."""
        try:
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AnalyticsService: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {'initialized': self._initialized}
    
    # ============================================================
    # Trip Analytics
    # ============================================================
    
    def get_trip_stats(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None, 
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get trip statistics.
        
        Args:
            start_date: Start date for stats
            end_date: End date for stats
            service_type: Optional service type filter
        
        Returns:
            dict: Trip statistics
        """
        from transport.models import ServiceRequest
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        queryset = ServiceRequest.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        total = queryset.count()
        completed = queryset.filter(status='completed')
        cancelled = queryset.filter(status='cancelled')
        in_progress = queryset.filter(status='in_progress')
        
        return {
            'total_trips': total,
            'completed': completed.count(),
            'cancelled': cancelled.count(),
            'in_progress': in_progress.count(),
            'completion_rate': (completed.count() / total * 100) if total > 0 else 0,
            'cancellation_rate': (cancelled.count() / total * 100) if total > 0 else 0,
            'by_service_type': dict(
                queryset.values('service_type').annotate(count=Count('id'))
                .values_list('service_type', 'count')
            ),
            'by_status': dict(
                queryset.values('status').annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            'total_revenue': completed.aggregate(total=Sum('total_fare'))['total'] or 0,
            'average_fare': completed.aggregate(avg=Avg('total_fare'))['avg'] or 0,
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days,
            }
        }
    
    def get_provider_stats(self, provider_id: int) -> Dict[str, Any]:
        """
        Get provider statistics.
        
        Args:
            provider_id: Provider ID
        
        Returns:
            dict: Provider statistics
        """
        from transport.models import ServiceRequest
        
        queryset = ServiceRequest.objects.filter(provider_id=provider_id)
        
        total = queryset.count()
        completed = queryset.filter(status='completed')
        cancelled = queryset.filter(status='cancelled')
        
        return {
            'total_services': total,
            'completed': completed.count(),
            'cancelled': cancelled.count(),
            'completion_rate': (completed.count() / total * 100) if total > 0 else 0,
            'cancellation_rate': (cancelled.count() / total * 100) if total > 0 else 0,
            'total_earnings': completed.aggregate(total=Sum('total_fare'))['total'] or 0,
            'average_earnings_per_trip': completed.aggregate(avg=Avg('total_fare'))['avg'] or 0,
            'average_rating_given': completed.filter(
                provider_rating__isnull=False
            ).aggregate(avg=Avg('provider_rating'))['avg'] or 0,
            'average_rating_received': completed.filter(
                customer_rating__isnull=False
            ).aggregate(avg=Avg('customer_rating'))['avg'] or 0,
            'total_distance_km': completed.aggregate(total=Sum('estimated_distance'))['total'] or 0,
            'total_duration_hours': completed.aggregate(total=Sum('estimated_duration'))['total'] or 0,
            'services_by_type': dict(
                queryset.values('service_type').annotate(count=Count('id'))
                .values_list('service_type', 'count')
            ),
            'weekly_trend': self._get_weekly_trend(queryset),
            'peak_hours': self._get_peak_hours(queryset),
        }
    
    def get_customer_stats(self, customer_id: int) -> Dict[str, Any]:
        """
        Get customer statistics.
        
        Args:
            customer_id: Customer ID
        
        Returns:
            dict: Customer statistics
        """
        from transport.models import ServiceRequest
        
        queryset = ServiceRequest.objects.filter(customer_id=customer_id)
        
        total = queryset.count()
        completed = queryset.filter(status='completed')
        cancelled = queryset.filter(status='cancelled')
        
        return {
            'total_rides': total,
            'completed': completed.count(),
            'cancelled': cancelled.count(),
            'completion_rate': (completed.count() / total * 100) if total > 0 else 0,
            'cancellation_rate': (cancelled.count() / total * 100) if total > 0 else 0,
            'total_spent': completed.aggregate(total=Sum('total_fare'))['total'] or 0,
            'average_spent_per_trip': completed.aggregate(avg=Avg('total_fare'))['avg'] or 0,
            'average_rating_given': completed.filter(
                customer_rating__isnull=False
            ).aggregate(avg=Avg('customer_rating'))['avg'] or 0,
            'average_rating_received': completed.filter(
                provider_rating__isnull=False
            ).aggregate(avg=Avg('provider_rating'))['avg'] or 0,
            'total_distance_km': completed.aggregate(total=Sum('estimated_distance'))['total'] or 0,
            'total_duration_hours': completed.aggregate(total=Sum('estimated_duration'))['total'] or 0,
            'services_by_type': dict(
                queryset.values('service_type').annotate(count=Count('id'))
                .values_list('service_type', 'count')
            ),
            'preferred_times': self._get_preferred_times(queryset),
        }
    
    def get_vehicle_stats(self, vehicle_id: int) -> Dict[str, Any]:
        """
        Get vehicle statistics.
        
        Args:
            vehicle_id: Vehicle ID
        
        Returns:
            dict: Vehicle statistics
        """
        from transport.models import ServiceRequest, Vehicle
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            return {'error': 'Vehicle not found'}
        
        queryset = ServiceRequest.objects.filter(vehicle_id=vehicle_id)
        
        total = queryset.count()
        completed = queryset.filter(status='completed')
        
        return {
            'vehicle_id': vehicle_id,
            'vehicle_name': str(vehicle),
            'total_trips': total,
            'completed_trips': completed.count(),
            'utilization_rate': (total / 30) * 100 if total > 0 else 0,  # Assuming 30 trips max/day
            'total_distance_km': completed.aggregate(total=Sum('estimated_distance'))['total'] or 0,
            'total_duration_hours': completed.aggregate(total=Sum('estimated_duration'))['total'] or 0,
            'total_revenue': completed.aggregate(total=Sum('total_fare'))['total'] or 0,
            'average_rating': completed.filter(
                provider_rating__isnull=False
            ).aggregate(avg=Avg('provider_rating'))['avg'] or 0,
        }
    
    def get_route_stats(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for specific routes.
        
        Args:
            origin: Origin city/address
            destination: Destination city/address
            start_date: Start date
            end_date: End date
        
        Returns:
            dict: Route statistics
        """
        from transport.models import ServiceRequest
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        queryset = ServiceRequest.objects.filter(
            status='completed',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if origin:
            queryset = queryset.filter(
                Q(pickup_address__icontains=origin) |
                Q(departure_city__icontains=origin)
            )
        
        if destination:
            queryset = queryset.filter(
                Q(dropoff_address__icontains=destination) |
                Q(destination_city__icontains=destination)
            )
        
        total = queryset.count()
        
        if total == 0:
            return {'total_trips': 0}
        
        return {
            'total_trips': total,
            'total_revenue': queryset.aggregate(total=Sum('total_fare'))['total'] or 0,
            'average_fare': queryset.aggregate(avg=Avg('total_fare'))['avg'] or 0,
            'average_distance_km': queryset.aggregate(avg=Avg('estimated_distance'))['avg'] or 0,
            'average_duration_minutes': queryset.aggregate(avg=Avg('estimated_duration'))['avg'] or 0,
            'most_common_time': self._get_most_common_time(queryset),
            'peak_days': self._get_peak_days(queryset),
            'origin': origin,
            'destination': destination,
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days,
            }
        }
    
    # ============================================================
    # Time Series Analytics
    # ============================================================
    
    def get_daily_trends(
        self,
        days: int = 30,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily trends for trips.
        
        Args:
            days: Number of days to analyze
            service_type: Optional service type filter
        
        Returns:
            dict: Daily trends
        """
        from transport.models import ServiceRequest
        
        start_date = timezone.now() - timedelta(days=days)
        
        queryset = ServiceRequest.objects.filter(
            created_at__gte=start_date
        )
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Group by date
        daily_data = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                completed=Count(Case(When(status='completed', then=1))),
                cancelled=Count(Case(When(status='cancelled', then=1))),
                revenue=Sum('total_fare'),
                avg_fare=Avg('total_fare'),
            )
            .order_by('date')
        )
        
        # Calculate rolling averages
        data = list(daily_data)
        for i, item in enumerate(data):
            # 7-day rolling average
            start_idx = max(0, i - 7)
            window = data[start_idx:i+1]
            item['rolling_avg_trips'] = sum(d['total'] for d in window) / len(window) if window else 0
            item['rolling_avg_revenue'] = sum(d['revenue'] or 0 for d in window) / len(window) if window else 0
        
        return {
            'period_days': days,
            'data': data,
            'total_trips': sum(d['total'] for d in data),
            'total_revenue': sum(d['revenue'] or 0 for d in data),
            'average_daily_trips': sum(d['total'] for d in data) / len(data) if data else 0,
            'peak_day': max(data, key=lambda x: x['total']) if data else None,
        }
    
    def get_hourly_breakdown(
        self,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get hourly breakdown of trips.
        
        Args:
            service_type: Optional service type filter
        
        Returns:
            dict: Hourly breakdown
        """
        from transport.models import ServiceRequest
        
        queryset = ServiceRequest.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Group by hour
        hourly_data = (
            queryset
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(
                total=Count('id'),
                completed=Count(Case(When(status='completed', then=1))),
                cancelled=Count(Case(When(status='cancelled', then=1))),
                revenue=Sum('total_fare'),
            )
            .order_by('hour')
        )
        
        # Format hours
        formatted_data = []
        for item in hourly_data:
            hour = item['hour'].hour
            formatted_data.append({
                'hour': hour,
                'total': item['total'],
                'completed': item['completed'],
                'cancelled': item['cancelled'],
                'revenue': float(item['revenue'] or 0),
                'completion_rate': (item['completed'] / item['total'] * 100) if item['total'] > 0 else 0,
            })
        
        return {
            'hourly_data': formatted_data,
            'peak_hours': sorted(formatted_data, key=lambda x: x['total'], reverse=True)[:5],
            'total_trips': sum(d['total'] for d in formatted_data),
        }
    
    def get_weekly_trends(
        self,
        weeks: int = 12,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get weekly trends.
        
        Args:
            weeks: Number of weeks to analyze
            service_type: Optional service type filter
        
        Returns:
            dict: Weekly trends
        """
        from transport.models import ServiceRequest
        
        start_date = timezone.now() - timedelta(weeks=weeks)
        
        queryset = ServiceRequest.objects.filter(
            created_at__gte=start_date
        )
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Group by week
        weekly_data = (
            queryset
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(
                total=Count('id'),
                completed=Count(Case(When(status='completed', then=1))),
                cancelled=Count(Case(When(status='cancelled', then=1))),
                revenue=Sum('total_fare'),
            )
            .order_by('week')
        )
        
        # Calculate week-over-week growth
        data = list(weekly_data)
        for i, item in enumerate(data):
            if i > 0:
                prev = data[i-1]
                item['growth'] = ((item['total'] - prev['total']) / prev['total'] * 100) if prev['total'] > 0 else 0
            else:
                item['growth'] = 0
        
        return {
            'period_weeks': weeks,
            'data': data,
            'total_trips': sum(d['total'] for d in data),
            'average_weekly_trips': sum(d['total'] for d in data) / len(data) if data else 0,
            'trend': self._calculate_trend(data),
        }
    
    # ============================================================
    # Performance Analytics
    # ============================================================
    
    def get_performance_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get overall performance summary.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            dict: Performance summary
        """
        from transport.models import ServiceRequest, ServiceProviderProfile
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        queryset = ServiceRequest.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        total = queryset.count()
        completed = queryset.filter(status='completed')
        
        # Provider metrics
        providers = ServiceProviderProfile.objects.filter(is_active=True)
        avg_provider_rating = providers.aggregate(avg=Avg('rating'))['avg'] or 0
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days,
            },
            'trip_metrics': {
                'total_trips': total,
                'completed_trips': completed.count(),
                'completion_rate': (completed.count() / total * 100) if total > 0 else 0,
                'avg_trip_duration_minutes': completed.aggregate(avg=Avg('estimated_duration'))['avg'] or 0,
                'avg_trip_distance_km': completed.aggregate(avg=Avg('estimated_distance'))['avg'] or 0,
                'avg_fare': completed.aggregate(avg=Avg('total_fare'))['avg'] or 0,
                'total_revenue': completed.aggregate(total=Sum('total_fare'))['total'] or 0,
            },
            'provider_metrics': {
                'active_providers': providers.count(),
                'avg_provider_rating': avg_provider_rating,
                'avg_acceptance_rate': providers.aggregate(avg=Avg('acceptance_rate'))['avg'] or 0,
            },
            'customer_metrics': {
                'total_customers': ServiceRequest.objects.values('customer').distinct().count(),
                'avg_customer_rating': completed.filter(
                    customer_rating__isnull=False
                ).aggregate(avg=Avg('customer_rating'))['avg'] or 0,
                'repeat_customers': self._get_repeat_customer_count(start_date, end_date),
            },
        }
    
    def get_revenue_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get revenue analytics.
        
        Args:
            start_date: Start date
            end_date: End date
            service_type: Optional service type filter
        
        Returns:
            dict: Revenue analytics
        """
        from transport.models import ServiceRequest
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        queryset = ServiceRequest.objects.filter(
            status='completed',
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        total_revenue = queryset.aggregate(total=Sum('total_fare'))['total'] or 0
        total_trips = queryset.count()
        
        # Revenue by service type
        revenue_by_type = dict(
            queryset.values('service_type')
            .annotate(
                revenue=Sum('total_fare'),
                trips=Count('id')
            )
            .values_list('service_type', 'revenue', 'trips')
        )
        
        # Revenue by day
        daily_revenue = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                revenue=Sum('total_fare'),
                trips=Count('id')
            )
            .order_by('date')
        )
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days,
            },
            'total_revenue': float(total_revenue),
            'average_daily_revenue': float(total_revenue / max((end_date - start_date).days, 1)),
            'total_trips': total_trips,
            'average_fare': float(total_revenue / total_trips) if total_trips > 0 else 0,
            'revenue_by_type': {k: float(v[0]) for k, v in revenue_by_type.items()} if revenue_by_type else {},
            'trips_by_type': {k: v[1] for k, v in revenue_by_type.items()} if revenue_by_type else {},
            'daily_revenue': [
                {
                    'date': item['date'],
                    'revenue': float(item['revenue'] or 0),
                    'trips': item['trips'],
                }
                for item in daily_revenue
            ],
            'growth_rate': self._calculate_growth_rate(daily_revenue),
        }
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _get_weekly_trend(self, queryset) -> List[Dict]:
        """Get weekly trend data."""
        weekly = (
            queryset
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )
        return [
            {
                'week': item['week'].isoformat(),
                'trips': item['count'],
            }
            for item in weekly
        ][-8:]  # Last 8 weeks
    
    def _get_peak_hours(self, queryset) -> List[Dict]:
        """Get peak hours for a queryset."""
        hourly = (
            queryset
            .annotate(hour=TruncHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('-count')
        )[:5]
        
        return [
            {
                'hour': item['hour'].hour,
                'trips': item['count'],
            }
            for item in hourly
        ]
    
    def _get_preferred_times(self, queryset) -> Dict[str, Any]:
        """Get preferred times for a customer."""
        return {
            'morning': queryset.filter(created_at__hour__range=(6, 11)).count(),
            'afternoon': queryset.filter(created_at__hour__range=(12, 16)).count(),
            'evening': queryset.filter(created_at__hour__range=(17, 20)).count(),
            'night': queryset.filter(created_at__hour__range=(21, 23)).count(),
        }
    
    def _get_most_common_time(self, queryset) -> str:
        """Get the most common time of day."""
        counts = {
            'morning': queryset.filter(created_at__hour__range=(6, 11)).count(),
            'afternoon': queryset.filter(created_at__hour__range=(12, 16)).count(),
            'evening': queryset.filter(created_at__hour__range=(17, 20)).count(),
            'night': queryset.filter(created_at__hour__range=(21, 23)).count(),
        }
        return max(counts, key=counts.get) if any(counts.values()) else 'unknown'
    
    def _get_peak_days(self, queryset) -> List[Dict]:
        """Get peak days for a route."""
        daily = (
            queryset
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('-count')
        )[:3]
        
        return [
            {
                'date': item['date'],
                'trips': item['count'],
            }
            for item in daily
        ]
    
    def _get_repeat_customer_count(self, start_date: datetime, end_date: datetime) -> int:
        """Get count of repeat customers in the period."""
        from transport.models import ServiceRequest
        
        customer_trips = (
            ServiceRequest.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                status='completed'
            )
            .values('customer')
            .annotate(trip_count=Count('id'))
            .filter(trip_count__gt=1)
        )
        
        return customer_trips.count()
    
    def _calculate_trend(self, data: List[Dict]) -> str:
        """Calculate trend direction."""
        if len(data) < 2:
            return 'insufficient_data'
        
        # Compare last 3 weeks to previous 3 weeks
        recent = data[-3:] if len(data) >= 3 else data
        previous = data[-6:-3] if len(data) >= 6 else data[:len(data)//2]
        
        if not previous:
            return 'insufficient_data'
        
        recent_avg = sum(d['total'] for d in recent) / len(recent)
        previous_avg = sum(d['total'] for d in previous) / len(previous)
        
        if recent_avg > previous_avg * 1.1:
            return 'increasing'
        elif recent_avg < previous_avg * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_growth_rate(self, daily_data: List[Dict]) -> float:
        """Calculate growth rate from daily data."""
        if len(daily_data) < 2:
            return 0.0
        
        first_week = sum(d['revenue'] or 0 for d in daily_data[:7])
        last_week = sum(d['revenue'] or 0 for d in daily_data[-7:])
        
        if first_week == 0:
            return 0.0
        
        return ((last_week - first_week) / first_week) * 100
    
    # ============================================================
    # Cache Management
    # ============================================================
    
    def clear_cache(self, key_pattern: Optional[str] = None) -> None:
        """
        Clear analytics cache.
        
        Args:
            key_pattern: Optional pattern to match cache keys
        """
        if key_pattern:
            self._metrics_cache = {
                k: v for k, v in self._metrics_cache.items()
                if key_pattern not in k
            }
        else:
            self._metrics_cache.clear()
        logger.info(f"Analytics cache cleared: {key_pattern or 'all'}")
    
    def invalidate_stats(self, model_name: str, object_id: int) -> None:
        """
        Invalidate cached stats for a specific object.
        
        Args:
            model_name: Name of the model
            object_id: ID of the object
        """
        self.clear_cache(f"{model_name}:{object_id}")