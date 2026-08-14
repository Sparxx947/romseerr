"""Pixel aus einem Playwright-Screenshot lesen — ohne Pillow und ohne numpy.

WARUM ÜBERHAUPT PIXEL: `getBoundingClientRect()` beschreibt Kästen, nicht das, was man
sieht. Ein Zeichen kann in seinem Kasten sitzen und trotzdem sichtbar daneben stehen —
genau das war #659: Der Kasten des Textes war 24 px hoch in einem 14 px hohen Inhalts-
bereich, also lag die Tinte tiefer als jeder Kasten es verriet. Wer nur Kästen misst,
bestätigt eine Verschiebung als in Ordnung.

WARUM KEIN PILLOW: Weder Pillow noch numpy sind Abhängigkeit dieses Projekts, und für
ein 32x32-Bild eines Knopfes lohnt keine. PNG mit 8 bit ohne Interlacing ist das, was
Chromium liefert; mehr muss hier nicht gelesen werden.

EN: rect measurements describe boxes, not ink. In #659 the text box was taller than the
button's content box, so the glyph sat visibly low while every box looked plausible.
This decodes the 8-bit non-interlaced PNG Chromium produces, with no extra dependency.
"""
import struct
import zlib


def png_lesen(daten):
    """PNG (8 bit, RGB oder RGBA, ohne Interlacing) -> (breite, hoehe, zeilen).

    `zeilen[y][x]` ist ein Tupel je Kanal. Andere Formen werden nicht stillschweigend
    falsch gelesen, sondern abgewiesen — ein stumm fehlinterpretiertes Bild ergäbe
    Messwerte, die nach etwas aussehen und nichts bedeuten.
    """
    if daten[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("kein PNG")
    pos, roh, breite, hoehe, kanaele = 8, b"", 0, 0, 4
    while pos + 8 <= len(daten):
        laenge, typ = struct.unpack(">I4s", daten[pos:pos + 8])
        block = daten[pos + 8:pos + 8 + laenge]
        if typ == b"IHDR":
            breite, hoehe, tiefe, farbtyp = struct.unpack(">IIBB", block[:10])
            verschraenkt = block[12]
            if tiefe != 8 or farbtyp not in (2, 6) or verschraenkt:
                raise ValueError(
                    f"PNG-Form nicht unterstützt: Tiefe {tiefe}, Farbtyp {farbtyp}, "
                    f"interlace {verschraenkt}")
            kanaele = 3 if farbtyp == 2 else 4
        elif typ == b"IDAT":
            roh += block
        elif typ == b"IEND":
            break
        pos += 12 + laenge
    puffer = zlib.decompress(roh)
    breite_bytes = breite * kanaele
    vorher = bytearray(breite_bytes)
    zeilen, p = [], 0
    for _ in range(hoehe):
        filt = puffer[p]
        p += 1
        akt = bytearray(puffer[p:p + breite_bytes])
        p += breite_bytes
        if filt:
            for i in range(breite_bytes):
                a = akt[i - kanaele] if i >= kanaele else 0
                b = vorher[i]
                c = vorher[i - kanaele] if i >= kanaele else 0
                if filt == 1:
                    akt[i] = (akt[i] + a) & 0xFF
                elif filt == 2:
                    akt[i] = (akt[i] + b) & 0xFF
                elif filt == 3:
                    akt[i] = (akt[i] + (a + b) // 2) & 0xFF
                elif filt == 4:
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    vorhersage = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                    akt[i] = (akt[i] + vorhersage) & 0xFF
                else:
                    raise ValueError(f"unbekannter Zeilenfilter {filt}")
        vorher = akt
        zeilen.append([tuple(akt[x * kanaele:(x + 1) * kanaele]) for x in range(breite)])
    return breite, hoehe, zeilen


def tintenraender(bild, schwelle=170):
    """Die Ränder um die hellen Pixel eines Bildes, in Gerätepixeln.

    Gedacht für helle Zeichen auf dunklem Grund — die Oberfläche ist durchgehend dunkel.
    Gibt `None` zurück, wenn nichts über der Schwelle liegt; ein Aufrufer, der das für
    „mittig" hält, bestünde inhaltsleer, deshalb kein stiller Nullwert.
    """
    breite, hoehe, zeilen = bild
    xs, ys = [], []
    for y in range(hoehe):
        for x in range(breite):
            px = zeilen[y][x]
            if len(px) == 4 and px[3] < 128:
                continue
            if (px[0] + px[1] + px[2]) / 3 >= schwelle:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return {"bild": (breite, hoehe),
            "tinte": (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1),
            "links": min(xs), "rechts": breite - 1 - max(xs),
            "oben": min(ys), "unten": hoehe - 1 - max(ys)}
