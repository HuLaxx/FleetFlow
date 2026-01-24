"""
Sentry error tracking configuration.
"""

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def configure_sentry(app_name: str = "FleetFlow", environment: str = "development"):
    """Configure Sentry error tracking."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if not sentry_dsn:
        # Sentry disabled if no DSN provided
        return
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=os.getenv("APP_VERSION", "0.1.0"),
        
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=None,  # Capture all levels
                event_level=None  # Send errors as events
            ),
        ],
        
        # Performance monitoring
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        
        # Profiling
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        
        # Error sampling
        sample_rate=1.0,
        
        # Before send hook for filtering
        before_send=before_send_hook,
        
        # Tag configuration
        _experiments={
            "profiles_sample_rate": float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        },
    )


def before_send_hook(event, hint):
    """Filter events before sending to Sentry."""
    # Don't send health check errors
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None
    
    # Don't send metrics endpoint errors
    if event.get("request", {}).get("url", "").endswith("/metrics"):
        return None
    
    return event


def capture_exception(exception: Exception, context: dict = None):
    """Manually capture an exception with optional context."""
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        sentry_sdk.capture_exception(exception)


def set_user_context(user_id: str, email: str = None):
    """Set user context for error tracking."""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
    })


def set_tag(key: str, value: str):
    """Set a tag for the current scope."""
    sentry_sdk.set_tag(key, value)
