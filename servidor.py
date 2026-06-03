from flask import Flask
import mysql.connector
from db import get_conexion, CARRERA_ID

app = Flask(__name__)

@app.route("/")
def tabla_posiciones():

    conexion_mysql = None
    cursor_mysql   = None

    try:
        conexion_mysql = get_conexion()
        cursor_mysql   = conexion_mysql.cursor()

        cursor_mysql.execute(
            "SELECT * FROM v_tabla_posiciones WHERE carrera_id = %s",
            (CARRERA_ID,)
        )

        filas    = cursor_mysql.fetchall()
        columnas = [col[0] for col in cursor_mysql.description]

        encabezados = "".join(f"<th>{col}</th>" for col in columnas)
        cuerpo = ""
        for fila in filas:
            cuerpo += "<tr>" + "".join(f"<td>{celda}</td>" for celda in fila) + "</tr>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="10">
    <title>Tabla de posiciones</title>
    <style>
        body  {{ font-family: Arial, sans-serif; padding: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #333; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Tabla de posiciones</h1>
    <table>
        <thead><tr>{encabezados}</tr></thead>
        <tbody>{cuerpo}</tbody>
    </table>
</body>
</html>"""

    except mysql.connector.Error as e:
        return f"<h2>Error de base de datos</h2><p>{e}</p>", 500

    finally:
        if cursor_mysql:
            cursor_mysql.close()
        if conexion_mysql:
            conexion_mysql.close()


if __name__ == "__main__":
    app.run(debug=True)
