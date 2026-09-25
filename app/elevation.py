"""Altura (m s. n. m.) de coordenadas vía la API de elevación de Open-Meteo.

Gratis y sin API key. Acepta lotes de hasta 100 puntos por petición:
https://open-meteo.com/en/docs/elevation-api
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import requests

_ENDPOINT = "https://api.open-meteo.com/v1/elevation"
_MAX_POR_LOTE = 100


def get_elevations(
    coords: Sequence[Tuple[float, float]],
    timeout: float = 15.0,
) -> List[float | None]:
    """Devuelve la elevación (m) para cada ``(lat, lon)``, en el mismo orden.

    Si un lote falla, esas posiciones quedan como ``None`` en lugar de romper
    toda la consulta.
    """
    resultados: List[float | None] = []

    for inicio in range(0, len(coords), _MAX_POR_LOTE):
        lote = coords[inicio : inicio + _MAX_POR_LOTE]
        lats = ",".join(str(lat) for lat, _ in lote)
        lons = ",".join(str(lon) for _, lon in lote)
        try:
            resp = requests.get(
                _ENDPOINT,
                params={"latitude": lats, "longitude": lons},
                timeout=timeout,
            )
            resp.raise_for_status()
            elevaciones = resp.json().get("elevation") or []
            # Normaliza longitud por si la API devuelve menos valores.
            elevaciones = list(elevaciones) + [None] * (len(lote) - len(elevaciones))
            resultados.extend(elevaciones[: len(lote)])
        except (requests.RequestException, ValueError):
            resultados.extend([None] * len(lote))

    return resultados
