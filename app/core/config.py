"""Gestor de configuración YAML para IA Video Editor Pro."""

from pathlib import Path
from typing import Any

import yaml


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mezcla recursiva de dos diccionarios preservando estructuras anidadas."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """Administrador central de carga y consulta de configuraciones YAML."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            # Localizar la carpeta config relativa al proyecto
            root_dir = Path(__file__).resolve().parent.parent.parent
            self.config_dir = root_dir / "config"
        else:
            self.config_dir = Path(config_dir)

        self._config_cache: dict[str, Any] = {}
        self.load_default_config()

    def load_default_config(self) -> dict[str, Any]:
        """Carga el archivo default.yaml base."""
        default_file = self.config_dir / "default.yaml"
        if not default_file.exists():
            raise FileNotFoundError(f"Archivo de configuración maestro no encontrado: {default_file}")

        with open(default_file, "r", encoding="utf-8") as f:
            self._config_cache = yaml.safe_load(f) or {}
        return self._config_cache

    def get_config_for_profile(self, profile_name: str) -> dict[str, Any]:
        """Devuelve la configuración base fusionada con el perfil especificado."""
        profile_file = self.config_dir / "profiles" / f"{profile_name}.yaml"
        if not profile_file.exists():
            raise FileNotFoundError(f"Perfil de configuración '{profile_name}' no encontrado en {profile_file}")

        with open(profile_file, "r", encoding="utf-8") as f:
            profile_data = yaml.safe_load(f) or {}

        return _deep_merge(self._config_cache, profile_data)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Accede a claves anidadas usando notación de puntos (ej. 'silence.analyze_above_ms')."""
        parts = key_path.split(".")
        current = self._config_cache
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current


# Instancia global por defecto
config = ConfigManager()
