"""Unit tests for configuration loading and validation."""

from src.config.settings import Settings, get_settings


def test_default_settings_instantiation():
    """Verify default settings instantiate with expected baseline values."""
    settings = get_settings()
    assert settings.app_name == "Real-Time Demand & Risk Intelligence Engine"
    assert settings.environment == "development"
    assert settings.random_seed == 42
    assert settings.default_service_level == 0.95
    assert settings.default_lead_time_days == 7
    assert settings.forecast_horizon_days == 14
    assert "sqlite" in settings.database_url


def test_settings_custom_override():
    """Verify settings can be initialized with custom valid configurations."""
    custom = Settings(
        environment="testing",
        random_seed=123,
        default_service_level=0.98,
        default_lead_time_days=10,
        forecast_horizon_days=30,
    )
    assert custom.environment == "testing"
    assert custom.random_seed == 123
    assert custom.default_service_level == 0.98
    assert custom.default_lead_time_days == 10
    assert custom.forecast_horizon_days == 30


def test_settings_production_enforces_auth_default():
    """Verify that in production environment, auth_enabled automatically defaults to True."""
    prod = Settings(environment="production")
    assert prod.environment == "production"
    assert prod.auth_enabled is True
