from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

from .database import DATA_DIR, DB_PATH, Database, row_to_runner_display
from .exporters import EXPORTS_DIR, export_excel, export_pdf
from .utils import (
    DISTANCIAS,
    ESTADOS_CARRERA,
    ESTADOS_INSCRIPCION,
    SEXOS,
    TALLES,
    calculate_age,
    date_to_db,
    elapsed_since,
    format_date,
    format_dni,
    iso_to_display,
    manual_parts_to_seconds,
    normalize_number,
    parse_date,
    seconds_to_time,
)


class CronometrajeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cronometraje de Atletismo")
        self.geometry("1180x760")
        self.minsize(1100, 680)
        self.db = Database()
        self.active_race_id: Optional[int] = None
        self.active_race_label = tk.StringVar(value="Sin carrera abierta")
        self.timer_text = tk.StringVar(value="00:00:00.00")
        self.selected_enrollment_id: Optional[int] = None
        self.selected_arrival_id: Optional[int] = None
        self._build_styles()
        self._build_ui()
        self.refresh_races()
        self.after(200, self._tick_timer)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_styles(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("BigTimer.TLabel", font=("Consolas", 38, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(10, 8))
        header.pack(fill="x")
        ttk.Label(header, text="Cronometraje", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.active_race_label).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tab_carrera = ttk.Frame(self.tabs, padding=10)
        self.tab_corredores = ttk.Frame(self.tabs, padding=10)
        self.tab_crono = ttk.Frame(self.tabs, padding=10)
        self.tab_resultados = ttk.Frame(self.tabs, padding=10)
        self.tab_backup = ttk.Frame(self.tabs, padding=10)

        self.tabs.add(self.tab_carrera, text="Crear / Abrir Carrera")
        self.tabs.add(self.tab_corredores, text="Registro de Corredores")
        self.tabs.add(self.tab_crono, text="Cronómetro / Llegadas")
        self.tabs.add(self.tab_resultados, text="Resultados / Reportes")
        self.tabs.add(self.tab_backup, text="Backup")

        self._build_carrera_tab()
        self._build_corredores_tab()
        self._build_crono_tab()
        self._build_resultados_tab()
        self._build_backup_tab()

    def _pack_tree_with_scrollbars(self, parent: ttk.Frame, tree: ttk.Treeview) -> None:
        """Agrega barras vertical y horizontal a las tablas grandes."""
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

    # ------------------------- Carrera -------------------------
    def _build_carrera_tab(self):
        left = ttk.LabelFrame(self.tab_carrera, text="Nueva / editar carrera", padding=10)
        left.pack(side="left", fill="y", padx=(0, 10))
        right = ttk.LabelFrame(self.tab_carrera, text="Carreras cargadas", padding=10)
        right.pack(side="left", fill="both", expand=True)

        self.race_form = {}
        fields = [
            ("nombre", "Nombre", "Cronos Cross Trail 2026"),
            ("fecha", "Fecha", "10/11/2026"),
            ("lugar", "Lugar", "Arrecifes, Buenos Aires"),
        ]
        for r, (key, label, default) in enumerate(fields):
            ttk.Label(left, text=label).grid(row=r, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=default)
            entry = ttk.Entry(left, textvariable=var, width=34)
            entry.grid(row=r, column=1, sticky="ew", pady=4)
            self.race_form[key] = var

        ttk.Label(left, text="Distancias").grid(row=3, column=0, sticky="nw", pady=4)
        self.distance_vars = {d: tk.BooleanVar(value=True) for d in DISTANCIAS}
        dist_frame = ttk.Frame(left)
        dist_frame.grid(row=3, column=1, sticky="w", pady=4)
        for d in DISTANCIAS:
            ttk.Checkbutton(dist_frame, text=d, variable=self.distance_vars[d]).pack(side="left", padx=(0, 8))

        ttk.Label(left, text="Estado").grid(row=4, column=0, sticky="w", pady=4)
        self.race_estado_var = tk.StringVar(value="Creada")
        ttk.Combobox(left, textvariable=self.race_estado_var, values=ESTADOS_CARRERA, state="readonly", width=31).grid(row=4, column=1, sticky="w", pady=4)

        btns = ttk.Frame(left)
        btns.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(btns, text="Agregar carrera", style="Accent.TButton", command=self.add_race).pack(fill="x", pady=2)
        ttk.Button(btns, text="Modificar seleccionada", command=self.update_selected_race).pack(fill="x", pady=2)
        ttk.Button(btns, text="Eliminar seleccionada", command=self.delete_selected_race).pack(fill="x", pady=2)
        ttk.Button(btns, text="Cargar datos de prueba", command=self.seed_demo).pack(fill="x", pady=(12, 2))
        ttk.Button(btns, text="Exportar Excel", command=self.export_active_excel).pack(fill="x", pady=2)

        cols = ("id", "nombre", "fecha", "lugar", "distancias", "estado", "inicio", "fin")
        races_table = ttk.Frame(right)
        races_table.pack(fill="both", expand=True)
        self.races_tree = ttk.Treeview(races_table, columns=cols, show="headings", selectmode="browse")
        headers = ["ID", "Nombre", "Fecha", "Lugar", "Distancias", "Estado", "Hora inicio", "Hora fin"]
        widths = [50, 220, 90, 180, 120, 90, 140, 140]
        for c, h, w in zip(cols, headers, widths):
            self.races_tree.heading(c, text=h)
            self.races_tree.column(c, width=w, anchor="w")
        self._pack_tree_with_scrollbars(races_table, self.races_tree)
        self.races_tree.bind("<<TreeviewSelect>>", self.on_race_select)
        self.races_tree.bind("<Double-1>", lambda e: self.open_selected_race())

        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Abrir seleccionada", style="Accent.TButton", command=self.open_selected_race).pack(side="left")
        ttk.Button(bottom, text="Actualizar", command=self.refresh_races).pack(side="left", padx=6)

    def selected_distances(self) -> list[str]:
        return [d for d, var in self.distance_vars.items() if var.get()]

    def add_race(self):
        try:
            nombre = self.race_form["nombre"].get().strip()
            if not nombre:
                raise ValueError("El nombre de carrera es obligatorio")
            parse_date(self.race_form["fecha"].get())
            distancias = self.selected_distances()
            if not distancias:
                raise ValueError("Seleccioná al menos una distancia")
            race_id = self.db.create_race(nombre, self.race_form["fecha"].get(), self.race_form["lugar"].get(), distancias)
            self.active_race_id = race_id
            self.refresh_races()
            self.refresh_all()
            messagebox.showinfo("Carrera", "Carrera creada y abierta correctamente")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def get_selected_race_id(self) -> Optional[int]:
        sel = self.races_tree.selection()
        if not sel:
            return None
        return int(self.races_tree.item(sel[0], "values")[0])

    def on_race_select(self, _event=None):
        race_id = self.get_selected_race_id()
        if not race_id:
            return
        race = self.db.get_race(race_id)
        if not race:
            return
        self.race_form["nombre"].set(race["nombre"])
        self.race_form["fecha"].set(format_date(race["fecha"]))
        self.race_form["lugar"].set(race["lugar"] or "")
        self.race_estado_var.set(race["estado"])
        selected = set((race["distancias"] or "").split(","))
        for d, var in self.distance_vars.items():
            var.set(d in selected)

    def open_selected_race(self):
        race_id = self.get_selected_race_id()
        if not race_id:
            messagebox.showwarning("Carrera", "Seleccioná una carrera")
            return
        self.active_race_id = race_id
        self.refresh_all()
        self.tabs.select(self.tab_corredores)

    def update_selected_race(self):
        race_id = self.get_selected_race_id()
        if not race_id:
            messagebox.showwarning("Carrera", "Seleccioná una carrera")
            return
        try:
            self.db.update_race(
                race_id,
                self.race_form["nombre"].get(),
                self.race_form["fecha"].get(),
                self.race_form["lugar"].get(),
                self.selected_distances(),
                self.race_estado_var.get(),
            )
            self.refresh_all()
            messagebox.showinfo("Carrera", "Carrera modificada")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_selected_race(self):
        race_id = self.get_selected_race_id()
        if not race_id:
            messagebox.showwarning("Carrera", "Seleccioná una carrera")
            return
        if not messagebox.askyesno("Eliminar", "¿Seguro que desea eliminar esta carrera?"):
            return
        self.db.delete_race(race_id)
        if self.active_race_id == race_id:
            self.active_race_id = None
        self.refresh_all()

    def seed_demo(self):
        if not messagebox.askyesno("Datos de prueba", "Se cargará una carrera de prueba FINALIZADA con 100 corredores y 100 llegadas. ¿Continuar?"):
            return
        try:
            self.active_race_id = self.db.seed_demo_data()
            self.refresh_all()
            messagebox.showinfo("Datos de prueba", "Carrera finalizada de prueba cargada: 100 corredores y 100 llegadas")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def refresh_races(self):
        self.races_tree.delete(*self.races_tree.get_children())
        for row in self.db.list_races():
            self.races_tree.insert("", "end", values=(
                row["id_carrera"], row["nombre"], format_date(row["fecha"]), row["lugar"], row["distancias"], row["estado"],
                iso_to_display(row["hora_inicio"]), iso_to_display(row["hora_fin"]),
            ))
        self.update_active_label()

    # ------------------------- Corredores -------------------------
    def _build_corredores_tab(self):
        form = ttk.LabelFrame(self.tab_corredores, text="Carga de corredor", padding=10)
        form.pack(fill="x")
        table_frame = ttk.LabelFrame(self.tab_corredores, text="Registro de corredores", padding=10)
        table_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.runner_vars = {}
        specs = [
            ("dni", "DNI", 0, 0, "00.000.000"),
            ("apellido", "Apellido", 0, 2, "Apellido"),
            ("nombre", "Nombre", 0, 4, "Nombre"),
            ("sexo", "Sexo", 1, 0, "M"),
            ("ciudad", "Ciudad", 1, 2, "Ciudad"),
            ("fecha_nacimiento", "Fecha nacimiento", 1, 4, "00/00/0000"),
            ("team", "Team", 2, 0, "Teams"),
            ("distancia", "KM", 2, 2, "...K"),
            ("talle", "Talle", 2, 4, "S"),
            ("numero", "Nº", 3, 0, "001"),
            ("estado", "Estado", 3, 2, "Ver"),
        ]
        for key, label, r, c, default in specs:
            ttk.Label(form, text=label).grid(row=r, column=c, sticky="w", padx=(0, 4), pady=3)
            var = tk.StringVar(value=default)
            self.runner_vars[key] = var
            if key == "sexo":
                widget = ttk.Combobox(form, textvariable=var, values=SEXOS, state="readonly", width=16)
            elif key == "distancia":
                widget = ttk.Combobox(form, textvariable=var, values=DISTANCIAS, state="readonly", width=16)
            elif key == "talle":
                widget = ttk.Combobox(form, textvariable=var, values=TALLES, state="readonly", width=16)
            elif key == "estado":
                widget = ttk.Combobox(form, textvariable=var, values=ESTADOS_INSCRIPCION, state="readonly", width=16)
            else:
                widget = ttk.Entry(form, textvariable=var, width=20)
            widget.grid(row=r, column=c + 1, sticky="w", padx=(0, 12), pady=3)

        actions = ttk.Frame(form)
        actions.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        ttk.Button(actions, text="Agregar nuevo", style="Accent.TButton", command=self.add_runner).pack(side="left")
        ttk.Button(actions, text="Modificar", command=self.update_runner).pack(side="left", padx=6)
        ttk.Button(actions, text="Eliminar", command=self.delete_runner).pack(side="left")
        ttk.Button(actions, text="Limpiar", command=self.clear_runner_form).pack(side="left", padx=6)
        ttk.Button(actions, text="Exportar a Excel", command=self.export_active_excel).pack(side="right")

        search_frame = ttk.Frame(table_frame)
        search_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(search_frame, text="Buscar").pack(side="left")
        self.runner_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.runner_search_var, width=40)
        search_entry.pack(side="left", padx=6)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_runners())
        ttk.Button(search_frame, text="Actualizar", command=self.refresh_runners).pack(side="left")

        cols = ("id", "dni", "apellido", "nombre", "sexo", "ciudad", "edad", "team", "km", "talle", "categoria", "numero", "estado")
        runners_table = ttk.Frame(table_frame)
        runners_table.pack(fill="both", expand=True)
        self.runners_tree = ttk.Treeview(runners_table, columns=cols, show="headings", selectmode="browse")
        headers = ["ID", "DNI", "Apellido", "Nombre", "Sexo", "Ciudad", "Edad calculada", "Team", "KM", "Talle", "Categoría", "Nº", "Estado"]
        widths = [45, 100, 120, 120, 50, 120, 100, 100, 55, 60, 85, 60, 90]
        for c, h, w in zip(cols, headers, widths):
            self.runners_tree.heading(c, text=h)
            self.runners_tree.column(c, width=w, anchor="w")
        self._pack_tree_with_scrollbars(runners_table, self.runners_tree)
        self.runners_tree.bind("<<TreeviewSelect>>", self.on_runner_select)

    def ensure_active_race(self) -> bool:
        if not self.active_race_id:
            messagebox.showwarning("Carrera", "Primero creá o abrí una carrera")
            self.tabs.select(self.tab_carrera)
            return False
        return True

    def add_runner(self):
        if not self.ensure_active_race():
            return
        try:
            self.db.create_or_enroll_runner(
                self.active_race_id,
                self.runner_vars["dni"].get(),
                self.runner_vars["apellido"].get(),
                self.runner_vars["nombre"].get(),
                self.runner_vars["sexo"].get(),
                self.runner_vars["ciudad"].get(),
                self.runner_vars["fecha_nacimiento"].get(),
                self.runner_vars["team"].get(),
                self.runner_vars["distancia"].get(),
                self.runner_vars["numero"].get(),
                self.runner_vars["talle"].get(),
            )
            self.refresh_all()
            self.clear_runner_form(keep_defaults=True)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def update_runner(self):
        if not self.selected_enrollment_id:
            messagebox.showwarning("Corredor", "Seleccioná un corredor")
            return
        try:
            self.db.update_enrollment(
                self.selected_enrollment_id,
                self.runner_vars["dni"].get(),
                self.runner_vars["apellido"].get(),
                self.runner_vars["nombre"].get(),
                self.runner_vars["sexo"].get(),
                self.runner_vars["ciudad"].get(),
                self.runner_vars["fecha_nacimiento"].get(),
                self.runner_vars["team"].get(),
                self.runner_vars["distancia"].get(),
                self.runner_vars["numero"].get(),
                self.runner_vars["talle"].get(),
                self.runner_vars["estado"].get(),
            )
            self.refresh_all()
            messagebox.showinfo("Corredor", "Corredor modificado")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_runner(self):
        if not self.selected_enrollment_id:
            messagebox.showwarning("Corredor", "Seleccioná un corredor")
            return
        if not messagebox.askyesno("Eliminar", "¿Seguro que desea eliminar este corredor?"):
            return
        self.db.delete_enrollment(self.selected_enrollment_id)
        self.selected_enrollment_id = None
        self.refresh_all()
        self.clear_runner_form()

    def clear_runner_form(self, keep_defaults: bool = False):
        values = {
            "dni": "", "apellido": "", "nombre": "", "sexo": "M", "ciudad": "", "fecha_nacimiento": "",
            "team": "", "distancia": "6K", "talle": "", "numero": "", "estado": "INSCRIPTO",
        }
        if keep_defaults:
            # Sugiere próximo número.
            numbers = []
            if self.active_race_id:
                for row in self.db.list_enrollments(self.active_race_id):
                    try:
                        numbers.append(int(row["numero"]))
                    except Exception:
                        pass
            values["numero"] = str((max(numbers) + 1) if numbers else 1).zfill(3)
        for k, v in values.items():
            self.runner_vars[k].set(v)
        self.selected_enrollment_id = None

    def on_runner_select(self, _event=None):
        sel = self.runners_tree.selection()
        if not sel:
            return
        values = self.runners_tree.item(sel[0], "values")
        id_ins = int(values[0])
        row = self.db.get_enrollment(id_ins)
        if not row:
            return
        self.selected_enrollment_id = id_ins
        self.runner_vars["dni"].set(format_dni(row["dni"]))
        self.runner_vars["apellido"].set(row["apellido"])
        self.runner_vars["nombre"].set(row["nombre"])
        self.runner_vars["sexo"].set(row["sexo"])
        self.runner_vars["ciudad"].set(row["ciudad"] or "")
        self.runner_vars["fecha_nacimiento"].set(format_date(row["fecha_nacimiento"]))
        self.runner_vars["team"].set(row["team"] or "")
        self.runner_vars["distancia"].set(row["distancia"])
        self.runner_vars["talle"].set(row["talle"] or "")
        self.runner_vars["numero"].set(row["numero"])
        self.runner_vars["estado"].set(row["estado"])

    def refresh_runners(self):
        self.runners_tree.delete(*self.runners_tree.get_children())
        if not self.active_race_id:
            return
        for row in self.db.list_enrollments(self.active_race_id, self.runner_search_var.get()):
            self.runners_tree.insert("", "end", values=row_to_runner_display(row))

    # ------------------------- Cronómetro -------------------------
    def _build_crono_tab(self):
        top = ttk.Frame(self.tab_crono)
        top.pack(fill="x")
        left = ttk.LabelFrame(top, text="Cronómetro", padding=10)
        left.pack(side="left", fill="y", padx=(0, 10))
        right = ttk.LabelFrame(top, text="Ingreso de llegada", padding=10)
        right.pack(side="left", fill="both", expand=True)
        bottom = ttk.LabelFrame(self.tab_crono, text="Llegadas registradas", padding=10)
        bottom.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(left, textvariable=self.timer_text, style="BigTimer.TLabel").pack(pady=(0, 12))
        ttk.Button(left, text="INICIAR", style="Accent.TButton", command=self.start_race).pack(fill="x", pady=3)
        ttk.Button(left, text="FINALIZAR", command=self.finalize_race).pack(fill="x", pady=3)
        ttk.Button(left, text="Exportar a Excel", command=self.export_active_excel).pack(fill="x", pady=(12, 3))
        ttk.Button(left, text="Generar PDF", command=self.export_active_pdf).pack(fill="x", pady=3)

        ttk.Label(right, text="Nº corredor / QR").grid(row=0, column=0, sticky="w")
        self.arrival_number_var = tk.StringVar()
        arrival_entry = ttk.Entry(right, textvariable=self.arrival_number_var, font=("Segoe UI", 18), width=12)
        arrival_entry.grid(row=1, column=0, sticky="w", pady=(2, 10))
        arrival_entry.bind("<Return>", lambda e: self.register_arrival())
        ttk.Button(right, text="Registrar llegada", style="Accent.TButton", command=self.register_arrival).grid(row=1, column=1, sticky="w", padx=8, pady=(2, 10))

        ttk.Separator(right).grid(row=2, column=0, columnspan=5, sticky="ew", pady=8)
        ttk.Label(right, text="Ingreso manual / corrección").grid(row=3, column=0, columnspan=5, sticky="w", pady=(0, 6))
        self.manual_vars = {k: tk.StringVar(value="0") for k in ("hs", "min", "seg", "cen")}
        labels = [("hs", "HS"), ("min", "MIN"), ("seg", "SEG"), ("cen", "CEN")]
        for i, (key, label) in enumerate(labels):
            ttk.Label(right, text=label).grid(row=4, column=i, sticky="w")
            ttk.Entry(right, textvariable=self.manual_vars[key], width=7).grid(row=5, column=i, sticky="w", padx=(0, 6))
        ttk.Button(right, text="Guardar manual", command=self.register_manual_arrival).grid(row=5, column=4, sticky="w", padx=8)
        ttk.Label(right, text="Observación").grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.manual_obs_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.manual_obs_var, width=55).grid(row=7, column=0, columnspan=5, sticky="ew")

        ttk.Button(right, text="Eliminar llegada seleccionada", command=self.delete_selected_arrival).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

        cols = ("id", "tiempo", "numero", "distancia", "categoria", "sexo", "apellido", "nombre", "ciudad", "tipo", "hora")
        arrivals_table = ttk.Frame(bottom)
        arrivals_table.pack(fill="both", expand=True)
        self.arrivals_tree = ttk.Treeview(arrivals_table, columns=cols, show="headings", selectmode="browse")
        headers = ["ID", "Tiempo", "Nº", "Distancia", "Categoría", "Sexo", "Apellido", "Nombre", "Ciudad", "Tipo", "Hora registro"]
        widths = [50, 100, 60, 80, 90, 50, 120, 120, 130, 100, 150]
        for c, h, w in zip(cols, headers, widths):
            self.arrivals_tree.heading(c, text=h)
            self.arrivals_tree.column(c, width=w, anchor="w")
        self._pack_tree_with_scrollbars(arrivals_table, self.arrivals_tree)
        self.arrivals_tree.bind("<<TreeviewSelect>>", self.on_arrival_select)

    def start_race(self):
        if not self.ensure_active_race():
            return
        try:
            race = self.db.get_race(self.active_race_id)
            if not race:
                raise ValueError("No se encontró la carrera")
            if race["estado"] == "Finalizada":
                raise ValueError("La carrera ya está finalizada")
            if not messagebox.askyesno("Iniciar", "¿Confirmás iniciar la carrera?"):
                return
            self.db.start_race(self.active_race_id)
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def finalize_race(self):
        if not self.ensure_active_race():
            return
        try:
            if not messagebox.askyesno("Finalizar", "¿Confirmás finalizar la carrera? Se bloquearán nuevas llegadas."):
                return
            self.db.finalize_race(self.active_race_id)
            self.refresh_all()
            path = export_pdf(self.db, self.active_race_id, "todos")
            messagebox.showinfo("Finalizada", f"Carrera finalizada. PDF generado:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def register_arrival(self):
        if not self.ensure_active_race():
            return
        try:
            race = self.db.get_race(self.active_race_id)
            if not race:
                raise ValueError("No se encontró la carrera")
            if race["estado"] != "Iniciada":
                raise ValueError("La carrera debe estar iniciada para registrar llegadas")
            number = normalize_number(self.arrival_number_var.get())
            if not number:
                raise ValueError("Ingresá el número de corredor")
            enrollment = self.db.get_enrollment_by_number(self.active_race_id, number)
            if not enrollment:
                raise ValueError("No existe un corredor con ese número")
            if self.db.arrival_exists(enrollment["id_inscripcion"]):
                raise ValueError("Este corredor ya tiene una llegada registrada")
            elapsed = elapsed_since(race["hora_inicio"])
            self.db.create_arrival(enrollment["id_inscripcion"], elapsed, "AUTOMATICO")
            self.arrival_number_var.set("")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Llegada", str(exc))

    def register_manual_arrival(self):
        if not self.ensure_active_race():
            return
        try:
            number = normalize_number(self.arrival_number_var.get())
            if not number:
                raise ValueError("Ingresá el número de corredor")
            enrollment = self.db.get_enrollment_by_number(self.active_race_id, number)
            if not enrollment:
                raise ValueError("No existe un corredor con ese número")
            tiempo = manual_parts_to_seconds(
                self.manual_vars["hs"].get(),
                self.manual_vars["min"].get(),
                self.manual_vars["seg"].get(),
                self.manual_vars["cen"].get(),
            )
            self.db.upsert_manual_arrival(enrollment["id_inscripcion"], tiempo, self.manual_obs_var.get())
            self.arrival_number_var.set("")
            self.manual_obs_var.set("")
            self.refresh_all()
            messagebox.showinfo("Llegada", "Tiempo manual guardado")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_selected_arrival(self):
        if not self.selected_arrival_id:
            messagebox.showwarning("Llegada", "Seleccioná una llegada")
            return
        if not messagebox.askyesno("Eliminar", "¿Seguro que desea eliminar esta llegada?"):
            return
        self.db.delete_arrival(self.selected_arrival_id)
        self.selected_arrival_id = None
        self.refresh_all()

    def on_arrival_select(self, _event=None):
        sel = self.arrivals_tree.selection()
        if not sel:
            return
        values = self.arrivals_tree.item(sel[0], "values")
        self.selected_arrival_id = int(values[0])
        self.arrival_number_var.set(values[2])
        tiempo = values[1].replace(".", ":")
        parts = tiempo.split(":")
        if len(parts) >= 4:
            self.manual_vars["hs"].set(parts[0])
            self.manual_vars["min"].set(parts[1])
            self.manual_vars["seg"].set(parts[2])
            self.manual_vars["cen"].set(parts[3])

    def refresh_arrivals(self):
        self.arrivals_tree.delete(*self.arrivals_tree.get_children())
        if not self.active_race_id:
            return
        for row in self.db.list_arrivals(self.active_race_id):
            self.arrivals_tree.insert("", "end", values=(
                row["id_llegada"], seconds_to_time(row["tiempo_llegada"]), row["numero"], row["distancia"], row["categoria"],
                row["sexo"], row["apellido"], row["nombre"], row["ciudad"], row["tipo_registro"], iso_to_display(row["hora_registro"]),
            ))

    # ------------------------- Resultados -------------------------
    def _build_resultados_tab(self):
        filters = ttk.LabelFrame(self.tab_resultados, text="Filtros", padding=10)
        filters.pack(fill="x")
        table = ttk.LabelFrame(self.tab_resultados, text="Tabla de posiciones", padding=10)
        table.pack(fill="both", expand=True, pady=(10, 0))

        self.result_distance_var = tk.StringVar(value="Todas")
        self.result_sex_var = tk.StringVar(value="Todos")
        self.result_category_var = tk.StringVar(value="Todas")
        ttk.Label(filters, text="Distancia").pack(side="left")
        ttk.Combobox(filters, textvariable=self.result_distance_var, values=["Todas"] + DISTANCIAS, state="readonly", width=12).pack(side="left", padx=6)
        ttk.Label(filters, text="Sexo").pack(side="left", padx=(10, 0))
        ttk.Combobox(filters, textvariable=self.result_sex_var, values=["Todos"] + SEXOS, state="readonly", width=10).pack(side="left", padx=6)
        ttk.Label(filters, text="Categoría").pack(side="left", padx=(10, 0))
        categorias = ["Todas", "16-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70 y mas"]
        ttk.Combobox(filters, textvariable=self.result_category_var, values=categorias, state="readonly", width=12).pack(side="left", padx=6)
        ttk.Button(filters, text="Actualizar", command=self.refresh_results).pack(side="left", padx=10)
        ttk.Button(filters, text="Exportar Excel", command=self.export_active_excel).pack(side="right")
        ttk.Button(filters, text="Generar PDF", command=self.export_active_pdf).pack(side="right", padx=6)

        cols = ("pos", "tiempo", "numero", "distancia", "categoria", "sexo", "apellido", "nombre", "ciudad", "tipo")
        results_table = ttk.Frame(table)
        results_table.pack(fill="both", expand=True)
        self.results_tree = ttk.Treeview(results_table, columns=cols, show="headings")
        headers = ["Pos", "Tiempo", "Nº", "KM", "Categoría", "Sexo", "Apellido", "Nombre", "Ciudad", "Tipo"]
        widths = [55, 100, 65, 70, 95, 55, 130, 130, 140, 100]
        for c, h, w in zip(cols, headers, widths):
            self.results_tree.heading(c, text=h)
            self.results_tree.column(c, width=w, anchor="w")
        self._pack_tree_with_scrollbars(results_table, self.results_tree)

    def refresh_results(self):
        self.results_tree.delete(*self.results_tree.get_children())
        if not self.active_race_id:
            return
        rows = self.db.list_results(
            self.active_race_id,
            self.result_distance_var.get(),
            self.result_sex_var.get(),
            self.result_category_var.get(),
        )
        # Posiciones se calculan dentro del filtro visible.
        for pos, row in enumerate(sorted(rows, key=lambda x: x["tiempo_llegada"]), start=1):
            self.results_tree.insert("", "end", values=(
                pos, seconds_to_time(row["tiempo_llegada"]), row["numero"], row["distancia"], row["categoria"], row["sexo"],
                row["apellido"], row["nombre"], row["ciudad"], row["tipo_registro"],
            ))

    # ------------------------- Backup -------------------------
    def _build_backup_tab(self):
        info = ttk.LabelFrame(self.tab_backup, text="Ubicación de datos", padding=12)
        info.pack(fill="x")

        self.backup_db_path_var = tk.StringVar(value=str(DB_PATH))
        self.backup_exports_path_var = tk.StringVar(value=str(EXPORTS_DIR))

        ttk.Label(info, text="Base actual:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(info, textvariable=self.backup_db_path_var, state="readonly", width=95).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(info, text="Excel / PDF:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(info, textvariable=self.backup_exports_path_var, state="readonly", width=95).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        info.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(self.tab_backup, text="Copia de seguridad", padding=12)
        actions.pack(fill="x", pady=(12, 0))

        ttk.Label(
            actions,
            text=(
                "Exportar crea un archivo .zip con la base cronometraje.db. "
                "Ese archivo sirve para llevar la carrera a otra máquina o guardar una copia de emergencia."
            ),
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        ttk.Button(
            actions,
            text="Exportar copia de seguridad",
            style="Accent.TButton",
            command=self.export_backup,
        ).pack(anchor="w")

        restore = ttk.LabelFrame(self.tab_backup, text="Restaurar información", padding=12)
        restore.pack(fill="x", pady=(12, 0))

        ttk.Label(
            restore,
            text=(
                "Importar reemplaza la base actual por una copia de seguridad. "
                "Antes de restaurar, el programa guarda automáticamente una copia de la base actual."
            ),
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        ttk.Button(
            restore,
            text="Importar / restaurar copia",
            command=self.import_backup,
        ).pack(anchor="w")

        notes = ttk.LabelFrame(self.tab_backup, text="Uso recomendado", padding=12)
        notes.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(
            notes,
            text=(
                "1. Antes de una carrera, exportá una copia de seguridad y guardala en un pendrive o nube.\n"
                "2. Durante la carrera, podés hacer copias de seguridad cada cierto tiempo.\n"
                "3. Si la PC falla, instalá el programa en otra máquina, entrá a Backup e importá el .zip.\n"
                "4. Al restaurar, la información queda como estaba al momento de generar el backup."
            ),
            justify="left",
        ).pack(anchor="w")

    def _update_backup_info(self):
        if hasattr(self, "backup_db_path_var"):
            self.backup_db_path_var.set(str(DB_PATH))
        if hasattr(self, "backup_exports_path_var"):
            self.backup_exports_path_var.set(str(EXPORTS_DIR))

    def _backup_filename(self) -> str:
        return f"backup_cronometraje_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    def export_backup(self):
        try:
            initial_dir = Path.home() / "Documents"
            if not initial_dir.exists():
                initial_dir = EXPORTS_DIR
            target = filedialog.asksaveasfilename(
                title="Guardar copia de seguridad",
                initialdir=str(initial_dir),
                initialfile=self._backup_filename(),
                defaultextension=".zip",
                filetypes=[("Backup Cronometraje", "*.zip"), ("Base SQLite", "*.db"), ("Todos los archivos", "*.*")],
            )
            if not target:
                return
            target_path = Path(target)
            if target_path.suffix.lower() == ".db":
                self.db.backup_to(target_path)
                messagebox.showinfo("Backup", f"Base exportada correctamente:\n{target_path}")
                return

            if target_path.suffix.lower() != ".zip":
                target_path = target_path.with_suffix(".zip")

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_db = Path(tmpdir) / "cronometraje.db"
                self.db.backup_to(tmp_db)
                manifest = Path(tmpdir) / "info_backup.txt"
                manifest.write_text(
                    "Backup Cronometraje Demo\n"
                    f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"Base original: {DB_PATH}\n",
                    encoding="utf-8",
                )
                with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(tmp_db, "cronometraje.db")
                    zf.write(manifest, "info_backup.txt")
            messagebox.showinfo("Backup", f"Copia de seguridad creada correctamente:\n{target_path}")
        except Exception as exc:
            messagebox.showerror("Backup", str(exc))

    def import_backup(self):
        try:
            source = filedialog.askopenfilename(
                title="Seleccionar copia de seguridad",
                filetypes=[("Backup Cronometraje", "*.zip *.db"), ("ZIP", "*.zip"), ("Base SQLite", "*.db"), ("Todos los archivos", "*.*")],
            )
            if not source:
                return
            source_path = Path(source)
            if not messagebox.askyesno(
                "Restaurar backup",
                "Esta acción reemplazará la base actual por la copia seleccionada.\n\n"
                "Antes de restaurar, se guardará una copia automática de la base actual.\n\n"
                "¿Querés continuar?",
            ):
                return

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                if source_path.suffix.lower() == ".zip":
                    candidate = self._extract_database_from_zip(source_path, tmpdir_path)
                else:
                    candidate = source_path

                Database.validate_database_file(candidate)

                auto_dir = DATA_DIR / "backups_automaticos"
                auto_name = f"antes_de_restaurar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                auto_path = auto_dir / auto_name
                self.db.backup_to(auto_path)

                self.db.close()
                try:
                    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(candidate, DB_PATH)
                finally:
                    self.db = Database()

            self.active_race_id = None
            self.selected_enrollment_id = None
            self.selected_arrival_id = None
            self.refresh_all()
            self.tabs.select(self.tab_carrera)
            messagebox.showinfo(
                "Backup",
                "Backup restaurado correctamente.\n\n"
                "La carrera quedó cerrada en pantalla; abrí la carrera que corresponda desde Crear / Abrir Carrera.",
            )
        except Exception as exc:
            try:
                # Asegura que el programa siga conectado a la base si hubo error a mitad del proceso.
                self.db.conn.execute("SELECT 1")
            except Exception:
                self.db = Database()
            messagebox.showerror("Backup", str(exc))

    def _extract_database_from_zip(self, zip_path: Path, destination: Path) -> Path:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = [name for name in zf.namelist() if not name.endswith("/")]
            selected = None
            if "cronometraje.db" in names:
                selected = "cronometraje.db"
            else:
                db_files = [name for name in names if name.lower().endswith(".db")]
                if db_files:
                    selected = db_files[0]
            if not selected:
                raise ValueError("El ZIP no contiene una base cronometraje.db")
            out_path = destination / "cronometraje_restaurar.db"
            with zf.open(selected) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            return out_path

    # ------------------------- Export / refresh -------------------------
    def export_active_excel(self):
        if not self.ensure_active_race():
            return
        try:
            path = export_excel(self.db, self.active_race_id)
            messagebox.showinfo("Excel", f"Archivo generado:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def export_active_pdf(self):
        if not self.ensure_active_race():
            return
        try:
            path = export_pdf(self.db, self.active_race_id, "todos")
            messagebox.showinfo("PDF", f"Archivo generado:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def refresh_all(self):
        self.refresh_races()
        self.refresh_runners()
        self.refresh_arrivals()
        self.refresh_results()
        self._update_backup_info()
        self.update_active_label()

    def update_active_label(self):
        if not self.active_race_id:
            self.active_race_label.set("Sin carrera abierta")
            return
        race = self.db.get_race(self.active_race_id)
        if not race:
            self.active_race_label.set("Sin carrera abierta")
            return
        self.active_race_label.set(f"Carrera abierta: {race['nombre']} | Estado: {race['estado']}")

    def _tick_timer(self):
        try:
            if self.active_race_id:
                race = self.db.get_race(self.active_race_id)
                if race and race["estado"] == "Iniciada" and race["hora_inicio"]:
                    self.timer_text.set(seconds_to_time(elapsed_since(race["hora_inicio"])))
                elif race and race["hora_inicio"] and race["hora_fin"]:
                    # Muestra duración aproximada hasta finalizar.
                    self.timer_text.set("FINALIZADA")
                else:
                    self.timer_text.set("00:00:00.00")
            else:
                self.timer_text.set("00:00:00.00")
        finally:
            self.after(200, self._tick_timer)

    def _on_close(self):
        self.db.close()
        self.destroy()
