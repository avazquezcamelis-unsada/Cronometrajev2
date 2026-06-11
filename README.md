[README.md](https://github.com/user-attachments/files/28835365/README.md)
# README - SISTEMA DE GESTIÓN Y CLASIFICACIÓN DE CARRERAS DEPORTIVAS

============================================================
1. PROYECTO
============================================================

SISTEMA DE GESTIÓN Y CLASIFICACIÓN DE CARRERAS DEPORTIVAS

============================================================
2. INTEGRANTES
============================================================

* Deleglise, Luca Agustin
* Di Palma, Valentina
* Paccapelo, Braian
* Lepiscopo, Fernando
* Rosset, Luciano Valentin
* Tapia Deleglise, Mateo Gabino
* Vazquez Camelis, Alejo

============================================================
3. OBJETIVO
============================================================

El sistema permite gestionar integralmente competencias deportivas,
administrando carreras, corredores, inscripciones y llegadas.

Además, genera automáticamente clasificaciones generales,
clasificaciones por categorías, podios y reportes exportables.

Está orientado a competencias de running y trail, permitiendo
trabajar con múltiples distancias dentro de una misma carrera.

============================================================
4. ALCANCE REAL DEL MVP
============================================================

FUNCIONALIDADES IMPLEMENTADAS

* Gestión de estados de carreras.
* Gestión de corredores.
* Gestión de estados de inscripciones.
* Clasificación automática por categorías etarias.
* Registro manual y automático de llegadas.
* Conversión y validación de tiempos.
* Generación de resultados generales.
* Generación de podios generales.
* Generación de podios por categoría.
* Exportación de reportes.
* Backup de base de datos.

LIMITACIONES ACTUALES

* Los tiempos deben cargarse manualmente.
* El sistema requiere acceso a la base de datos.
* No existe integración con hardware externo.

============================================================
5. FUNCIONALIDADES IMPLEMENTADAS
============================================================

5.1 Gestión de Carreras

* Crear carreras.
* Configurar nombre, fecha, lugar y distancias.
* Iniciar carreras.
* Finalizar carreras.
* Gestionar estados de carrera.

Estados disponibles:

* Creada
* Iniciada
* Finalizada

------------------------------------------------------------

5.2 Gestión de Corredores

* Alta de corredores.
* Administración de datos personales.
* Asociación a múltiples carreras.

Datos almacenados:

* DNI
* Apellido
* Nombre
* Sexo
* Ciudad
* Fecha de nacimiento
* Team

------------------------------------------------------------

5.3 Gestión de Inscripciones

* Inscripción de corredores.
* Asignación de números de corredor.
* Asignación automática de categorías.
* Gestión de estados de inscripción.

Estados disponibles:

* INSCRIPTO
* LLEGÓ
* DNS
* DNF
* DSQ
* SIN TIEMPO
* CORREGIDO

------------------------------------------------------------

5.4 Gestión de Llegadas

* Registro automático.
* Registro manual.
* Registro mediante QR (si está habilitado).
* Corrección manual de tiempos.

Información registrada:

* Tiempo registrado.
* Fecha y hora de registro.
* Tipo de registro.
* Observaciones.

Tipos de registro:

* AUTOMATICO
* MANUAL
* QR
* CORREGIDO

------------------------------------------------------------

5.5 Resultados y Clasificaciones

* Resultados generales.
* Clasificación por categorías.
* Filtrado por distancia.
* Filtrado por sexo.
* Filtrado por categoría.

------------------------------------------------------------

5.6 Podios

* Podios generales.
* Podios por categoría.

------------------------------------------------------------

5.7 Reportes

* Exportación de resultados.
* Backup de base de datos.

============================================================
6. FUNCIONALIDADES FUERA DE ALCANCE
============================================================

* Cronometraje mediante hardware externo.
* Resultados online en tiempo real.
* Aplicación móvil.
* Gestión multiusuario.
* Sincronización entre dispositivos.
* Operación offline/online.

============================================================
7. TECNOLOGÍAS UTILIZADAS
============================================================

Según el alcance definido para el MVP:

* Python     
* Tkinter   
* SQLite       
* Visual Studio Code 
* QR / Código de barras 2D
* Lector NICTOM LCB6200 
* CSV / Excel 
* PDF / TXT     
* Sistema de backup 
* PyInstaller

============================================================
8. INSTRUCCIONES DE INSTALACIÓN
============================================================

1. Clonar o descargar el repositorio.
2. Instalar las dependencias requeridas (ejecutar_windows.bat).
3. Ejecutar la aplicación.


pip install Tkinter openpyxl reportlab


============================================================
9. INSTRUCCIONES DE EJECUCIÓN
============================================================

1. Abrir el archivo main.py
2. Ejecutar *Run Python File*

============================================================
10. ESTRUCTURA DEL REPOSITORIO
============================================================

proyecto/

│
├── docs/
│   ├── ALCANCE_MVP.md
│   ├── MANUAL_USUARIO.md
│   └── MODELOS_DATOS.md
│
├── README.md
│
└── src/

(Ajustar según la estructura real del repositorio)

============================================================
11. CREACIÓN DE BASE DE DATOS
============================================================

TABLAS PRINCIPALES

------------------------------------------------------------

Carreras

* id_carrera (PK)
* nombre
* fecha
* lugar
* distancias
* estado
* hora_inicio
* hora_fin

Descripción:

Almacena la información general de cada carrera.

------------------------------------------------------------

Corredores

* id_corredor (PK)
* dni
* apellido
* nombre
* sexo
* ciudad
* fecha_nacimiento
* team

Descripción:

Almacena los datos personales de cada corredor.

------------------------------------------------------------

Inscripciones

* id_inscripcion (PK)
* id_carrera (FK)
* id_corredor (FK)
* numero
* distancia
* categoria
* talle
* estado

Descripción:

Relaciona corredores con carreras.

Permite asignar número, distancia y categoría.

------------------------------------------------------------

Llegadas

* id_llegada (PK)
* id_inscripcion (FK)
* tiempo_llegada
* hora_registro
* tipo_registro
* tiempo_manual
* observacion

Descripción:

Almacena los tiempos registrados para cada corredor.

------------------------------------------------------------

RELACIONES

Carrera
1 ---- N
Inscripciones

Corredor
1 ---- N
Inscripciones

Inscripción
1 ---- 1
Llegada

------------------------------------------------------------

REGLAS DE NEGOCIO

* Un corredor se identifica por DNI.
* Un corredor puede participar en múltiples carreras.
* No puede inscribirse dos veces en una misma carrera.
* No puede existir un número repetido dentro de una carrera.
* Las categorías se asignan automáticamente según la edad.

============================================================
12. DATOS DE PRUEBA
============================================================

Carrera de ejemplo

Nombre: Carrera Ciudad 2026
Fecha: 15/10/2026
Lugar: Arrecifes
Distancias: 6K - 12K - 18K

------------------------------------------------------------

Corredor de ejemplo

DNI: 12345678
Apellido: Pérez
Nombre: Juan
Sexo: Masculino
Ciudad: Arrecifes
Fecha de nacimiento: 10/05/1995

------------------------------------------------------------

Inscripción

Número: 101
Distancia: 12K
Categoría: 30 - 34 años

============================================================
13. CAPTURAS DE PANTALLA
============================================================

Agregar capturas de:

* Pantalla principal.
* Gestión de carreras.
* Gestión de corredores.
* Inscripciones.
* Registro de llegadas.
* Resultados.
* Podios.
* Exportación de reportes.



![Pantalla Principal](docs/img/principal.png)

============================================================
14. MEJORAS FUTURAS
============================================================

* Cronometraje en tiempo real.
* Integración con hardware especializado.
* Aplicación móvil.
* Portal web de resultados.
* Gestión avanzada de estadísticas.
* Gestión multiusuario.
* Dashboard de métricas y rendimiento.

============================================================
15. VIDEO DEMOSTRATIVO
============================================================

Enlace al video de presentación:

https://youtu.be/QurkFpIYpmc

============================================================
16. FLUJO GENERAL DEL SISTEMA
============================================================

Carrera
↓
Corredores
↓
Inscripciones
↓
Inicio de Carrera
↓
Registro de Llegadas
↓
Resultados
↓
Clasificaciones
↓
Podios
↓
Exportación de Reportes

============================================================
17. ESTADOS DEL SISTEMA
============================================================

ESTADOS DE CARRERA

* Creada
* Iniciada
* Finalizada

------------------------------------------------------------

ESTADOS DE INSCRIPCIÓN

* INSCRIPTO
* LLEGÓ
* DNS (No largó)
* DNF (No finalizó)
* DSQ (Descalificado)
* SIN TIEMPO
* CORREGIDO

------------------------------------------------------------

TIPOS DE REGISTRO

* AUTOMATICO
* MANUAL
* QR
* CORREGIDO

============================================================
18. CATEGORÍAS ETARIAS
============================================================

* 16 - 19 años
* 20 - 24 años
* 25 - 29 años
* 30 - 34 años
* 35 - 39 años
* 40 - 44 años
* 45 - 49 años
* 50 - 54 años
* 55 - 59 años
* 60 - 64 años
* 65 - 69 años
* 70 años o más

Las categorías se asignan automáticamente según la edad
del corredor en la fecha de realización de la carrera.

============================================================
19. DISTANCIAS DISPONIBLES
============================================================

* 6K
* 12K
* 18K

============================================================
20. CRÉDITOS
============================================================

Materia:
Ingeniería de Software

Institución:
[UNSAdA]

Año:
2026

Autores:

* Deleglise, Luca Agustin
* Di Palma, Valentina
* Paccapelo, Braian
* Lepiscopo, Fernando
* Rosset, Luciano Valentin
* Tapia Deleglise, Mateo Gabino
* Vazquez Camelis, Alejo
