MODELO DE DATOS
Sistema de Gestión y Clasificación de Carreras Deportivas

============================================================
1. DESCRIPCIÓN GENERAL
============================================================

La base de datos almacena información relacionada con carreras,
corredores, inscripciones y resultados.

============================================================
2. TABLAS PRINCIPALES
============================================================

TABLA: Carreras

Campos:

id_carrera (PK)
nombre
fecha
lugar
distancias
estado
hora_inicio
hora_fin

Descripción:

Almacena la información general de cada carrera.

------------------------------------------------------------

TABLA: Corredores

Campos:

id_corredor (PK)
dni
apellido
nombre
sexo
ciudad
fecha_nacimiento
team

Descripción:

Almacena los datos personales de cada corredor.

------------------------------------------------------------

TABLA: Inscripciones

Campos:

id_inscripcion (PK)
id_carrera (FK)
id_corredor (FK)

numero
distancia
categoria
talle
estado

Descripción:

Relaciona corredores con carreras.

Permite asignar número, distancia y categoría.

------------------------------------------------------------

TABLA: Llegadas

Campos:

id_llegada (PK)
id_inscripcion (FK)

tiempo_llegada
hora_registro
tipo_registro
tiempo_manual
observacion

Descripción:

Almacena los tiempos registrados para cada corredor.

============================================================
3. RELACIONES
============================================================

Carrera
1 ---- N
Inscripciones

Corredor
1 ---- N
Inscripciones

Inscripción
1 ---- 1
Llegada


============================================================
4. REGLAS DE NEGOCIO
============================================================

- Un corredor se identifica mediante su DNI.
- Un corredor puede participar en múltiples carreras.
- Un corredor no puede inscribirse dos veces en la misma carrera.
- No puede existir más de un número de corredor repetido dentro de una misma carrera.
- Las categorías se asignan automáticamente según la edad del corredor al momento de la

============================================================
5. ESTADOS DE CARRERA
============================================================

Creada
Iniciada
Finalizada

============================================================
6. ESTADOS DE INSCRIPCIÓN
============================================================

INSCRIPTO
LLEGÓ
DNS
DNF
DSQ
SIN TIEMPO
CORREGIDO

============================================================
7. TIPOS DE REGISTRO DE LLEGADA
============================================================

AUTOMATICO
MANUAL
QR
CORREGIDO

============================================================
8. CATEGORÍAS
============================================================

16 - 19 años
20 - 24 años
25 - 29 años
30 - 34 años
35 - 39 años
40 - 44 años
45 - 49 años
50 - 54 años
55 - 59 años
60 - 64 años
65 - 69 años
70 años o más

Las categorías se asignan automáticamente según la edad del corredor en la fecha de realización de la carrera.

============================================================
9. DISTANCIAS DISPONIBLES
============================================================

- 6K
- 12K
- 18K