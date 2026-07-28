"""Captura información de N videojuegos por consola y la guarda en un CSV."""

import csv
import os

ARCHIVO_CSV = "videojuegos.csv"
CAMPOS = ["Nombre", "Género", "Desarrollador", "Clasificación ESRB"]
CLASIFICACIONES_ESRB = ["E", "E10+", "T", "M", "AO", "RP"]


def pedir_cantidad():
    while True:
        try:
            cantidad = int(input("¿Cuántos videojuegos vas a ingresar? ").strip())
        except ValueError:
            print("Entrada inválida: escribe un número entero.")
            continue
        if cantidad <= 0:
            print("La cantidad debe ser un entero positivo.")
            continue
        return cantidad


def pedir_texto(etiqueta):
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if valor:
            return valor
        print("El valor no puede estar vacío.")


def pedir_clasificacion():
    opciones = ", ".join(CLASIFICACIONES_ESRB)
    while True:
        valor = input(f"Clasificación ESRB ({opciones}): ").strip().upper()
        for clasificacion in CLASIFICACIONES_ESRB:
            if valor == clasificacion.upper():
                return clasificacion
        print(f"Clasificación inválida. Opciones válidas: {opciones}.")


def pedir_videojuegos(cantidad):
    videojuegos = []
    for indice in range(1, cantidad + 1):
        print(f"\nVideojuego {indice} de {cantidad}")
        videojuegos.append(
            {
                "Nombre": pedir_texto("Nombre"),
                "Género": pedir_texto("Género"),
                "Desarrollador": pedir_texto("Desarrollador"),
                "Clasificación ESRB": pedir_clasificacion(),
            }
        )
    return videojuegos


def guardar_csv(videojuegos, ruta=ARCHIVO_CSV):
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(videojuegos)
    return os.path.abspath(ruta)


def main():
    videojuegos = pedir_videojuegos(pedir_cantidad())
    ruta = guardar_csv(videojuegos)
    print(f"\nSe guardaron {len(videojuegos)} videojuegos en: {ruta}")


if __name__ == "__main__":
    main()
