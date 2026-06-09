from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

from .utils import (
    calculate_age,
    category_for_age,
    date_to_db,
    format_dni,
    normalize_dni,
    normalize_number,
    now_iso,
    seconds_to_time,
)

def get_user_data_dir() -> Path:
    """Carpeta segura para guardar la base, funcione como .py o como .exe instalado."""
    if os.name == "nt":
        root = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if root:
            return Path(root) / "CronometrajeDemo"
    return Path.home() / ".cronometraje_demo"


DATA_DIR = get_user_data_dir()
DB_PATH = DATA_DIR / "cronometraje.db"


class Database:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    def create_schema(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS carreras (
                id_carrera INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                fecha TEXT NOT NULL,
                lugar TEXT,
                distancias TEXT NOT NULL DEFAULT '6K,12K,18K',
                estado TEXT NOT NULL DEFAULT 'Creada',
                hora_inicio TEXT,
                hora_fin TEXT
            );

            CREATE TABLE IF NOT EXISTS corredores (
                id_corredor INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT NOT NULL UNIQUE,
                apellido TEXT NOT NULL,
                nombre TEXT NOT NULL,
                sexo TEXT NOT NULL,
                ciudad TEXT,
                fecha_nacimiento TEXT NOT NULL,
                team TEXT
            );

            CREATE TABLE IF NOT EXISTS inscripciones (
                id_inscripcion INTEGER PRIMARY KEY AUTOINCREMENT,
                id_carrera INTEGER NOT NULL,
                id_corredor INTEGER NOT NULL,
                numero TEXT NOT NULL,
                distancia TEXT NOT NULL,
                categoria TEXT NOT NULL,
                talle TEXT,
                estado TEXT NOT NULL DEFAULT 'INSCRIPTO',
                FOREIGN KEY (id_carrera) REFERENCES carreras(id_carrera) ON DELETE CASCADE,
                FOREIGN KEY (id_corredor) REFERENCES corredores(id_corredor) ON DELETE CASCADE,
                UNIQUE (id_carrera, numero),
                UNIQUE (id_carrera, id_corredor)
            );

            CREATE TABLE IF NOT EXISTS llegadas (
                id_llegada INTEGER PRIMARY KEY AUTOINCREMENT,
                id_inscripcion INTEGER NOT NULL UNIQUE,
                tiempo_llegada REAL NOT NULL,
                hora_registro TEXT NOT NULL,
                tipo_registro TEXT NOT NULL,
                tiempo_manual REAL,
                observacion TEXT,
                FOREIGN KEY (id_inscripcion) REFERENCES inscripciones(id_inscripcion) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def backup_to(self, destination: Path | str) -> Path:
        """Crea una copia consistente de la base SQLite aunque el programa esté abierto."""
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # IMPORTANTE:
        # En Windows, `with sqlite3.connect(...) as target:` NO cierra la conexión;
        # solo confirma o revierte la transacción. Si no se cierra manualmente,
        # el archivo temporal queda bloqueado y al comprimirlo aparece WinError 32.
        target = sqlite3.connect(str(dest))
        try:
            self.conn.backup(target)
            target.commit()
        finally:
            target.close()

        return dest

    @staticmethod
    def validate_database_file(path: Path | str) -> None:
        """Valida que el archivo sea una base SQLite compatible con el programa."""
        db_path = Path(path)
        if not db_path.exists():
            raise ValueError("El archivo de base de datos no existe")
        required_tables = {"carreras", "corredores", "inscripciones", "llegadas"}
        try:
            with sqlite3.connect(db_path) as conn:
                integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    raise ValueError("La base SQLite está dañada o no pasó el control de integridad")
                rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                tables = {row[0] for row in rows}
        except sqlite3.DatabaseError as exc:
            raise ValueError("El archivo seleccionado no es una base SQLite válida") from exc
        missing = required_tables - tables
        if missing:
            faltantes = ", ".join(sorted(missing))
            raise ValueError(f"La base no corresponde a Cronometraje. Faltan tablas: {faltantes}")

    def _one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, tuple(params)).fetchone()

    def _all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, tuple(params)).fetchall())

    # Carreras
    def create_race(self, nombre: str, fecha: str, lugar: str, distancias: list[str]) -> int:
        fecha_db = date_to_db(fecha)
        distancias_txt = ",".join(distancias or ["6K", "12K", "18K"])
        cur = self.conn.execute(
            "INSERT INTO carreras(nombre, fecha, lugar, distancias, estado) VALUES (?, ?, ?, ?, 'Creada')",
            (nombre.strip(), fecha_db, lugar.strip(), distancias_txt),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_race(self, id_carrera: int, nombre: str, fecha: str, lugar: str, distancias: list[str], estado: str) -> None:
        self.conn.execute(
            "UPDATE carreras SET nombre=?, fecha=?, lugar=?, distancias=?, estado=? WHERE id_carrera=?",
            (nombre.strip(), date_to_db(fecha), lugar.strip(), ",".join(distancias), estado, id_carrera),
        )
        self.conn.commit()

    def delete_race(self, id_carrera: int) -> None:
        self.conn.execute("DELETE FROM carreras WHERE id_carrera=?", (id_carrera,))
        self.conn.commit()

    def list_races(self) -> list[sqlite3.Row]:
        return self._all("SELECT * FROM carreras ORDER BY fecha DESC, id_carrera DESC")

    def get_race(self, id_carrera: int) -> Optional[sqlite3.Row]:
        return self._one("SELECT * FROM carreras WHERE id_carrera=?", (id_carrera,))

    def start_race(self, id_carrera: int) -> None:
        race = self.get_race(id_carrera)
        if not race:
            raise ValueError("No se encontró la carrera")
        if race["estado"] == "Finalizada":
            raise ValueError("La carrera ya está finalizada")
        hora_inicio = race["hora_inicio"] or now_iso()
        self.conn.execute(
            "UPDATE carreras SET estado='Iniciada', hora_inicio=? WHERE id_carrera=?",
            (hora_inicio, id_carrera),
        )
        self.conn.commit()

    def finalize_race(self, id_carrera: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE carreras SET estado='Finalizada', hora_fin=? WHERE id_carrera=?",
                (now_iso(), id_carrera),
            )
            self.conn.execute(
                """
                UPDATE inscripciones
                SET estado='SIN TIEMPO'
                WHERE id_carrera=?
                  AND estado NOT IN ('DNS','DNF','DSQ','LLEGÓ','CORREGIDO')
                  AND id_inscripcion NOT IN (SELECT id_inscripcion FROM llegadas)
                """,
                (id_carrera,),
            )

    # Corredores e inscripciones
    def create_or_enroll_runner(
        self,
        id_carrera: int,
        dni: str,
        apellido: str,
        nombre: str,
        sexo: str,
        ciudad: str,
        fecha_nacimiento: str,
        team: str,
        distancia: str,
        numero: str,
        talle: str,
    ) -> int:
        race = self.get_race(id_carrera)
        if not race:
            raise ValueError("Debe abrir una carrera válida")
        if race["estado"] == "Finalizada":
            raise ValueError("La carrera está finalizada. No se pueden cargar corredores")
        dni_norm = normalize_dni(dni)
        if not dni_norm:
            raise ValueError("El DNI es obligatorio")
        numero_norm = normalize_number(numero)
        if not numero_norm:
            raise ValueError("El número de corredor es obligatorio")
        if sexo not in ("M", "F"):
            raise ValueError("Sexo inválido")
        edad = calculate_age(date_to_db(fecha_nacimiento), race["fecha"])
        categoria = category_for_age(edad)
        birth_db = date_to_db(fecha_nacimiento)

        existing_number = self._one(
            "SELECT id_inscripcion FROM inscripciones WHERE id_carrera=? AND numero=?",
            (id_carrera, numero_norm),
        )
        if existing_number:
            raise ValueError("Ya existe un corredor con ese número en esta carrera")

        with self.conn:
            corredor = self._one("SELECT * FROM corredores WHERE dni=?", (dni_norm,))
            if corredor:
                id_corredor = int(corredor["id_corredor"])
                enrolled = self._one(
                    "SELECT id_inscripcion FROM inscripciones WHERE id_carrera=? AND id_corredor=?",
                    (id_carrera, id_corredor),
                )
                if enrolled:
                    raise ValueError("El DNI ya está cargado en esta carrera")
                # Actualiza datos personales por si estaban incompletos en otra carrera.
                self.conn.execute(
                    """
                    UPDATE corredores
                    SET apellido=?, nombre=?, sexo=?, ciudad=?, fecha_nacimiento=?, team=?
                    WHERE id_corredor=?
                    """,
                    (apellido.strip(), nombre.strip(), sexo, ciudad.strip(), birth_db, team.strip(), id_corredor),
                )
            else:
                cur = self.conn.execute(
                    """
                    INSERT INTO corredores(dni, apellido, nombre, sexo, ciudad, fecha_nacimiento, team)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (dni_norm, apellido.strip(), nombre.strip(), sexo, ciudad.strip(), birth_db, team.strip()),
                )
                id_corredor = int(cur.lastrowid)

            cur = self.conn.execute(
                """
                INSERT INTO inscripciones(id_carrera, id_corredor, numero, distancia, categoria, talle, estado)
                VALUES (?, ?, ?, ?, ?, ?, 'INSCRIPTO')
                """,
                (id_carrera, id_corredor, numero_norm, distancia, categoria, talle),
            )
            return int(cur.lastrowid)

    def update_enrollment(
        self,
        id_inscripcion: int,
        dni: str,
        apellido: str,
        nombre: str,
        sexo: str,
        ciudad: str,
        fecha_nacimiento: str,
        team: str,
        distancia: str,
        numero: str,
        talle: str,
        estado: str,
    ) -> None:
        row = self.get_enrollment(id_inscripcion)
        if not row:
            raise ValueError("No se encontró la inscripción")
        race = self.get_race(row["id_carrera"])
        if not race:
            raise ValueError("No se encontró la carrera")
        dni_norm = normalize_dni(dni)
        numero_norm = normalize_number(numero)
        edad = calculate_age(date_to_db(fecha_nacimiento), race["fecha"])
        categoria = category_for_age(edad)
        birth_db = date_to_db(fecha_nacimiento)

        other_dni = self._one(
            "SELECT id_corredor FROM corredores WHERE dni=? AND id_corredor<>?",
            (dni_norm, row["id_corredor"]),
        )
        if other_dni:
            raise ValueError("Ese DNI ya pertenece a otro corredor")
        other_num = self._one(
            "SELECT id_inscripcion FROM inscripciones WHERE id_carrera=? AND numero=? AND id_inscripcion<>?",
            (row["id_carrera"], numero_norm, id_inscripcion),
        )
        if other_num:
            raise ValueError("Ese número ya está usado por otro corredor en esta carrera")

        with self.conn:
            self.conn.execute(
                """
                UPDATE corredores
                SET dni=?, apellido=?, nombre=?, sexo=?, ciudad=?, fecha_nacimiento=?, team=?
                WHERE id_corredor=?
                """,
                (dni_norm, apellido.strip(), nombre.strip(), sexo, ciudad.strip(), birth_db, team.strip(), row["id_corredor"]),
            )
            self.conn.execute(
                """
                UPDATE inscripciones
                SET numero=?, distancia=?, categoria=?, talle=?, estado=?
                WHERE id_inscripcion=?
                """,
                (numero_norm, distancia, categoria, talle, estado, id_inscripcion),
            )

    def delete_enrollment(self, id_inscripcion: int) -> None:
        self.conn.execute("DELETE FROM inscripciones WHERE id_inscripcion=?", (id_inscripcion,))
        self.conn.commit()

    def get_enrollment(self, id_inscripcion: int) -> Optional[sqlite3.Row]:
        return self._one(
            """
            SELECT i.*, c.dni, c.apellido, c.nombre, c.sexo, c.ciudad, c.fecha_nacimiento, c.team,
                   ca.fecha AS fecha_carrera
            FROM inscripciones i
            JOIN corredores c ON c.id_corredor=i.id_corredor
            JOIN carreras ca ON ca.id_carrera=i.id_carrera
            WHERE i.id_inscripcion=?
            """,
            (id_inscripcion,),
        )

    def get_enrollment_by_number(self, id_carrera: int, numero: str) -> Optional[sqlite3.Row]:
        return self._one(
            """
            SELECT i.*, c.dni, c.apellido, c.nombre, c.sexo, c.ciudad, c.fecha_nacimiento, c.team
            FROM inscripciones i
            JOIN corredores c ON c.id_corredor=i.id_corredor
            WHERE i.id_carrera=? AND i.numero=?
            """,
            (id_carrera, normalize_number(numero)),
        )

    def list_enrollments(self, id_carrera: int, search: str = "") -> list[sqlite3.Row]:
        params: list[Any] = [id_carrera]
        where = "WHERE i.id_carrera=?"
        if search.strip():
            like = f"%{search.strip()}%"
            dni_like = f"%{normalize_dni(search)}%"
            where += " AND (c.apellido LIKE ? OR c.nombre LIKE ? OR c.ciudad LIKE ? OR c.dni LIKE ? OR i.numero LIKE ?)"
            params += [like, like, like, dni_like, like]
        return self._all(
            f"""
            SELECT i.*, c.dni, c.apellido, c.nombre, c.sexo, c.ciudad, c.fecha_nacimiento, c.team,
                   ca.fecha AS fecha_carrera
            FROM inscripciones i
            JOIN corredores c ON c.id_corredor=i.id_corredor
            JOIN carreras ca ON ca.id_carrera=i.id_carrera
            {where}
            ORDER BY CAST(i.numero AS INTEGER), i.numero
            """,
            params,
        )

    # Llegadas
    def arrival_exists(self, id_inscripcion: int) -> bool:
        return self._one("SELECT id_llegada FROM llegadas WHERE id_inscripcion=?", (id_inscripcion,)) is not None

    def create_arrival(self, id_inscripcion: int, tiempo_llegada: float, tipo_registro: str = "AUTOMATICO", observacion: str = "") -> int:
        if self.arrival_exists(id_inscripcion):
            raise ValueError("Este corredor ya tiene una llegada registrada")
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO llegadas(id_inscripcion, tiempo_llegada, hora_registro, tipo_registro, tiempo_manual, observacion)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (id_inscripcion, tiempo_llegada, now_iso(), tipo_registro, observacion),
            )
            self.conn.execute(
                "UPDATE inscripciones SET estado='LLEGÓ' WHERE id_inscripcion=?",
                (id_inscripcion,),
            )
            return int(cur.lastrowid)

    def upsert_manual_arrival(self, id_inscripcion: int, tiempo: float, observacion: str = "") -> None:
        with self.conn:
            existing = self._one("SELECT id_llegada FROM llegadas WHERE id_inscripcion=?", (id_inscripcion,))
            if existing:
                self.conn.execute(
                    """
                    UPDATE llegadas
                    SET tiempo_llegada=?, tiempo_manual=?, hora_registro=?, tipo_registro='CORREGIDO', observacion=?
                    WHERE id_inscripcion=?
                    """,
                    (tiempo, tiempo, now_iso(), observacion, id_inscripcion),
                )
                self.conn.execute("UPDATE inscripciones SET estado='CORREGIDO' WHERE id_inscripcion=?", (id_inscripcion,))
            else:
                self.conn.execute(
                    """
                    INSERT INTO llegadas(id_inscripcion, tiempo_llegada, hora_registro, tipo_registro, tiempo_manual, observacion)
                    VALUES (?, ?, ?, 'MANUAL', ?, ?)
                    """,
                    (id_inscripcion, tiempo, now_iso(), tiempo, observacion),
                )
                self.conn.execute("UPDATE inscripciones SET estado='LLEGÓ' WHERE id_inscripcion=?", (id_inscripcion,))

    def delete_arrival(self, id_llegada: int) -> None:
        row = self._one("SELECT id_inscripcion FROM llegadas WHERE id_llegada=?", (id_llegada,))
        if not row:
            return
        with self.conn:
            self.conn.execute("DELETE FROM llegadas WHERE id_llegada=?", (id_llegada,))
            self.conn.execute("UPDATE inscripciones SET estado='INSCRIPTO' WHERE id_inscripcion=?", (row["id_inscripcion"],))

    def list_arrivals(self, id_carrera: int) -> list[sqlite3.Row]:
        return self._all(
            """
            SELECT l.*, i.numero, i.distancia, i.categoria, i.estado, c.apellido, c.nombre, c.ciudad, c.sexo
            FROM llegadas l
            JOIN inscripciones i ON i.id_inscripcion=l.id_inscripcion
            JOIN corredores c ON c.id_corredor=i.id_corredor
            WHERE i.id_carrera=?
            ORDER BY l.tiempo_llegada ASC
            """,
            (id_carrera,),
        )

    def list_results(self, id_carrera: int, distancia: str = "Todas", sexo: str = "Todos", categoria: str = "Todas") -> list[dict[str, Any]]:
        rows = self._all(
            """
            SELECT l.*, i.numero, i.distancia, i.categoria, i.estado, c.apellido, c.nombre, c.ciudad, c.sexo, c.dni
            FROM llegadas l
            JOIN inscripciones i ON i.id_inscripcion=l.id_inscripcion
            JOIN corredores c ON c.id_corredor=i.id_corredor
            WHERE i.id_carrera=?
            ORDER BY i.distancia, c.sexo, l.tiempo_llegada ASC
            """,
            (id_carrera,),
        )
        result = []
        for r in rows:
            if distancia != "Todas" and r["distancia"] != distancia:
                continue
            if sexo != "Todos" and r["sexo"] != sexo:
                continue
            if categoria != "Todas" and r["categoria"] != categoria:
                continue
            result.append(dict(r))
        result.sort(key=lambda x: (x["distancia"], x["sexo"], x["tiempo_llegada"]))
        return result

    def list_without_time(self, id_carrera: int) -> list[sqlite3.Row]:
        return self._all(
            """
            SELECT i.*, c.dni, c.apellido, c.nombre, c.sexo, c.ciudad
            FROM inscripciones i
            JOIN corredores c ON c.id_corredor=i.id_corredor
            WHERE i.id_carrera=?
              AND i.id_inscripcion NOT IN (SELECT id_inscripcion FROM llegadas)
            ORDER BY CAST(i.numero AS INTEGER)
            """,
            (id_carrera,),
        )

    def set_enrollment_status(self, id_inscripcion: int, estado: str) -> None:
        self.conn.execute("UPDATE inscripciones SET estado=? WHERE id_inscripcion=?", (estado, id_inscripcion))
        self.conn.commit()

    def seed_demo_data(self) -> int:
        """Carga una carrera de prueba ya finalizada con 100 corredores y 100 llegadas.

        Esta muestra sirve para probar reportes, clasificaciones, podios por distancia,
        sexo y categorías sin tener que tipear manualmente las llegadas durante la demo.
        """
        race_id = self.create_race(
            "Cronos Cross Trail 2026",
            "10/11/2026",
            "Arrecifes, Buenos Aires",
            ["6K", "12K", "18K"],
        )

        apellidos = [
            "Lepiscopo", "Gomez", "Perez", "Diaz", "Rossi", "Sosa", "Fernandez", "Martinez",
            "Rodriguez", "Lopez", "Garcia", "Sanchez", "Romero", "Torres", "Alvarez", "Ruiz",
            "Acosta", "Benitez", "Molina", "Herrera", "Castro", "Silva", "Vega", "Suarez",
            "Morales", "Nunez", "Ortiz", "Medina", "Arias", "Paz", "Correa", "Rivas",
        ]
        nombres_m = [
            "Fernando", "Marcos", "Pablo", "Juan", "Lucas", "Martin", "Nicolas", "Diego",
            "Sebastian", "Matias", "Ezequiel", "Agustin", "Tomas", "Joaquin", "Carlos", "Miguel",
            "Hernan", "Federico", "Leonardo", "Maximiliano",
        ]
        nombres_f = [
            "Laura", "Carla", "Andrea", "Sofia", "Valentina", "Camila", "Lucia", "Martina",
            "Florencia", "Natalia", "Rocio", "Julieta", "Paula", "Gabriela", "Veronica", "Cecilia",
            "Mariana", "Romina", "Daniela", "Patricia",
        ]
        ciudades = [
            "Arrecifes", "Pergamino", "Salto", "Rojas", "Capitan Sarmiento", "San Antonio de Areco",
            "Carmen de Areco", "Baradero", "San Pedro", "Chacabuco", "Junin", "Ramallo",
        ]
        teams = ["Cronos", "Libre", "Team Norte", "Trail", "Runners", "Atletismo Areco", "Sin Team"]
        distancias = ["6K", "12K", "18K"]
        talles = ["XS", "S", "M", "L", "XL", "XXL", ""]

        # Fechas elegidas para cubrir todas las categorías al día 10/11/2026.
        fechas_por_categoria = [
            "15/06/2010",  # 16 años -> 16-19
            "20/04/2006",  # 20 años -> 20-24
            "12/08/2001",  # 25 años -> 25-29
            "03/03/1993",  # 33 años -> 30-34
            "25/12/1988",  # 37 años -> 35-39
            "15/08/1982",  # 44 años -> 40-44
            "07/07/1977",  # 49 años -> 45-49
            "11/05/1972",  # 54 años -> 50-54
            "19/09/1968",  # 58 años -> 55-59
            "30/01/1962",  # 64 años -> 60-64
            "16/02/1958",  # 68 años -> 65-69
            "10/10/1952",  # 74 años -> 70 y mas
        ]

        inicio_dt = datetime(2026, 11, 10, 9, 0, 0)
        fin_dt = inicio_dt + timedelta(hours=3, minutes=10)
        self.conn.execute(
            "UPDATE carreras SET estado='Iniciada', hora_inicio=?, hora_fin=NULL WHERE id_carrera=?",
            (inicio_dt.isoformat(timespec="seconds"), race_id),
        )
        self.conn.commit()

        for i in range(1, 101):
            sexo = "M" if i % 2 else "F"
            nombre = nombres_m[(i - 1) % len(nombres_m)] if sexo == "M" else nombres_f[(i - 1) % len(nombres_f)]
            apellido = apellidos[(i - 1) % len(apellidos)]
            dni = str(29000000 + i)
            ciudad = ciudades[(i - 1) % len(ciudades)]
            fecha_nacimiento = fechas_por_categoria[(i - 1) % len(fechas_por_categoria)]
            team = teams[(i - 1) % len(teams)]
            distancia = distancias[(i - 1) % len(distancias)]
            numero = f"{i:03d}"
            talle = talles[(i - 1) % len(talles)]

            id_inscripcion = self.create_or_enroll_runner(
                race_id,
                dni,
                apellido,
                nombre,
                sexo,
                ciudad,
                fecha_nacimiento,
                team,
                distancia,
                numero,
                talle,
            )

            # Tiempos variados y realistas por distancia para probar clasificaciones.
            if distancia == "6K":
                base_seconds = 22 * 60
                variation = (i * 73) % (34 * 60)
            elif distancia == "12K":
                base_seconds = 45 * 60
                variation = (i * 91) % (52 * 60)
            else:
                base_seconds = 72 * 60
                variation = (i * 113) % (78 * 60)
            tiempo = float(base_seconds + variation)
            hora_registro = (inicio_dt + timedelta(seconds=tiempo)).isoformat(timespec="seconds")

            tipo_registro = "QR" if i % 3 == 0 else "AUTOMATICO"
            tiempo_manual = None
            observacion = ""
            estado = "LLEGÓ"
            if i % 17 == 0:
                tipo_registro = "CORREGIDO"
                tiempo_manual = tiempo
                observacion = "Tiempo corregido en datos de prueba"
                estado = "CORREGIDO"

            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO llegadas(id_inscripcion, tiempo_llegada, hora_registro, tipo_registro, tiempo_manual, observacion)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (id_inscripcion, tiempo, hora_registro, tipo_registro, tiempo_manual, observacion),
                )
                self.conn.execute(
                    "UPDATE inscripciones SET estado=? WHERE id_inscripcion=?",
                    (estado, id_inscripcion),
                )

        self.conn.execute(
            "UPDATE carreras SET estado='Finalizada', hora_fin=? WHERE id_carrera=?",
            (fin_dt.isoformat(timespec="seconds"), race_id),
        )
        self.conn.commit()
        return race_id


def row_to_runner_display(row: sqlite3.Row) -> tuple:
    edad = calculate_age(row["fecha_nacimiento"], row["fecha_carrera"])
    return (
        row["id_inscripcion"],
        format_dni(row["dni"]),
        row["apellido"],
        row["nombre"],
        row["sexo"],
        row["ciudad"] or "",
        edad,
        row["team"] or "",
        row["distancia"],
        row["talle"] or "",
        row["categoria"],
        row["numero"],
        row["estado"],
    )
