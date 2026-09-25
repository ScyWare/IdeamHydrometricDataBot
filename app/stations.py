"""Búsqueda de las estaciones hidrométricas IDEAM más cercanas a un punto.

Independiente de ``research/``: la lógica de proximidad vive aquí.
"""

from __future__ import annotations

import math
import unicodedata
from typing import List, TypedDict

from ideam_dhime.stations_generated import STATIONS_DHIME  # dict[str, StationMetadata]


class EstacionCercana(TypedDict):
    distancia_km: float
    codigo: str
    nombre: str
    categoria: str
    municipio: str
    departamento: str
    latitud: float
    longitud: float
    activa: bool
    fecha_fin_op: str


# Categorías que miden precipitación / meteorología (NO son hidrométricas).
_CATEGORIAS_PRECIP = ("pluvio", "climat", "climatolog", "agro", "sinop", "meteor")

_RADIO_TIERRA_KM = 6371.0088


def _to_float(x: str) -> float | None:
    """Convierte coordenada a float tolerando coma decimal ('5,50' -> 5.50)."""
    if not x:
        return None
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def _sin_tildes(texto: str) -> str:
    """Minúsculas sin tildes ('Sinóptica' -> 'sinoptica') para comparar categorías."""
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(ch for ch in t if not unicodedata.combining(ch)).lower()


def _mide_precip(categoria: str) -> bool:
    c = _sin_tildes(categoria)
    return any(k in c for k in _CATEGORIAS_PRECIP)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia sobre la esfera (km) entre dos puntos en grados decimales."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def nearest_ideam_stations(
    lat: float,
    lon: float,
    top_k: int,
    incluir_cerradas: bool = True,
) -> List[EstacionCercana]:
    """Devuelve las ``top_k`` estaciones hidrométricas más cercanas a (lat, lon).

    Filtra las estaciones que miden precipitación/meteorología (se quedan las
    hidrométricas: limnimétricas, limnigráficas, etc.) y ordena por distancia
    haversine ascendente.
    """
    encontradas: list[EstacionCercana] = []

    for station in STATIONS_DHIME.values():
        if _mide_precip(station.category):
            continue

        activa = not bool((station.fecha_fin_op or "").strip())
        if not incluir_cerradas and not activa:
            continue

        la, lo = _to_float(station.latitude), _to_float(station.longitude)
        if la is None or lo is None:
            continue

        encontradas.append(
            EstacionCercana(
                distancia_km=round(_haversine_km(lat, lon, la, lo), 3),
                codigo=station.station_code,
                nombre=station.station_name,
                categoria=station.category,
                municipio=station.municipality,
                departamento=station.department,
                latitud=la,
                longitud=lo,
                activa=activa,
                fecha_fin_op=station.fecha_fin_op,
            )
        )

    encontradas.sort(key=lambda e: e["distancia_km"])
    return encontradas[: max(top_k, 0)]
