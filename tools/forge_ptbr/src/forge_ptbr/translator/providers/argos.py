from __future__ import annotations

import importlib
import os


class ProviderUnavailableError(RuntimeError):
    pass


def _normalize_language(code: str) -> str:
    normalized = code.strip().replace("_", "-").casefold()
    if normalized in {"pt-br", "pb"}:
        return "pb"
    return normalized.split("-", 1)[0]


class ArgosProvider:
    name = "argos"

    def __init__(self, *, source_lang: str = "en", target_lang: str = "pt-BR") -> None:
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._package_module = None
        self._translate_module = None

    def _load(self):
        if self._package_module is not None and self._translate_module is not None:
            return self._package_module, self._translate_module
        os.environ.setdefault("ARGOS_MODEL_PROVIDER", "OPENNMT")
        os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")
        try:
            package_module = importlib.import_module("argostranslate.package")
            translate_module = importlib.import_module("argostranslate.translate")
        except ModuleNotFoundError as exc:
            raise ProviderUnavailableError(
                "Argos Translate is not installed. Install forge-ptbr[local-translate]."
            ) from exc
        self._package_module = package_module
        self._translate_module = translate_module
        return package_module, translate_module

    def is_ready(self) -> bool:
        try:
            package_module, _ = self._load()
        except ProviderUnavailableError:
            return False
        source = _normalize_language(self.source_lang)
        target = _normalize_language(self.target_lang)
        try:
            packages = package_module.get_installed_packages()
        except Exception:
            return False
        return any(
            getattr(package, "type", "translate") == "translate"
            and getattr(package, "from_code", None) == source
            and getattr(package, "to_code", None) == target
            for package in packages
        )

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        _, translate_module = self._load()
        if not self.is_ready():
            raise ProviderUnavailableError(
                "Argos EN→PT-BR model is not installed. Run the explicit provider setup step first."
            )
        return str(
            translate_module.translate(
                text,
                _normalize_language(source_lang),
                _normalize_language(target_lang),
            )
        )
