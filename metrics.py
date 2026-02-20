"""
metrics.py — Datadog metrics + LLM Observability integration.
Handles all telemetry for the three Agent Watch panels.

If Datadog is not configured, falls back to local console logging
so the demo still works without a DD account during development.
"""

import os
import time
import json
import threading
from datetime import datetime

# Track whether Datadog is available
DD_ENABLED = False
_dd_api = None
_dd_api_host = None
LLMObs = None

try:
    if os.environ.get("DD_API_KEY"):
        from datadog import initialize, api as _api

        dd_site = os.environ.get("DD_SITE", "datadoghq.com")
        _dd_api_host = f"https://api.{dd_site}"

        initialize(
            api_key=os.environ.get("DD_API_KEY"),
            app_key=os.environ.get("DD_APP_KEY"),
            api_host=_dd_api_host,
        )

        _dd_api = _api
        DD_ENABLED = True
        print(f"[metrics] Datadog enabled (API → {dd_site})")

        # Optional: LLM Observability (requires ddtrace)
        try:
            from ddtrace.llmobs import LLMObs as _LLMObs
            _LLMObs.enable(
                ml_app="agent-watch",
                api_key=os.environ.get("DD_API_KEY"),
                site=dd_site,
                agentless_enabled=True,
            )
            LLMObs = _LLMObs
            print("[metrics] LLM Observability enabled")
        except ImportError:
            LLMObs = None
        except Exception as e:
            print(f"[metrics] LLM Observability init failed: {e}")
            LLMObs = None
    else:
        print("[metrics] DD_API_KEY not set — using local logging")
except ImportError as e:
    print("[metrics] Datadog packages not installed — using local logging")
    print("           Run: pip install datadog")


# ── Async metric submission via HTTP API ──

_metric_buffer = []
_buffer_lock = threading.Lock()


def _submit_metric(name: str, value: float, metric_type: str = "gauge", tags: list = None):
    """Queue a metric for async submission to Datadog HTTP API."""
    if not DD_ENABLED or not _dd_api:
        return
    point = {
        "metric": name,
        "points": [[int(time.time()), value]],
        "type": metric_type,
        "tags": tags or [],
        "host": "agent-watch",
    }
    with _buffer_lock:
        _metric_buffer.append(point)


def _flush_metrics():
    """Flush buffered metrics to Datadog via HTTP API."""
    if not DD_ENABLED or not _dd_api:
        return
    with _buffer_lock:
        if not _metric_buffer:
            return
        batch = list(_metric_buffer)
        _metric_buffer.clear()
    try:
        _dd_api.Metric.send(batch)
    except Exception as e:
        print(f"  [metrics] Datadog send failed: {e}")


def _flush_loop():
    """Background thread that flushes metrics every 10 seconds."""
    while True:
        time.sleep(10)
        _flush_metrics()


_flush_thread = threading.Thread(target=_flush_loop, daemon=True)
_flush_thread.start()


# ── Local metrics store (always active, used for demo dashboard too) ──

class LocalMetrics:
    """In-memory metrics store for when Datadog isn't available,
    and also serves the local demo dashboard."""

    def __init__(self):
        self.events = []
        self.counters = {}
        self.gauges = {}
        self.token_log = []

    def increment(self, name, value=1, tags=None):
        self.counters[name] = self.counters.get(name, 0) + value
        self._log_event("counter", name, value, tags)

    def gauge(self, name, value, tags=None):
        self.gauges[name] = value
        self._log_event("gauge", name, value, tags)

    def _log_event(self, kind, name, value, tags):
        event = {
            "time": datetime.now().isoformat(),
            "kind": kind,
            "name": name,
            "value": value,
            "tags": tags or [],
        }
        self.events.append(event)
        # Keep last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]

    def get_summary(self):
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "recent_events": self.events[-20:],
        }

    def reset(self):
        self.events.clear()
        self.counters.clear()
        self.gauges.clear()
        self.token_log.clear()


local_metrics = LocalMetrics()


# ── Unified metrics interface ──

def track_increment(name: str, tags: list = None):
    """Increment a counter metric."""
    tag_list = tags or []
    local_metrics.increment(name, tags=tag_list)
    current = local_metrics.counters.get(name, 0)
    _submit_metric(name, current, metric_type="gauge", tags=tag_list)


def track_gauge(name: str, value: float, tags: list = None):
    """Set a gauge metric."""
    tag_list = tags or []
    local_metrics.gauge(name, value, tags=tag_list)
    _submit_metric(name, value, metric_type="gauge", tags=tag_list)


# ── Panel-specific tracking functions ──

def track_behavior(compliant: bool, severity: str = "low", issues: list = None):
    """Track a behavior evaluation result."""
    tag = "compliant" if compliant else "drift_detected"
    track_increment(
        f"agent_watch.behavior.{tag}",
        tags=[f"severity:{severity}"],
    )
    if not compliant:
        track_increment(
            "agent_watch.behavior.issues",
            tags=[f"severity:{severity}"] + [f"issue:{i}" for i in (issues or [])],
        )
    print(f"  [behavior] {'✅ COMPLIANT' if compliant else f'🚨 DRIFT DETECTED ({severity})'}")
    if issues:
        for issue in issues:
            print(f"             → {issue}")


def track_security(allowed: bool, agent: str, tool: str, reason: str = ""):
    """Track a security check result."""
    status = "allowed" if allowed else "blocked"
    track_increment(
        f"agent_watch.security.{status}",
        tags=[f"agent:{agent}", f"tool:{tool}"],
    )
    icon = "✅" if allowed else "🛑"
    print(f"  [security] {icon} {status.upper()}: {agent} → {tool}")
    if reason:
        print(f"             → {reason}")


def track_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet"):
    """Track token cost for a single LLM call."""
    # Approximate costs (per 1K tokens)
    costs = {
        "claude-sonnet": {"input": 0.003, "output": 0.015},
        "claude-haiku": {"input": 0.00025, "output": 0.00125},
    }
    rates = costs.get(model, costs["claude-sonnet"])
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1000

    entry = {"time": time.time(), "cost": cost, "input": input_tokens, "output": output_tokens}
    local_metrics.token_log.append(entry)

    # Cost in last 60 seconds
    cutoff = time.time() - 60
    recent_cost = sum(e["cost"] for e in local_metrics.token_log if e["time"] > cutoff)

    track_gauge("agent_watch.cost.per_call", cost, tags=[f"model:{model}"])
    track_gauge("agent_watch.cost.last_60s", recent_cost)
    track_gauge("agent_watch.cost.total_tokens", input_tokens + output_tokens)

    print(f"  [cost] ${cost:.6f} this call | ${recent_cost:.6f} last 60s | {input_tokens}+{output_tokens} tokens")

    return {"cost": cost, "recent_cost": recent_cost, "input_tokens": input_tokens, "output_tokens": output_tokens}


def track_request(status: str, agent: str, message_preview: str):
    """Track an overall request outcome."""
    track_increment(
        f"agent_watch.request.{status.lower()}",
        tags=[f"agent:{agent}"],
    )
    icon = {"OK": "✅", "BLOCKED": "🛑", "THROTTLED": "⚠️"}.get(status, "❓")
    print(f"  [result]   {icon} {status} | agent={agent} | \"{message_preview[:60]}...\"")


def get_cost_status(threshold: float = 0.50) -> dict:
    """Check if cost threshold is exceeded."""
    cutoff = time.time() - 60
    recent_cost = sum(e["cost"] for e in local_metrics.token_log if e["time"] > cutoff)
    exceeded = recent_cost > threshold
    if exceeded:
        track_increment("agent_watch.cost.threshold_exceeded")
    return {
        "ok": not exceeded,
        "recent_cost": recent_cost,
        "threshold": threshold,
    }
