"""
Monitoring and metrics collection for Master backend
Simple metrics tracking for small-scale deployments (Agent < 50)
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, deque
import logging
from pathlib import Path

# Metrics storage (in-memory for simplicity)
request_counts: Dict[str, int] = defaultdict(int)  # endpoint -> count
response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))  # endpoint -> response times
error_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # endpoint -> {status_code: count}
total_requests: int = 0
start_time: datetime = datetime.now()

logger = logging.getLogger(__name__)


# Note: Metrics collection is handled in main.py RequestLoggingMiddleware
# This module provides utility functions to read and aggregate metrics


def get_metrics_summary() -> Dict:
    """Get current metrics summary"""
    collected = get_collected_metrics()
    
    request_counts = collected['request_counts']
    response_times = {k: v for k, v in collected['response_times'].items()}
    error_counts = collected['error_counts']
    total_requests = collected['total_requests']
    start_time_obj = collected['start_time']
    
    uptime = (datetime.now() - start_time_obj).total_seconds()
    
    summary = {
        "uptime_seconds": uptime,
        "total_requests": total_requests,
        "requests_per_second": total_requests / uptime if uptime > 0 else 0,
        "endpoints": {}
    }
    
    for endpoint, count in request_counts.items():
        times = response_times.get(endpoint, [])
        
        if not times:
            continue
        
        sorted_times = sorted(times)
        p50_idx = int(len(sorted_times) * 0.5)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        summary["endpoints"][endpoint] = {
            "request_count": count,
            "rps": count / uptime if uptime > 0 else 0,
            "response_time_ms": {
                "mean": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "p50": sorted_times[p50_idx] if p50_idx < len(sorted_times) else sorted_times[-1],
                "p95": sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1],
                "p99": sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1],
            },
            "errors": error_counts.get(endpoint, {}),
            "error_rate": sum(error_counts.get(endpoint, {}).values()) / count if count > 0 else 0
        }
    
    return summary


def get_pending_deployment_metrics() -> Dict:
    """Get specific metrics for /api/deployments/pending/{agent_id} endpoint"""
    from collections import defaultdict
    
    endpoint_pattern = "GET /api/deployments/pending/"
    
    metrics = {
        "total_requests": 0,
        "rps": 0,
        "response_time_ms": {
            "mean": 0,
            "p50": 0,
            "p95": 0,
            "p99": 0
        },
        "errors": {},
        "error_rate": 0
    }
    
    collected = get_collected_metrics()
    request_counts = collected['request_counts']
    response_times = collected['response_times']
    error_counts = collected['error_counts']
    start_time_obj = collected['start_time']
    
    # Aggregate all pending deployment endpoint requests
    pending_endpoints = [ep for ep in request_counts.keys() if endpoint_pattern in ep]
    
    if not pending_endpoints:
        return metrics
    
    total_count = sum(request_counts[ep] for ep in pending_endpoints)
    all_times = []
    all_errors = defaultdict(int)
    
    for ep in pending_endpoints:
        times = response_times.get(ep, [])
        all_times.extend(times)
        for status, count in error_counts.get(ep, {}).items():
            all_errors[status] += count
    
    if not all_times:
        return metrics
    
    uptime = (datetime.now() - start_time_obj).total_seconds()
    sorted_times = sorted(all_times)
    p50_idx = int(len(sorted_times) * 0.5)
    p95_idx = int(len(sorted_times) * 0.95)
    p99_idx = int(len(sorted_times) * 0.99)
    
    metrics["total_requests"] = total_count
    metrics["rps"] = total_count / uptime if uptime > 0 else 0
    metrics["response_time_ms"] = {
        "mean": sum(all_times) / len(all_times),
        "p50": sorted_times[p50_idx] if p50_idx < len(sorted_times) else sorted_times[-1],
        "p95": sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1],
        "p99": sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1],
    }
    metrics["errors"] = dict(all_errors)
    metrics["error_rate"] = sum(all_errors.values()) / total_count if total_count > 0 else 0
    
    return metrics
