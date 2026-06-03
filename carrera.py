import validaciones
import time
from datetime import datetime
import mysql.connector
from db import get_conexion, CARRERA_ID

corredores = []



def pedir_talle():
    """
    Talles válidos
    """

    talles_validos = ["XS", "S", "M", "L", "XL", "XXL"]

    while True:

        talle = input(
            "Talle remera (XS/S/M/L/XL/XXL): "
        ).strip().upper()

        if talle in talles_validos:
            return talle

        print("ERROR: Talle inválido.")
def pedir_numero(mensaje):
    """
    Solo números enteros
    """

    while True:

        dato = input(mensaje).strip()

        if dato.isdigit():
            return int(dato)

        print("ERROR: Debe ingresar solo números.")
def pedir_numero_remera(corredores):
    """
    Número de remera válido y no repetido
    """

    while True:
        numero = pedir_numero("Número de remera: ")

        if numero <= 0:
            print("ERROR: El número de remera debe ser mayor a 0.")
            continue

        # Verificar si el número de remera ya existe en la lista de corredores
        if any(corredor.numero_remera == numero for corredor in corredores):
            print("ERROR: Ese número de remera ya está registrado.")
            continue

        return numero

print("1.Registrar nuevo corredor")
print ("2.Iniciar cronometraje")


y = int(input("Seleccione una opción: "))
if (y == 1):
        dni      = input("DNI: ")
        apellido = validaciones.pedir_texto("Apellido: ")
        nombre   = validaciones.pedir_texto("Nombre: ")
        sexo     = validaciones.pedir_sexo()
        ciudad   = input("Ciudad: ").strip()

        while True:
            fecha_str = input("Fecha de nacimiento (dd/mm/aaaa): ").strip()
            try:
                fecha_nacimiento = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                break
            except ValueError:
                print("ERROR: Formato inválido. Use dd/mm/aaaa.")

        team             = input("Team: ").strip()
        distancia_nombre = validaciones.pedir_distancia()
        talle            = pedir_talle()
        numero_remera    = pedir_numero_remera(corredores)

        conexion_mysql = None
        cursor_mysql   = None

        try:
            conexion_mysql = get_conexion()
            cursor_mysql   = conexion_mysql.cursor()

            distancia_map = {"6KM": 6.00, "12KM": 12.00, "18KM": 18.00}
            cursor_mysql.execute(
                "SELECT id FROM distancias WHERE carrera_id = %s AND distancia_km = %s",
                (CARRERA_ID, distancia_map[distancia_nombre])
            )
            row = cursor_mysql.fetchone()
            if not row:
                print("ERROR: Distancia no encontrada en la base de datos.")
            else:
                distancia_id = row[0]

                cursor_mysql.execute("""
                    INSERT INTO corredores (dni, apellido, nombre, sexo, ciudad, fecha_nacimiento, team, talle_remera, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (dni, apellido, nombre, sexo, ciudad, fecha_nacimiento, team, talle, 1))

                corredor_id = cursor_mysql.lastrowid

                cursor_mysql.execute("""
                    INSERT INTO inscripciones (corredor_id, distancia_id, numero_dorsal, estado)
                    VALUES (%s, %s, %s, %s)
                """, (corredor_id, distancia_id, numero_remera, 'inscripto'))

                conexion_mysql.commit()
                print("Corredor registrado en MySQL correctamente.")

        except mysql.connector.Error as e:
            print(f"Error de base de datos: {e}")

        finally:
            if cursor_mysql:
                cursor_mysql.close()
            if conexion_mysql:
                conexion_mysql.close()

        
        
if y == 2:

    z = input("¿Desea iniciar el cronometraje? (y/n): ".lower())

    if z == "y":

        inicio = time.time()

        while z == "y":

            entrada = input("Ingrese número de remera o 'stop': ").lower()

            if entrada == "stop":

                z = "n"


            else:

                x              = int(entrada)
                conexion_mysql = None
                cursor_mysql   = None

                try:
                    conexion_mysql = get_conexion()
                    cursor_mysql   = conexion_mysql.cursor()

                    cursor_mysql.execute("""
                        SELECT i.id, c.nombre
                        FROM inscripciones i
                        JOIN corredores c ON i.corredor_id = c.id
                        JOIN distancias d  ON i.distancia_id = d.id
                        WHERE i.numero_dorsal = %s AND d.carrera_id = %s
                    """, (x, CARRERA_ID))

                    inscripcion = cursor_mysql.fetchone()

                    if inscripcion is None:
                        print("ERROR: Corredor no encontrado.")
                    else:
                        inscripcion_id = inscripcion[0]
                        nombre         = inscripcion[1]

                        cursor_mysql.execute(
                            "SELECT id FROM llegadas WHERE inscripcion_id = %s",
                            (inscripcion_id,)
                        )
                        if cursor_mysql.fetchone():
                            print("Ese corredor ya registró llegada.")
                        else:
                            tiempo_llegada = datetime.now()

                            cursor_mysql.execute("""
                                INSERT INTO llegadas (inscripcion_id, usuario_id, tiempo_llegada, metodo_carga)
                                VALUES (%s, %s, %s, %s)
                            """, (inscripcion_id, None, tiempo_llegada, 'manual'))

                            conexion_mysql.commit()

                            print(x, nombre, "- Tiempo:", tiempo_llegada.strftime("%H:%M:%S"))

                except mysql.connector.Error as e:
                    print(f"Error de base de datos: {e}")

                finally:
                    if cursor_mysql:
                        cursor_mysql.close()
                    if conexion_mysql:
                        conexion_mysql.close()