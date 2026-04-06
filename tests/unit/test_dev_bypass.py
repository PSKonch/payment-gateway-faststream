from app.api.dependencies import _is_dev_bypass_key_id
from app.core.config import settings
from scripts.seed_data import get_seed_merchants


def test_is_dev_bypass_key_id_respects_flag(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", False)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_KEY_IDS", "devbypass001")

    assert _is_dev_bypass_key_id("devbypass001") is False


def test_is_dev_bypass_key_id_matches_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", True)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_KEY_IDS", "devbypass001, devbypass002")

    assert _is_dev_bypass_key_id("devbypass001") is True
    assert _is_dev_bypass_key_id("devbypass002") is True
    assert _is_dev_bypass_key_id("testm001") is False


def test_seed_merchants_include_dev_bypass_merchant_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", True)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_MERCHANT_NAME", "Dev Bypass Merchant")
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_BALANCE", 100000)
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_API_KEY_ID", "devbypass001")
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_SECRET", "dev-bypass-secret")

    merchants = get_seed_merchants()
    assert any(m.api_key_prefix == "devbypass001" for m in merchants)


def test_seed_merchants_do_not_include_dev_bypass_merchant_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", False)

    merchants = get_seed_merchants()
    assert all(m.api_key_prefix != "devbypass001" for m in merchants)
