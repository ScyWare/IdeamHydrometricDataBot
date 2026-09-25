"""Descarga de datos DHIME por código de estación (envuelve batch_download).

Reemplaza el uso directo del script ``research/get_data_by_station_id.py`` para
que la app no dependa de ese directorio.
"""

from __future__ import annotations

import os
from typing import List, Sequence

from ideam_dhime import batch_download
from ideam_dhime.batch import DownloadResult


def descargar_estaciones(
    codigos: Sequence[str],
    download_path: str,
    variable_id: int,
    date_ini: str,
    date_fin: str,
    parallel: bool = False,
    workers: int = 2,
) -> List[DownloadResult]:
    """Descarga datos DHIME para ``codigos`` y devuelve los resultados.

    Args:
        codigos: lista de station_code a descargar.
        download_path: carpeta destino (se crea si no existe).
        variable_id: id de variable DHIME (p.ej. 84 = precipitación diaria).
        date_ini / date_fin: rango en formato dd/mm/aaaa (el que usa DHIME).
        parallel / workers: paralelismo del scraper (1 sesión Chrome por worker).
    """
    os.makedirs(download_path, exist_ok=True)

    requests = [
        {
            "download_path": download_path,
            "station_code": str(code),
            "variable_id": variable_id,
            "date_ini": date_ini,
            "date_fin": date_fin,
        }
        for code in codigos
    ]
    return batch_download(requests, parallel=parallel, workers=workers)
