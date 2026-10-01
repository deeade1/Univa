# settings/databases.py - FIXED VERSION
import os
import json
from django.conf import settings
from django.db import connections
import boto3
from botocore.config import Config
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """Environment-specific configuration"""
    
    @staticmethod
    def get_database_config(environment=None):
        """Get database configuration for environment"""
        env = environment or os.getenv('DJANGO_ENV', 'development')
        
        configs = {
            'development': DevelopmentConfig(),
            'staging': StagingConfig(),
            'production': ProductionConfig(),
        }
        
        return configs.get(env, configs['development'])

class BaseDatabaseConfig:
    """Base database configuration"""
    
    def get_common_options(self):
        return {
            'connect_timeout': 10,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'options': '-c statement_timeout=30000',  # 30 second timeout
        }
    
    def get_analytics_options(self):
        return {
            'connect_timeout': 30,
            'options': '-c statement_timeout=300000',  # 5 minute timeout for analytics
            'application_name': 'saleor_analytics',
        }

class ProductionConfig(BaseDatabaseConfig):
    """Production database configuration"""
    
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.use_rds_proxy = os.getenv('USE_RDS_PROXY', 'false').lower() == 'true'
        
    def get_primary_config(self):
        """Primary write database configuration"""
        if self.use_rds_proxy:
            host = os.getenv('DB_PROXY_ENDPOINT', 'db-proxy.proxy-xyz.us-east-1.rds.amazonaws.com')
        else:
            host = os.getenv('DB_HOST_PRIMARY', 'db-primary.us-east-1.rds.amazonaws.com')
        
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'saleor_primary'),
            'USER': os.getenv('DB_USER', 'saleor'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': host,
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                **self.get_common_options(),
                'application_name': 'saleor_primary_write',
            },
            'CONN_MAX_AGE': 300,  # 5 minutes
            'CONN_HEALTH_CHECKS': True,
            'ATOMIC_REQUESTS': False,  # Disable for performance
        }
    
    def get_read_replica_config(self, replica_num: int = 1):
        """Read replica configuration"""
        host_env = f'DB_HOST_REPLICA_{replica_num}'
        host = os.getenv(host_env, f'db-replica-{replica_num}.us-east-1.rds.amazonaws.com')
        
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'saleor_primary'),
            'USER': os.getenv('DB_USER', 'saleor'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': host,
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                **self.get_common_options(),
                'application_name': f'saleor_replica_{replica_num}',
            },
            'CONN_MAX_AGE': 300,
            'TEST': {'MIRROR': 'default'},
        }
    
    def get_analytics_config(self):
        """Analytics database configuration"""
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'saleor_primary'),
            'USER': os.getenv('DB_USER_ANALYTICS', 'saleor_analytics'),
            'PASSWORD': os.getenv('DB_PASSWORD_ANALYTICS', ''),
            'HOST': os.getenv('DB_HOST_ANALYTICS', 'db-analytics.us-east-1.rds.amazonaws.com'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': self.get_analytics_options(),
            'CONN_MAX_AGE': 60,  # 1 minute for analytics (shorter connections)
        }

# ----------------------------
# DATABASE ROUTING (IMPROVED)
# ----------------------------
class SmartDatabaseRouter:
    """
    Intelligent database routing with:
    1. Region-aware routing
    2. Load balancing
    3. Query analysis for optimal routing
    4. Failover support
    """
    
    def __init__(self):
        self.region_mapping = self._load_region_mapping()
        self.replica_weights = self._initialize_replica_weights()
        self.query_analytics = {}
        
    def _load_region_mapping(self):
        """Load region mapping from configuration"""
        return {
            'us-east-1': 'default',
            'eu-west-1': 'europe',
            'ap-southeast-1': 'asia',
        }
    
    def _initialize_replica_weights(self):
        """Initialize replica weights for load balancing"""
        return {
            'default': {'default_replica_1': 1.0, 'default_replica_2': 1.0},
            'europe': {'europe_replica_1': 1.0},
            'asia': {'asia_replica_1': 1.0},
        }
    
    def db_for_read(self, model, **hints):
        """
        Route read queries intelligently
        """
        # Extract routing hints
        region = hints.get('region')
        force_primary = hints.get('force_primary', False)
        analytics_query = hints.get('analytics', False)
        query_complexity = hints.get('query_complexity', 'medium')
        
        # Force primary for writes or complex transactions
        if force_primary:
            return self._get_primary_for_region(region)
        
        # Analytics queries go to analytics replica
        if analytics_query:
            return self._get_analytics_db(region)
        
        # Get appropriate region
        if not region:
            region = self._get_request_region()
        
        # Route to appropriate replica with load balancing
        return self._select_replica(region, query_complexity)
    
    def db_for_write(self, model, **hints):
        """
        Route write queries
        """
        region = hints.get('region')
        
        # Region-specific writes
        if hasattr(model, '_region_specific'):
            return self._get_primary_for_region(region or self._get_request_region())
        
        # All writes go to primary region
        return 'default'
    
    def _get_primary_for_region(self, region):
        """Get primary database for region"""
        return self.region_mapping.get(region, 'default')
    
    def _get_analytics_db(self, region):
        """Get analytics database"""
        primary = self._get_primary_for_region(region)
        return f"{primary}_analytics"
    
    def _select_replica(self, region, query_complexity):
        """Select replica with load balancing and query awareness"""
        primary = self._get_primary_for_region(region)
        
        if primary not in self.replica_weights:
            return f"{primary}_replica_1"  # Default
        
        replicas = list(self.replica_weights[primary].keys())
        
        if not replicas:
            return primary  # Fallback to primary
        
        # Simple weighted random selection
        import random
        weights = list(self.replica_weights[primary].values())
        selected = random.choices(replicas, weights=weights, k=1)[0]
        
        # Update weights based on query complexity
        self._adjust_weights(primary, selected, query_complexity)
        
        return selected
    
    def _adjust_weights(self, primary, selected_replica, query_complexity):
        """Adjust replica weights based on query complexity"""
        # Simple weight adjustment - in production, use more sophisticated logic
        if query_complexity == 'high':
            # Reduce weight for heavy queries
            self.replica_weights[primary][selected_replica] *= 0.9
        elif query_complexity == 'low':
            # Increase weight for light queries
            self.replica_weights[primary][selected_replica] = min(
                2.0, self.replica_weights[primary][selected_replica] * 1.1
            )
    
    def _get_request_region(self):
        """Determine region from request"""
        # This would typically come from request middleware
        # For now, use environment variable or default
        return os.getenv('AWS_REGION', 'us-east-1')

# ----------------------------
# CONNECTION POOLING (IMPROVED)
# ----------------------------
class DatabaseConnectionManager:
    """
    Advanced connection management with:
    1. Connection pooling
    2. Health monitoring
    3. Automatic failover
    4. Connection warming
    """
    
    def __init__(self):
        self.pools = {}
        self.health_monitor = DatabaseHealthMonitor()
        self.failover_manager = FailoverManager()
        
    @contextmanager
    def get_connection(self, db_alias, read_only=False, timeout=30):
        """
        Get database connection with context management
        """
        connection = None
        
        try:
            # Get connection from pool
            connection = self._acquire_connection(db_alias, read_only, timeout)
            
            # Verify connection is healthy
            if not self.health_monitor.check_connection(connection):
                raise ConnectionError(f"Unhealthy connection for {db_alias}")
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error for {db_alias}: {e}")
            
            # Mark connection as unhealthy
            if connection:
                self.health_monitor.mark_unhealthy(db_alias, str(e))
            
            # Try failover if available
            if read_only and self.failover_manager.has_failover(db_alias):
                failover_alias = self.failover_manager.get_failover_target(db_alias)
                logger.info(f"Failing over from {db_alias} to {failover_alias}")
                
                # Retry with failover
                with self.get_connection(failover_alias, read_only, timeout) as failover_conn:
                    yield failover_conn
            else:
                raise
            
        finally:
            if connection:
                self._release_connection(db_alias, connection)
    
    def _acquire_connection(self, db_alias, read_only, timeout):
        """Acquire connection from pool"""
        if db_alias not in self.pools:
            self._initialize_pool(db_alias)
        
        pool = self.pools[db_alias]
        
        # For read-only, try to use read replica pool if available
        if read_only and f"{db_alias}_read_pool" in self.pools:
            pool = self.pools[f"{db_alias}_read_pool"]
        
        return pool.getconn(timeout=timeout)
    
    def _release_connection(self, db_alias, connection):
        """Release connection back to pool"""
        if db_alias in self.pools:
            pool = self.pools[db_alias]
            pool.putconn(connection)
    
    def _initialize_pool(self, db_alias):
        """Initialize connection pool for database"""
        db_config = DATABASES[db_alias]
        
        pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=db_config['HOST'],
            database=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            port=db_config['PORT'],
            **db_config.get('OPTIONS', {})
        )
        
        self.pools[db_alias] = pool
        
        # Start health monitoring for this pool
        self.health_monitor.monitor_pool(db_alias, pool)
        
        logger.info(f"Initialized connection pool for {db_alias}")
    
    def warmup_pools(self, aliases=None):
        """Warm up connection pools"""
        if aliases is None:
            aliases = list(DATABASES.keys())
        
        for alias in aliases:
            if alias not in self.pools:
                self._initialize_pool(alias)
            
            # Create a few connections to warm up the pool
            connections = []
            try:
                for _ in range(min(5, 20)):  # Warm up 5 connections
                    conn = self._acquire_connection(alias, read_only=False, timeout=5)
                    connections.append(conn)
                
                logger.info(f"Warmed up pool for {alias} with {len(connections)} connections")
                
            finally:
                for conn in connections:
                    self._release_connection(alias, conn)

# ----------------------------
# DATABASE HEALTH MONITORING
# ----------------------------
class DatabaseHealthMonitor:
    """Monitor database health and performance"""
    
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.health_status = {}
        self.unhealthy_since = {}
        
    def monitor_pool(self, db_alias, pool):
        """Start monitoring a connection pool"""
        import threading
        
        def monitor():
            while True:
                try:
                    self._check_pool_health(db_alias, pool)
                    time.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Health monitor error for {db_alias}: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _check_pool_health(self, db_alias, pool):
        """Check health of connection pool"""
        try:
            # Try to get and return a connection
            conn = pool.getconn(timeout=5)
            
            # Run simple health check query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            
            # Return connection
            pool.putconn(conn)
            
            # Update health status
            self.health_status[db_alias] = {
                'status': 'healthy',
                'last_check': time.time(),
                'connection_count': len(pool._used) + len(pool._idle),
            }
            
            # Clear unhealthy marker if previously unhealthy
            if db_alias in self.unhealthy_since:
                del self.unhealthy_since[db_alias]
            
        except Exception as e:
            logger.error(f"Health check failed for {db_alias}: {e}")
            
            self.health_status[db_alias] = {
                'status': 'unhealthy',
                'last_check': time.time(),
                'error': str(e),
            }
            
            # Track how long it's been unhealthy
            if db_alias not in self.unhealthy_since:
                self.unhealthy_since[db_alias] = time.time()
    
    def check_connection(self, connection):
        """Check if connection is healthy"""
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except:
            return False
    
    def mark_unhealthy(self, db_alias, reason):
        """Mark database as unhealthy"""
        self.health_status[db_alias] = {
            'status': 'unhealthy',
            'last_check': time.time(),
            'error': reason,
        }
        
        if db_alias not in self.unhealthy_since:
            self.unhealthy_since[db_alias] = time.time()
    
    def get_health_report(self):
        """Get comprehensive health report"""
        report = {
            'timestamp': time.time(),
            'databases': self.health_status,
            'unhealthy_durations': {
                alias: time.time() - since
                for alias, since in self.unhealthy_since.items()
            }
        }
        
        return report

# ----------------------------
# CONFIGURATION LOADING
# ----------------------------
def load_database_config():
    """Load database configuration based on environment"""
    env_config = EnvironmentConfig.get_database_config()
    
    # Build DATABASES dictionary
    databases = {
        'default': env_config.get_primary_config(),
    }
    
    # Add read replicas
    for i in range(1, 3):  # Add replica_1 and replica_2
        try:
            databases[f'default_replica_{i}'] = env_config.get_read_replica_config(i)
        except Exception as e:
            logger.warning(f"Failed to configure replica {i}: {e}")
    
    # Add analytics database
    try:
        databases['default_analytics'] = env_config.get_analytics_config()
    except Exception as e:
        logger.warning(f"Failed to configure analytics database: {e}")
    
    return databases

# Load configuration
DATABASES = load_database_config()
DATABASE_ROUTERS = ['core.database.SmartDatabaseRouter']

# Initialize connection manager
db_connection_manager = DatabaseConnectionManager()

# ----------------------------
# MIDDLEWARE FOR DATABASE ROUTING
# ----------------------------
class DatabaseRoutingMiddleware:
    """
    Middleware to set database routing hints based on request
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract region from request (e.g., from header, IP, or domain)
        region = self._extract_region_from_request(request)
        
        # Set thread-local variable for database router
        import threading
        thread_local = threading.local()
        thread_local.current_region = region
        
        # Add database hints to request
        request.db_hints = {
            'region': region,
            'force_primary': request.method in ['POST', 'PUT', 'DELETE', 'PATCH'],
            'analytics': request.path.startswith('/api/analytics/'),
        }
        
        response = self.get_response(request)
        
        return response
    
    def _extract_region_from_request(self, request):
        """Extract region from request"""
        # Check X-Region header
        region = request.headers.get('X-Region')
        if region:
            return region
        
        # Check domain
        host = request.get_host()
        if 'eu.' in host:
            return 'eu-west-1'
        elif 'ap.' in host:
            return 'ap-southeast-1'
        
        # Default to primary region
        return os.getenv('AWS_REGION', 'us-east-1')