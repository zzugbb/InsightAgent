#!/usr/bin/env python3
"""生成 32×32 favicon.ico（内嵌 PNG），与品牌符号「气泡 + 轨迹」一致。"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

W = H = 32
BG = (15, 20, 25, 255)
ACCENT = (34, 197, 94, 255)
HI = (34, 197, 94, 115)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _encode_png_rgba(rgba: bytes, w: int, h: int) -> bytes:
    raw = b""
    for y in range(h):
        raw += b"\x00" + rgba[y * w * 4 : (y + 1) * w * 4]
    ihdr = struct.pack(">2I5B", w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def _blend(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]):
    """src over dst"""
    sr, sg, sb, sa = src
    if sa >= 255:
        return src
    dr, dg, db, da = dst
    a = sa + da * (255 - sa) // 255
    if a == 0:
        return (0, 0, 0, 0)
    r = (sr * sa + dr * da * (255 - sa) // 255) // a
    g = (sg * sa + dg * da * (255 - sa) // 255) // a
    b = (sb * sa + db * da * (255 - sa) // 255) // a
    return (r, g, b, a)


def _draw_disk(buf: bytearray, w: int, cx: float, cy: float, rad: float, col) -> None:
    r0 = int(rad + 1)
    for y in range(max(0, int(cy - r0)), min(H, int(cy + r0) + 1)):
        for x in range(max(0, int(cx - r0)), min(W, int(cx + r0) + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                i = (y * w + x) * 4
                buf[i : i + 4] = bytes(_blend(tuple(buf[i : i + 4]), col))


def _draw_ring_ellipse(
    buf: bytearray,
    w: int,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    thickness: float,
    col,
) -> None:
    """近似椭圆描边。"""
    for y in range(H):
        for x in range(W):
            nx = (x - cx) / rx
            ny = (y - cy) / ry
            d = (nx * nx + ny * ny) ** 0.5
            if abs(d - 1.0) * min(rx, ry) <= thickness * 0.5:
                i = (y * w + x) * 4
                buf[i : i + 4] = bytes(_blend(tuple(buf[i : i + 4]), col))


def _draw_line(buf: bytearray, w: int, x0: float, y0: float, x1: float, y1: float, sw: float, col) -> None:
    """粗线段（圆帽）。"""
    steps = int(max(abs(x1 - x0), abs(y1 - y0), 1)) * 2
    for t in range(steps + 1):
        px = x0 + (x1 - x0) * t / steps
        py = y0 + (y1 - y0) * t / steps
        _draw_disk(buf, w, px, py, sw / 2, col)


def rasterize() -> bytes:
    buf = bytearray(W * H * 4)
    for i in range(W * H):
        buf[i * 4 : i * 4 + 4] = BG

    # 对话气泡（椭圆描边），与 40px 设计同比缩放到 32
    _draw_ring_ellipse(buf, W, 8.5, 13.0, 7.2, 6.2, 1.35, ACCENT)
    # 气泡尾巴
    _draw_line(buf, W, 10.5, 18.5, 12.5, 21.5, 1.8, ACCENT)
    _draw_line(buf, W, 12.5, 21.5, 14.0, 20.0, 1.8, ACCENT)

    # 轨迹：竖线 + 三节点
    _draw_line(buf, W, 23.0, 8.5, 23.0, 25.5, 1.65, ACCENT)
    _draw_disk(buf, W, 23.0, 7.0, 2.1, ACCENT)
    _draw_disk(buf, W, 23.0, 16.0, 2.1, ACCENT)
    _draw_disk(buf, W, 23.0, 25.0, 2.1, ACCENT)

    # 气泡内高光
    _draw_disk(buf, W, 11.0, 12.0, 1.6, HI)

    return bytes(buf)


def png_to_ico(png_bytes: bytes, out: Path) -> None:
    reserved = 0
    header = struct.pack("<HHH", reserved, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        32,
        32,
        0,
        0,
        1,
        32,
        len(png_bytes),
        6 + 16,
    )
    out.write_bytes(header + entry + png_bytes)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rgba = rasterize()
    png = _encode_png_rgba(rgba, W, H)
    out = root / "public" / "favicon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    png_to_ico(png, out)
    print(f"Wrote {out} ({len(png)} bytes PNG in ICO)")


if __name__ == "__main__":
    main()
