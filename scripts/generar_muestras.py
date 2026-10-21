"""Genera los CSV ficticios de ejemplo en data/samples/.

Uso, desde la raíz del repositorio:

    python scripts/generar_muestras.py

Produce `rcv_sii.csv` (Registro de Compras del SII) y `libro_bc.csv` (libro de compras de
Business Central simulado), con los formatos de docs/arquitectura.md ("Contratos de entrada").
Los datos son inventados y la salida es determinista: no usa azar ni la fecha actual.
"""

import csv
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "data" / "samples"

PERIODO = "2026-08"
RUT_RECEPTOR = 76999888
TASA_IVA = 0.19

# Proveedores ficticios: clave -> (RUT sin dígito verificador, razón social inventada).
PROVEEDORES = {
    "A": (76100010, "Distribuidora Ejemplo Uno SpA"),
    "B": (76200025, "Servicios Ficticios Dos Ltda"),
    "C": (77300031, "Comercial Muestra Tres SA"),
    "D": (76400047, "Insumos de Prueba Cuatro SpA"),
    "E": (77500052, "Logistica Inventada Cinco Ltda"),
    "F": (76600068, "Tecnologia Simulada Seis SA"),
    "G": (77700073, "Papeleria Demo Siete SpA"),
    "H": (76800089, "Mantencion Ficticia Ocho Ltda"),
}

COLUMNAS_SII = [
    "Tipo Doc",
    "RUT Proveedor",
    "Razon Social",
    "Folio",
    "Fecha Docto",
    "Fecha Recepcion",
    "Monto Exento",
    "Monto Neto",
    "Monto IVA Recuperable",
    "Monto Total",
    "RUT Receptor",
    "Periodo",
    "Estado",
]
COLUMNAS_ERP = [
    "Entry No.",
    "Posting Date",
    "Document Date",
    "Document No.",
    "External Document No.",
    "VAT Registration No.",
    "Vendor Name",
    "DTE Type",
    "DTE Folio",
    "Amount Excl. VAT",
    "VAT Amount",
    "Amount Incl. VAT",
]

ENTRY_NO_INICIAL = 5000


def digito_verificador(numero: int) -> str:
    """Dígito verificador de un RUT chileno (módulo 11)."""
    suma, factor = 0, 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return "0" if resto == 11 else "K" if resto == 10 else str(resto)


def rut_con_puntos(numero: int) -> str:
    """Formato del SII: 76.100.010-1."""
    return f"{numero:,}".replace(",", ".") + f"-{digito_verificador(numero)}"


def rut_sin_puntos(numero: int) -> str:
    """Formato del ERP simulado: 76100010-1."""
    return f"{numero}-{digito_verificador(numero)}"


def montos(tipo: int, base: int) -> dict[str, int]:
    """Montos coherentes: el tipo 34 es todo exento; el 33 lleva neto e IVA 19 %."""
    if tipo == 34:
        return {"exento": base, "neto": 0, "iva": 0, "total": base}
    iva = round(base * TASA_IVA)
    return {"exento": 0, "neto": base, "iva": iva, "total": base + iva}


def fecha(dia: int, mes: int = 8) -> str:
    return f"2026-{mes:02d}-{dia:02d}"


class Generador:
    """Acumula las filas de ambos CSV a medida que se declaran los documentos."""

    def __init__(self) -> None:
        self.filas_sii: list[list[object]] = []
        self.filas_erp: list[list[object]] = []
        self._entry_no = ENTRY_NO_INICIAL

    def agregar(
        self,
        proveedor: str,
        tipo: int,
        folio: int,
        base: int,
        dia: int,
        *,
        solo_sii: bool = False,
        solo_erp: bool = False,
        cambios_erp: dict[str, int] | None = None,
        mes_registro_erp: int = 8,
        dia_registro_erp: int | None = None,
        fecha_docto_erp: str | None = None,
        folio_erp: int | None = None,
    ) -> None:
        """Declara un documento y lo escribe en el SII, en el ERP o en ambos.

        `cambios_erp` pisa montos solo del lado ERP (diferencias de monto); `mes_registro_erp`
        y `dia_registro_erp` mueven la fecha de registro contable (diferencias de período);
        `fecha_docto_erp` cambia la fecha del documento; `folio_erp` permite un folio distinto.
        """
        rut, razon_social = PROVEEDORES[proveedor]
        m = montos(tipo, base)
        if not solo_erp:
            self.filas_sii.append(
                [
                    tipo,
                    rut_con_puntos(rut),
                    razon_social,
                    folio,
                    fecha(dia),
                    fecha(min(dia + 1, 31)),
                    m["exento"],
                    m["neto"],
                    m["iva"],
                    m["total"],
                    rut_con_puntos(RUT_RECEPTOR),
                    PERIODO,
                    "Registro",
                ]
            )
        if not solo_sii:
            e = {**m, **(cambios_erp or {})}
            self._entry_no += 1
            folio_bc = folio_erp or folio
            self.filas_erp.append(
                [
                    self._entry_no,
                    fecha(dia_registro_erp or dia, mes_registro_erp),
                    fecha_docto_erp or fecha(dia),
                    f"FC{self._entry_no}",
                    f"{tipo}-{folio_bc}",
                    rut_sin_puntos(rut),
                    razon_social,
                    tipo,
                    folio_bc,
                    e["exento"] if tipo == 34 else e["neto"],
                    e["iva"],
                    e["total"],
                ]
            )


def declarar_documentos(g: Generador) -> None:
    """Los 30 documentos de la muestra, agrupados por categoría de RN-05."""
    # Cuadrado (12): 9 de tipo 33 y 3 de tipo 34; el folio 1001 se repite con distinto RUT.
    g.agregar("A", 33, 1001, 100000, 3)
    g.agregar("B", 33, 1001, 250000, 4)
    g.agregar("A", 33, 1002, 480000, 5)
    g.agregar("A", 33, 1003, 75000, 6)
    g.agregar("C", 33, 2210, 1200000, 7)
    g.agregar("D", 33, 330, 39990, 10)
    g.agregar("E", 33, 9001, 860500, 11)
    g.agregar("F", 33, 15, 310000, 12)
    g.agregar("G", 33, 4410, 52000, 13)
    g.agregar("B", 34, 77, 180000, 14)
    g.agregar("H", 34, 120, 95000, 17)
    g.agregar("E", 34, 9002, 420000, 18)

    # Diferencia de monto (6).
    # IVA distinto en un tipo 33.
    g.agregar("C", 33, 2211, 500000, 19, cambios_erp={"iva": 90000, "total": 590000})
    # Tipo 34 con IVA distinto de cero en BC.
    g.agregar("H", 34, 121, 130000, 20, cambios_erp={"iva": 24700, "total": 154700})
    # Diferencia de $1 por redondeo (SII: IVA 19.002 y total 119.012).
    g.agregar("D", 33, 331, 100010, 21, cambios_erp={"iva": 19003, "total": 119013})
    # Neto distinto.
    g.agregar("F", 33, 16, 640000, 24, cambios_erp={"neto": 639000, "iva": 121410, "total": 760410})
    # Fecha de emisión distinta, con montos iguales.
    g.agregar("G", 33, 4411, 220000, 25, fecha_docto_erp=fecha(26))
    # Solo el total distinto.
    g.agregar("A", 33, 1004, 90000, 26, cambios_erp={"total": 107000})

    # Diferencia de período (3): BC registra el documento en un mes vecino.
    g.agregar("B", 33, 1002, 310000, 27, mes_registro_erp=9, dia_registro_erp=2)
    g.agregar("E", 33, 9003, 145000, 28, mes_registro_erp=7, dia_registro_erp=30)
    # Período y monto distintos a la vez: prevalece el período (RN-06).
    g.agregar(
        "C",
        33,
        2212,
        700000,
        31,
        mes_registro_erp=9,
        dia_registro_erp=1,
        cambios_erp={"neto": 690000, "iva": 131100, "total": 821100},
    )

    # Solo en SII (4).
    g.agregar("F", 33, 17, 275000, 5, solo_sii=True)
    g.agregar("H", 34, 122, 64000, 12, solo_sii=True)
    g.agregar("G", 33, 4412, 33000, 18, solo_sii=True)
    # Forma par con el Solo en ERP de abajo: mismo RUT y total, folio distinto (RN-08).
    g.agregar("D", 33, 332, 88000, 20, solo_sii=True)

    # Solo en ERP (5).
    g.agregar("A", 33, 1005, 410000, 6, solo_erp=True)
    g.agregar("C", 34, 2213, 56000, 13, solo_erp=True)
    g.agregar("B", 33, 1003, 125000, 19, solo_erp=True)
    g.agregar("E", 33, 9004, 990000, 25, solo_erp=True)
    g.agregar("D", 33, 340, 88000, 20, solo_erp=True)


def escribir_csv(ruta: Path, columnas: list[str], filas: list[list[object]]) -> None:
    """UTF-8, separador `;` y saltos de línea `\\n` para que la salida no dependa del sistema."""
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo, delimiter=";", lineterminator="\n")
        escritor.writerow(columnas)
        escritor.writerows(filas)


def main() -> None:
    g = Generador()
    declarar_documentos(g)
    assert len(g.filas_sii) == 25 and len(g.filas_erp) == 26

    DESTINO.mkdir(parents=True, exist_ok=True)
    escribir_csv(DESTINO / "rcv_sii.csv", COLUMNAS_SII, g.filas_sii)
    escribir_csv(DESTINO / "libro_bc.csv", COLUMNAS_ERP, g.filas_erp)
    print(f"Archivos escritos en {DESTINO}")


if __name__ == "__main__":
    main()
