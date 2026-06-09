from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Optional

DISTANCIAS = ["6K", "12K", "18K"]
SEXOS = ["M", "F"]
TALLES = ["", "XS", "S", "M", "L", "XL", "XXL"]
ESTADOS_CARRERA = ["Creada", "Iniciada", "Finalizada"]
ESTADOS_INSCRIPCION = ["INSCRIPTO", "LLEGÓ", "DNS", "DNF", "DSQ", "SIN TIEMPO", "CORREGIDO"]
TIPOS_REGISTRO = ["AUTOMATICO", "MANUAL", "QR", "CORREGIDO"]

CATEGORIAS = [
    (16, 19, "16-19"),
    (20, 24, "20-24"),
    (25, 29, "25-29"),
    (30, 34, "30-34"),
    (35, 39, "35-39"),
    (40, 44, "40-44"),
    (45, 49, "45-49"),
    (50, 54, "50-54"),
    (55, 59, "55-59"),
    (60, 64, "60-64"),
    (65, 69, "65-69"),
    (70, 200, "70 y mas"),
]


def normalize_dni(value: str) -> str:
    """Guarda el DNI sin puntos ni espacios."""
    return re.sub(r"\D", "", value or "")


def format_dni(value: str) -> str:
    digits = normalize_dni(value)
    if not digits:
        return ""
    parts = []
    while digits:
        parts.insert(0, digits[-3:])
        digits = digits[:-3]
    return ".".join(parts)


def normalize_number(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    return digits.zfill(3)


def parse_date(value: str) -> date:
    """Acepta dd/mm/aaaa, dd-mm-aaaa o aaaa-mm-dd."""
    value = (value or "").strip()
    if not value:
        raise ValueError("La fecha está vacía")
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Formato de fecha inválido. Usar dd/mm/aaaa")


def format_date(value: Optional[str | date]) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        d = value
    else:
        d = parse_date(str(value))
    return d.strftime("%d/%m/%Y")


def date_to_db(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return parse_date(value).isoformat()


def today_db() -> str:
    return date.today().isoformat()


def calculate_age(fecha_nacimiento: str, fecha_carrera: str) -> int:
    born = parse_date(fecha_nacimiento)
    race_date = parse_date(fecha_carrera)
    age = race_date.year - born.year - ((race_date.month, race_date.day) < (born.month, born.day))
    return age


def category_for_age(age: int) -> str:
    for start, end, label in CATEGORIAS:
        if start <= age <= end:
            return label
    if age < 16:
        return "Menor de 16"
    return "70 y mas"


def seconds_to_time(value: float) -> str:
    if value is None:
        return ""
    value = max(float(value), 0.0)
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    cent = int(round((value - int(value)) * 100))
    if cent >= 100:
        seconds += 1
        cent = 0
    if seconds >= 60:
        minutes += 1
        seconds -= 60
    if minutes >= 60:
        hours += 1
        minutes -= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{cent:02d}"


def time_to_seconds(value: str) -> float:
    """Acepta HH:MM:SS, HH:MM:SS.cc o MM:SS."""
    value = (value or "").strip().replace(",", ".")
    if not value:
        raise ValueError("El tiempo está vacío")
    parts = value.split(":")
    try:
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            sec = float(parts[2])
        elif len(parts) == 2:
            h = 0
            m = int(parts[0])
            sec = float(parts[1])
        else:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Formato de tiempo inválido. Usar HH:MM:SS") from exc
    return h * 3600 + m * 60 + sec


def manual_parts_to_seconds(hs: str, minutes: str, seconds: str, cent: str) -> float:
    h = int(hs or 0)
    m = int(minutes or 0)
    s = int(seconds or 0)
    c = int(cent or 0)
    if not (0 <= m < 60 and 0 <= s < 60 and 0 <= c < 100):
        raise ValueError("Minutos, segundos y centésimas fuera de rango")
    return h * 3600 + m * 60 + s + c / 100


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def iso_to_display(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return value


def elapsed_since(start_iso: Optional[str]) -> float:
    if not start_iso:
        return 0.0
    start = datetime.fromisoformat(start_iso)
    return max((datetime.now() - start).total_seconds(), 0.0)
