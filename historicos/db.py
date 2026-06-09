import mysql.connector

CARRERA_ID = 1

def get_conexion():
    return mysql.connector.connect(
        host     = "acela.proxy.rlwy.net",
        port     = 43667,
        database = "railway",
        user     = "root",
        password = "DFahCFOyOBUGJNvegeGsOvjNaZgYvBAP"
    )
