from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

import numpy as np


@dataclass(frozen=True)
class TecmagHeader:
    magic_ascii: str
    tecmag_struct_size: int
    actualpoint1d: int
    npoints2d_header: int
    npoints3d: int
    npoints4d: int
    npoints1d: int
    actualpoint2d: int
    actualpoint3d: int
    actualpoint4d: int
    acqpoints: int
    startscan1d: int
    startscan2d: int
    startscan3d: int
    startscan4d: int
    scans1d: int
    actualscan1d: int
    dummyscans: int
    repeattimes: int
    date_raw: str


@dataclass(frozen=True)
class TecmagTNTData:
    path: Path
    header: TecmagHeader
    raw_data: np.ndarray
    acqpoints: int
    actualscan1d: int
    npoints2d: int


def _decode_ascii(block: bytes) -> str:
    return block.decode("latin1", errors="replace").rstrip("\x00")


def read_tnt(path: str | Path) -> TecmagTNTData:
    file_path = Path(path)
    with file_path.open("rb") as handle:
        prefix = handle.read(16)
        ints = struct.unpack("<20i", handle.read(80))

        tecmag_struct_size = ints[0]
        npoints1d = ints[5]
        npoints2d = ints[6]
        npoints3d = ints[3]
        npoints4d = ints[4]
        count = 2 * npoints1d * npoints2d * npoints3d * npoints4d

        body = handle.read(tecmag_struct_size - 64)
        date_raw = _decode_ascii(body[787:806]).strip()

        raw_flat = np.fromfile(handle, dtype="<f4", count=count)

    if raw_flat.size != count:
        raise ValueError(
            f"Expected {count} float32 values from TNT payload, found {raw_flat.size}"
        )

    raw_pairs = raw_flat.reshape(-1, 2)
    raw_complex = raw_pairs[:, 0] + 1j * raw_pairs[:, 1]
    raw_complex = np.conj(raw_complex)
    raw_complex = raw_complex.reshape(npoints1d, npoints2d, npoints3d, npoints4d)

    header = TecmagHeader(
        magic_ascii=_decode_ascii(prefix),
        tecmag_struct_size=tecmag_struct_size,
        actualpoint1d=ints[1],
        npoints2d_header=ints[2],
        npoints3d=ints[3],
        npoints4d=ints[4],
        npoints1d=npoints1d,
        actualpoint2d=ints[6],
        actualpoint3d=ints[7],
        actualpoint4d=ints[8],
        acqpoints=ints[9],
        startscan1d=ints[10],
        startscan2d=ints[11],
        startscan3d=ints[12],
        startscan4d=ints[13],
        scans1d=ints[14],
        actualscan1d=ints[15],
        dummyscans=ints[16],
        repeattimes=ints[17],
        date_raw=date_raw,
    )

    return TecmagTNTData(
        path=file_path,
        header=header,
        raw_data=raw_complex,
        acqpoints=ints[9],
        actualscan1d=ints[15],
        npoints2d=ints[6],
    )
