def pedir_texto(mensaje):
    """
    Solo letras y espacios
    """

    while True:

        dato = input(mensaje).strip()

        if dato.replace(" ", "").isalpha():
            return dato.title()

        print("ERROR: Solo se permiten letras.")


def pedir_sexo():
    """
    Solo M o F
    """

    while True:

        sexo = input("Sexo (M/F): ").strip().upper()

        if sexo in ["M", "F"]:
            return sexo

        print("ERROR: Solo puede ingresar M o F.")


def pedir_distancia():
    """
    Distancias válidas
    """

    Distacias = ["6KM", "12KM", "18KM"]

    while True:

        print("\nDistancias disponibles:")
        print("- 6KM")
        print("- 12KM")
        print("- 18KM")

        Distancias_Disponibles = input("Seleccione distancia: ").strip().upper()

        if Distancias_Disponibles in Distacias:
            return Distancias_Disponibles

        print("ERROR: Opción inválida.")

def pedir_categoria():
    """
    Categorías válidas
    """

    categorias_validas = [
        "16-19", "20-24", "25-29", "30-34", "35-39",
        "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70"
    ]

    while True:
        print("\nCategorías disponibles:")
        for categoria in categorias_validas:
            print(f"- {categoria}")

        categoria = input("Seleccione una categoría: ").strip()

        if categoria in categorias_validas:
            return categoria

        print("ERROR: Categoría inválida.")
