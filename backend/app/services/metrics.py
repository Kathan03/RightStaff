# backend/app/services/metrics.py
"""
Metrics collection service for observability.
Simple in-memory metrics (future: Prometheus).

Why metrics?
- Track ingestion pipeline performance (stage timings)
- Monitor success/failure rates
- Identify bottlenecks
- Enable alerting on anomalies
- Foundation for production monitoring
"""

from typing import Dict
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Simple in-memory metrics collector.
    
    Supports three metric types:
    1. Counters - Incrementing values (e.g., jobs processed, errors)
    2. Timings - Duration measurements with statistics
    3. Gauges - Point-in-time values (e.g., queue depth)
    
    Why in-memory?
    - Fast (no I/O overhead)
    - Simple to implement
    - Good for MVP
    - Can migrate to Prometheus/CloudWatch later
    
    Limitations:
    - Metrics reset on restart
    - No persistence
    - No aggregation across instances
    """
    
    def __init__(self):
        """Initialize empty metric collections."""
        self.counters = defaultdict(int)
        self.timings = defaultdict(list)
        self.gauges = {}
    
    def increment_counter(self, metric_name: str, value: int = 1):
        """
        Increment a counter metric.
        
        Use for: counting events, errors, successes.
        
        Args:
            metric_name: Counter name (e.g., "ingestion_jobs_success")
            value: Amount to increment (default: 1)
        
        Example:
            metrics_collector.increment_counter("ingestion_jobs_success")
            metrics_collector.increment_counter("bytes_processed", 1024)
        """
        self.counters[metric_name] += value
        logger.debug(f"📊 Counter {metric_name}: {self.counters[metric_name]}")
    
    def record_timing(self, metric_name: str, start_time: datetime):
        """
        Record timing from start_time to now.
        
        Automatically calculates duration and stores it.
        Statistics (avg, min, max) computed on retrieval.
        
        Args:
            metric_name: Timing metric name (e.g., "ingestion_stage_1_fetch")
            start_time: When operation started (datetime)
        
        Example:
            start = datetime.utcnow()
            # ... do work ...
            metrics_collector.record_timing("api_request", start)
        """
        duration = (datetime.utcnow() - start_time).total_seconds()
        self.timings[metric_name].append(duration)
        logger.debug(f"⏱️  Timing {metric_name}: {duration:.2f}s")
    
    def set_gauge(self, metric_name: str, value: float):
        """
        Set a gauge value.
        
        Gauges represent point-in-time measurements.
        
        Args:
            metric_name: Gauge name (e.g., "queue_depth")
            value: Current value
        
        Example:
            metrics_collector.set_gauge("queue_depth", 42)
            metrics_collector.set_gauge("cpu_usage_percent", 65.3)
        """
        self.gauges[metric_name] = value
    
    def get_metrics(self) -> Dict:
        """
        Get all metrics with timing statistics.
        
        Computes statistics for timing metrics:
        - count: Number of measurements
        - avg: Average duration
        - min: Minimum duration
        - max: Maximum duration
        
        Returns:
            Dictionary with all metrics:
            {
                "counters": {"metric_name": value, ...},
                "timings": {"metric_name": {"count": N, "avg": X, ...}, ...},
                "gauges": {"metric_name": value, ...}
            }
        """
        timing_stats = {}
        for key, values in self.timings.items():
            if values:
                timing_stats[key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return {
            "counters": dict(self.counters),
            "timings": timing_stats,
            "gauges": dict(self.gauges)
        }
    
    def reset(self):
        """
        Reset all metrics.
        
        Useful for testing or periodic resets.
        ⚠️  Use with caution in production!
        """
        self.counters.clear()
        self.timings.clear()
        self.gauges.clear()
        logger.info("🔄 Metrics reset")


# Global metrics collector instance
# Why global? Single source of truth across all modules
metrics_collector = MetricsCollector()

