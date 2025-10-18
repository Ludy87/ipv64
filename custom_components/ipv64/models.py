"""Data models for the IPv64 integration."""

from __future__ import annotations

from dataclasses import dataclass

from .coordinator import IPv64DataUpdateCoordinator


@dataclass(slots=True)
class IPv64RuntimeData:
    """Runtime data stored on the config entry."""

    coordinator: IPv64DataUpdateCoordinator
