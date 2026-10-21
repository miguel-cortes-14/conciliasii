"""HU-09 · Resumen por categoría y HU-10 · Detalle de diferencias (engine/summary.py)."""

import pytest
from conciliasii.domain.models import Categoria
from conciliasii.engine.summary import campos_del_detalle, filtrar_detalle, resumir

from .conftest import (
    CONTEOS_MUESTRA,
    DIFERENCIAS_MUESTRA,
    TOTAL_MUESTRA,
)


@pytest.fixture
def resultados(repo, ejecucion):
    return repo.listar_resultados(ejecucion.id)


def test_resumen_por_categoria_con_cantidades_y_montos(resultados):
    resumen = resumir(resultados)

    assert {c.name: resumen.por_categoria[c].cantidad for c in Categoria} == CONTEOS_MUESTRA
    solo_sii = resumen.por_categoria[Categoria.SOLO_SII]
    assert (solo_sii.monto_sii, solo_sii.monto_erp) == (535_240, 0)
    solo_erp = resumen.por_categoria[Categoria.SOLO_ERP]
    assert (solo_erp.monto_sii, solo_erp.monto_erp) == (0, 1_975_470)
    cuadrado = resumen.por_categoria[Categoria.CUADRADO]
    assert (cuadrado.monto_sii, cuadrado.monto_erp) == (4_702_313, 4_702_313)
    periodo = resumen.por_categoria[Categoria.DIFERENCIA_PERIODO]
    assert (periodo.monto_sii, periodo.monto_erp) == (1_374_450, 1_362_550)


def test_resumen_total_general(resultados):
    resumen = resumir(resultados)

    assert resumen.total_documentos == TOTAL_MUESTRA
    assert resumen.total_monto_sii == 8_586_515
    assert resumen.total_monto_erp == 10_033_256


def test_avance_de_comentarios_cuenta_solo_documentos_fuera_de_cuadrado(resultados):
    diferencias = [r for r in resultados if r.categoria != Categoria.CUADRADO]
    comentadas = {r.llave for r in diferencias[:4]}

    resumen = resumir(resultados, llaves_comentadas=comentadas)

    assert resumen.con_comentario == 4
    assert resumen.sin_comentario == DIFERENCIAS_MUESTRA - 4


def test_sin_comentarios_todo_queda_pendiente(resultados):
    resumen = resumir(resultados)

    assert (resumen.con_comentario, resumen.sin_comentario) == (0, DIFERENCIAS_MUESTRA)


def test_detalle_de_una_diferencia_de_monto_muestra_valores_lado_a_lado(resultados):
    r = next(r for r in resultados if r.llave == "77300031-K|33|2211")

    lineas = {linea.campo: linea for linea in campos_del_detalle(r)}

    iva = lineas["monto_iva_recuperable"]
    assert (iva.valor_sii, iva.valor_erp) == (95000, 90000)
    assert iva.distinto is True
    assert iva.diferencia == 5000  # SII menos ERP
    assert lineas["monto_neto"].distinto is False
    assert lineas["monto_neto"].diferencia == 0


def test_filtrar_por_rut_de_proveedor_acepta_cualquier_formato(resultados):
    de_la_categoria = [r for r in resultados if r.categoria == Categoria.SOLO_ERP]

    filtrados = filtrar_detalle(de_la_categoria, rut="77.500.052-k")

    assert [r.llave for r in filtrados] == ["77500052-K|33|9004"]


def test_filtrar_por_sin_comentario(resultados):
    de_la_categoria = [r for r in resultados if r.categoria == Categoria.SOLO_SII]
    comentadas = {de_la_categoria[0].llave}

    filtrados = filtrar_detalle(de_la_categoria, sin_comentario=True, llaves_comentadas=comentadas)

    assert de_la_categoria[0] not in filtrados
    assert len(filtrados) == CONTEOS_MUESTRA["SOLO_SII"] - 1
