from types import SimpleNamespace
import os

import pytest

from forge_ptbr.translator.providers.argos import ArgosProvider, ProviderUnavailableError


def _fake_modules():
    package_module = SimpleNamespace(
        get_installed_packages=lambda: [SimpleNamespace(from_code="en", to_code="pb", type="translate")]
    )
    translate_module = SimpleNamespace(translate=lambda text, source, target: f"{text}:{source}->{target}")
    return package_module, translate_module


def test_argos_provider_is_lazy_and_checks_installed_en_pb_package(monkeypatch) -> None:
    calls: list[str] = []
    package_module, translate_module = _fake_modules()

    def fake_import(name: str):
        calls.append(name)
        return package_module if name == "argostranslate.package" else translate_module

    monkeypatch.setattr("importlib.import_module", fake_import)
    provider = ArgosProvider()
    assert calls == []
    assert provider.is_ready() is True
    assert provider.translate("Hello", "en", "pt-BR") == "Hello:en->pb"
    assert "argostranslate.package" in calls
    assert "argostranslate.translate" in calls


def test_argos_provider_forces_offline_safe_backend_before_import(monkeypatch) -> None:
    package_module, translate_module = _fake_modules()
    monkeypatch.setenv("ARGOS_MODEL_PROVIDER", "LIBRETRANSLATE")
    monkeypatch.setenv("ARGOS_CHUNK_TYPE", "STANZA")

    def fake_import(name: str):
        assert os.environ["ARGOS_MODEL_PROVIDER"] == "OPENNMT"
        assert os.environ["ARGOS_CHUNK_TYPE"] == "MINISBD"
        return package_module if name == "argostranslate.package" else translate_module

    monkeypatch.setattr("importlib.import_module", fake_import)
    assert ArgosProvider().is_ready() is True


def test_argos_provider_never_updates_or_downloads_package_index(monkeypatch) -> None:
    package_module = SimpleNamespace(
        get_installed_packages=lambda: [SimpleNamespace(from_code="en", to_code="pb", type="translate")],
        update_package_index=lambda: (_ for _ in ()).throw(AssertionError("network update called")),
        get_available_packages=lambda: (_ for _ in ()).throw(AssertionError("network index called")),
    )
    translate_module = SimpleNamespace(translate=lambda text, source, target: "Olá")
    monkeypatch.setattr(
        "importlib.import_module",
        lambda name: package_module if name == "argostranslate.package" else translate_module,
    )
    provider = ArgosProvider()
    assert provider.is_ready()
    assert provider.translate("Hello", "en", "pt-BR") == "Olá"


def test_missing_optional_dependency_is_reported_cleanly(monkeypatch) -> None:
    def missing(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("importlib.import_module", missing)
    provider = ArgosProvider()
    assert provider.is_ready() is False
    with pytest.raises(ProviderUnavailableError, match="local-translate"):
        provider.translate("Hello", "en", "pt-BR")
