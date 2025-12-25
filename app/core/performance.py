"""
Performance monitoring utilities for PC Recommendation System
"""
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""

    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.max_metrics_per_endpoint = 1000

    def record_metric(self, endpoint: str, method: str, duration: float, status_code: int, additional_data: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        key = f"{method}:{endpoint}"
        metric = {
            'timestamp': time.time(),
            'duration': duration,
            'status_code': status_code,
            'endpoint': endpoint,
            'method': method,
            **(additional_data or {})
        }

        if key not in self.metrics:
            self.metrics[key] = []

        self.metrics[key].append(metric)

        # Keep only recent metrics
        if len(self.metrics[key]) > self.max_metrics_per_endpoint:
            self.metrics[key] = self.metrics[key][-self.max_metrics_per_endpoint:]

        # Log slow requests
        if duration > 5.0:  # Log requests taking more than 5 seconds
            logger.warning(f"Slow request: {method} {endpoint} took {duration:.2f}s")

    def get_metrics_summary(self, endpoint: Optional[str] = None, method: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics summary"""
        summaries = {}

        for key, metrics in self.metrics.items():
            if not metrics:
                continue

            key_method, key_endpoint = key.split(':', 1)

            # Filter by endpoint/method if specified
            if endpoint and key_endpoint != endpoint:
                continue
            if method and key_method != method:
                continue

            durations = [m['duration'] for m in metrics]
            status_codes = [m['status_code'] for m in metrics]

            summaries[key] = {
                'endpoint': key_endpoint,
                'method': key_method,
                'total_requests': len(metrics),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
                'p99_duration': sorted(durations)[int(len(durations) * 0.99)],
                'success_rate': (sum(1 for code in status_codes if 200 <= code < 300) / len(status_codes)) * 100,
                'error_rate': (sum(1 for code in status_codes if code >= 400) / len(status_codes)) * 100,
                'last_updated': max(m['timestamp'] for m in metrics)
            }

        return summaries

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get overall health metrics"""
        all_metrics = self.get_metrics_summary()

        if not all_metrics:
            return {
                'status': 'unknown',
                'total_requests': 0,
                'avg_response_time': 0,
                'error_rate': 0
            }

        total_requests = sum(m['total_requests'] for m in all_metrics.values())
        total_duration = sum(m['avg_duration'] * m['total_requests'] for m in all_metrics.values())
        total_errors = sum(m['error_rate'] * m['total_requests'] / 100 for m in all_metrics.values())

        avg_response_time = total_duration / total_requests if total_requests > 0 else 0
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0

        # Determine health status
        if error_rate > 10 or avg_response_time > 10:
            status = 'critical'
        elif error_rate > 5 or avg_response_time > 5:
            status = 'warning'
        else:
            status = 'healthy'

        return {
            'status': status,
            'total_requests': total_requests,
            'avg_response_time': avg_response_time,
            'error_rate': error_rate,
            'endpoints_monitored': len(all_metrics)
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics for health checks"""
        health_metrics = self.get_health_metrics()
        current_time = time.time()

        # Calculate requests per second (rough estimate based on recent activity)
        recent_metrics = []
        for metrics_list in self.metrics.values():
            recent_metrics.extend([
                m for m in metrics_list
                if current_time - m['timestamp'] < 60  # Last minute
            ])

        requests_per_second = len(recent_metrics) / 60 if recent_metrics else 0

        return {
            'total_requests': health_metrics['total_requests'],
            'avg_response_time': health_metrics['avg_response_time'],
            'error_rate': health_metrics['error_rate'],
            'requests_per_second': requests_per_second,
            'endpoints_monitored': health_metrics['endpoints_monitored'],
            'status': health_metrics['status']
        }


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance"""

    def __init__(self, app, monitor: PerformanceMonitor):
        super().__init__(app)
        self.monitor = monitor

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Record performance metric
            self.monitor.record_metric(
                endpoint=request.url.path,
                method=request.method,
                duration=process_time,
                status_code=response.status_code,
                additional_data={
                    'user_agent': request.headers.get('user-agent', ''),
                    'content_length': response.headers.get('content-length', 0),
                    'query_params_count': len(request.query_params)
                }
            )

            # Add performance header
            response.headers['X-Response-Time'] = f"{process_time:.3f}s"

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # Record error metric
            self.monitor.record_metric(
                endpoint=request.url.path,
                method=request.method,
                duration=process_time,
                status_code=500,
                additional_data={
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            )

            raise


def timed(func: Callable) -> Callable:
    """Decorator to time function execution"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.debug(f"Function {func.__name__} executed in {execution_time:.3f}s")

            # Log slow functions
            if execution_time > 2.0:
                logger.warning(f"Slow function: {func.__name__} took {execution_time:.3f}s")

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper


def optimize_query(func: Callable) -> Callable:
    """Decorator to optimize database queries"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        # Execute function
        result = await func(*args, **kwargs)

        execution_time = time.time() - start_time

        # Log query performance
        if hasattr(result, '__len__') and callable(getattr(result, '__len__', None)):
            result_count = len(result)
            logger.debug(f"Query {func.__name__} returned {result_count} results in {execution_time:.3f}s")

            # Warn about potentially slow queries
            if execution_time > 1.0 and result_count > 100:
                logger.warning(f"Potentially slow query: {func.__name__} returned {result_count} results in {execution_time:.3f}s")

        return result

    return wrapper


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
