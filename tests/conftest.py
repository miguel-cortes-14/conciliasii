"""Soporte común de las pruebas de aceptación (docs/historias.md).

Las pruebas se escribieron ANTES que el código (aún no existe `src/conciliasii/`). Por eso fijan,
además del comportamiento, una API propuesta que sigue los nombres de docs/arquitectura.md. Todo lo
que esa API inventa (firmas, nombres de atributos) se concentra en este archivo y en los imports de
cada módulo de prueba, para ajustarlo en un solo lugar cuando se implemente.

Datos: data/samples/ (período 2026-08). Resultado esperado con la configuración por defecto
(tolerancia 0, vecinos 2 anteriores y 1 siguiente, período según `posting_date`):

    Cuadrado 12 · Diferencia de monto 6 · Diferencia de período 3 · Solo en SII 4 · Solo en ERP 5
    (universo filtrado = 30 documentos)
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest
from conciliasii.config import Config
from conciliasii.domain.models import Actor, Documento, Periodo, Rol
from conciliasii.engine.service import ejecutar_conciliacion
from conciliasii.erp.csv_adapter import CsvLedgerAdapter
from conciliasii.ingest.sii_csv import leer_rcv
from conciliasii.storage.repository import SqliteRepository

RAIZ = Path(__file__).resolve().parent.parent
MUESTRAS = RAIZ / "data" / "samples"
RCV_SII = MUESTRAS / "rcv_sii.csv"
LIBRO_BC = MUESTRAS / "libro_bc.csv"

RUT_EMPRESA = "76.999.888-8"
PERIODO = Periodo(2026, 8)

TESORERO = Actor("Tamara Tesorera", Rol.TESORERO)
ANALISTA = Actor("Andrés Analista", Rol.ANALISTA_CONTABLE)
JEFA = Actor("Julia Jefa", Rol.JEFA_CONTABILIDAD)
GAF = Actor("Gonzalo Gerente", Rol.GAF)

# Conteos esperados de las muestras.
CONTEOS_MUESTRA = {
    "CUADRADO": 12,
    "DIFERENCIA_MONTO": 6,
    "DIFERENCIA_PERIODO": 3,
    "SOLO_SII": 4,
    "SOLO_ERP": 5,
}
TOTAL_MUESTRA = 30
DIFERENCIAS_MUESTRA = TOTAL_MUESTRA - CONTEOS_MUESTRA["CUADRADO"]  # 18


# --- Fábricas de documentos en memoria -----------------------------------------------------


def doc(
    *,
    rut: str = "76123456-7",
    tipo_doc: int = 33,
    folio: int = 1050,
    neto: int = 100000,
    iva: int = 19000,
    total: int | None = None,
    exento: int = 0,
    periodo: Periodo = PERIODO,
    estado: str = "Registro",
    nro_movimiento: int | None = None,
    fecha_docto: date = date(2026, 8, 3),
) -> Documento:
    """Un `Documento` con valores razonables; sobreescribe solo lo que cada prueba necesita."""
    return Documento(
        rut=rut,
        tipo_doc=tipo_doc,
        folio=folio,
        razon_social="Proveedor Ficticio SpA",
        fecha_docto=fecha_docto,
        monto_exento=exento,
        monto_neto=neto,
        monto_iva_recuperable=iva,
        monto_total=total if total is not None else exento + neto + iva,
        periodo=periodo,
        estado=estado,
        nro_movimiento=nro_movimiento,
    )


# --- ERP en memoria (implementa ErpLedgerPort) ---------------------------------------------


class ErpEnMemoria:
    """Libro de BC en memoria; filtra por `Documento.periodo` como lo haría el adaptador."""

    def __init__(self, documentos: list[Documento]) -> None:
        self.documentos = list(documentos)
        self.llamadas: list[Periodo] = []

    def get_purchase_ledger(self, period: Periodo) -> list[Documento]:
        self.llamadas.append(period)
        return [d for d in self.documentos if d.periodo == period]


class ErpCaido:
    """Simula la API de BC no disponible."""

    def __init__(self, causa: str) -> None:
        self.causa = causa

    def get_purchase_ledger(self, period: Periodo) -> list[Documento]:
        from conciliasii.domain.errors import ErpNoDisponibleError

        raise ErpNoDisponibleError(self.causa)


# --- Fixtures sobre las muestras -----------------------------------------------------------


@pytest.fixture
def config() -> Config:
    return Config(empresa_rut=RUT_EMPRESA)


@pytest.fixture
def docs_sii() -> list[Documento]:
    return leer_rcv(RCV_SII.read_bytes(), periodo=PERIODO, rut_empresa=RUT_EMPRESA)


@pytest.fixture
def adaptador_bc() -> CsvLedgerAdapter:
    return CsvLedgerAdapter(LIBRO_BC, erp_period_date_field="posting_date")


@pytest.fixture
def docs_erp_todos(adaptador_bc: CsvLedgerAdapter) -> list[Documento]:
    """Todo el libro de BC de la muestra (jul a sep 2026), con su período ya asignado."""
    docs: list[Documento] = []
    periodo = Periodo(2026, 6)
    for _ in range(5):
        docs.extend(adaptador_bc.get_purchase_ledger(periodo))
        periodo = periodo.desplazar(1)
    return docs


@pytest.fixture
def erp(docs_erp_todos: list[Documento]) -> ErpEnMemoria:
    return ErpEnMemoria(docs_erp_todos)


@pytest.fixture
def repo() -> SqliteRepository:
    return SqliteRepository(":memory:")


@pytest.fixture
def ejecucion(repo, erp, docs_sii, config):
    """Período 2026-08 conciliado con las muestras: versión 1 en `Borrador`."""
    return ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)


# --- Utilidades para CSV del SII modificados -----------------------------------------------


def csv_sii_modificado(
    *,
    reemplazos: dict[str, str] | None = None,
    quitar_columnas: tuple[str, ...] = (),
    agregar_filas: list[dict[str, str]] | None = None,
) -> bytes:
    """Copia del CSV de muestra del SII con columnas reemplazadas/quitadas y filas agregadas."""
    with RCV_SII.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f, delimiter=";")
        columnas = [c for c in lector.fieldnames or [] if c not in quitar_columnas]
        filas = [dict(f_) for f_ in lector]
    for fila in filas:
        fila.update(reemplazos or {})
    filas.extend(agregar_filas or [])
    salida = io.StringIO()
    escritor = csv.DictWriter(
        salida, fieldnames=columnas, delimiter=";", lineterminator="\n", extrasaction="ignore"
    )
    escritor.writeheader()
    escritor.writerows(filas)
    return salida.getvalue().encode("utf-8")


def fila_sii(**campos: str) -> dict[str, str]:
    """Fila válida de un CSV del SII (período 2026-08) para agregar documentos de prueba."""
    base = {
        "Tipo Doc": "33",
        "RUT Proveedor": "76.100.010-1",
        "Razon Social": "Proveedor Ficticio SpA",
        "Folio": "7000",
        "Fecha Docto": "2026-08-10",
        "Fecha Recepcion": "2026-08-11",
        "Monto Exento": "0",
        "Monto Neto": "10000",
        "Monto IVA Recuperable": "1900",
        "Monto Total": "11900",
        "RUT Receptor": RUT_EMPRESA,
        "Periodo": "2026-08",
        "Estado": "Registro",
    }
    return {**base, **campos}


def csv_bc_modificado(destino: Path, *, vaciar_en_entry: dict[int, dict[str, str]]) -> Path:
    """Copia del libro de BC de muestra con campos pisados por `Entry No.`."""
    with LIBRO_BC.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f, delimiter=";")
        columnas = lector.fieldnames or []
        filas = [dict(f_) for f_ in lector]
    for fila in filas:
        fila.update(vaciar_en_entry.get(int(fila["Entry No."]), {}))
    with destino.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, delimiter=";", lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)
    return destino


# --- Avance del flujo de aprobación --------------------------------------------------------


def comentar_todas_las_diferencias(repo, ejecucion, actor=TESORERO, texto="Revisado") -> None:
    """Deja un comentario en cada documento fuera de `Cuadrado` (requisito de RN-11)."""
    from conciliasii.domain.models import Categoria
    from conciliasii.workflow import approval

    for r in repo.listar_resultados(ejecucion.id):
        if r.categoria != Categoria.CUADRADO:
            approval.agregar_comentario(repo, ejecucion.id, r.llave, actor, texto)


def llevar_a_estado(repo, ejecucion, estado: str, *, comentar: bool = True):
    """Recorre el camino feliz hasta `estado` ('Borrador', 'EnRevisionContable', ...)."""
    from conciliasii.workflow import approval

    pasos = [
        (
            "EnRevisionContable",
            lambda: approval.enviar_a_revision_contable(repo, ejecucion.id, TESORERO),
        ),
        ("PendienteJefaContabilidad", lambda: approval.enviar_a_jefa(repo, ejecucion.id, ANALISTA)),
        ("PendienteGAF", lambda: approval.aprobar_nivel1(repo, ejecucion.id, JEFA)),
        ("Aprobado", lambda: approval.aprobar_nivel2(repo, ejecucion.id, GAF)),
    ]
    if comentar:
        comentar_todas_las_diferencias(repo, ejecucion)
    for nombre, accion in pasos:
        if estado == "Borrador":
            break
        accion()
        if nombre == estado:
            break
    return repo.ejecucion_vigente(ejecucion.periodo_id)
