"""HU-05 a HU-08 · Cruce, clasificación, diferencias de período, calces aproximados y duplicados.

Primero los escenarios con documentos armados a mano (idénticos a los de las historias) y luego los
resultados esperados sobre los CSV de muestra de data/samples/.
"""

from dataclasses import replace

import pytest
from conciliasii.config import Config
from conciliasii.domain.errors import TransicionInvalidaError
from conciliasii.domain.models import Categoria, Periodo
from conciliasii.engine.matcher import sugerir_calces
from conciliasii.engine.service import (
    conciliar,
    confirmar_sugerencia,
    descartar_sugerencia,
    ejecutar_conciliacion,
)

from .conftest import (
    CONTEOS_MUESTRA,
    PERIODO,
    TESORERO,
    TOTAL_MUESTRA,
    doc,
)


def categoria_de(resultado_conciliacion, llave: str) -> Categoria:
    (r,) = [r for r in resultado_conciliacion.resultados if r.llave == llave]
    return r.categoria


# --- HU-05 · escenarios de la historia ------------------------------------------------------


def test_documento_cuadrado_con_rut_en_distinto_formato():
    sii = doc(rut="76.123.456-7", tipo_doc=33, folio=1050)
    bc = doc(rut="76123456-7", tipo_doc=33, folio=1050, nro_movimiento=1)

    resultado = conciliar([sii], [bc], PERIODO, Config())

    assert [r.categoria for r in resultado.resultados] == [Categoria.CUADRADO]
    assert resultado.resultados[0].llave == "76123456-7|33|1050"


def test_rut_con_k_en_minuscula_y_mayuscula_es_la_misma_llave():
    sii = doc(rut="76.123.456-k")
    bc = doc(rut="76123456-K", nro_movimiento=1)

    resultado = conciliar([sii], [bc], PERIODO, Config())

    assert len(resultado.resultados) == 1
    assert resultado.resultados[0].categoria == Categoria.CUADRADO


def test_diferencia_de_monto_marca_el_campo_distinto():
    sii = doc(iva=19000, total=119000)
    bc = doc(iva=18900, total=118900, nro_movimiento=1)

    resultado = conciliar([sii], [bc], PERIODO, Config())

    (r,) = resultado.resultados
    assert r.categoria == Categoria.DIFERENCIA_MONTO
    assert "monto_iva_recuperable" in r.campos_distintos


def test_solo_en_sii():
    resultado = conciliar([doc()], [], PERIODO, Config())

    assert [r.categoria for r in resultado.resultados] == [Categoria.SOLO_SII]


def test_solo_en_erp():
    resultado = conciliar([], [doc(nro_movimiento=1)], PERIODO, Config())

    assert [r.categoria for r in resultado.resultados] == [Categoria.SOLO_ERP]


def test_factura_exenta_con_iva_en_bc_es_diferencia_de_monto():
    sii = doc(tipo_doc=34, neto=0, exento=130000, iva=0)
    bc = doc(tipo_doc=34, neto=0, exento=130000, iva=24700, total=154700, nro_movimiento=1)

    (r,) = conciliar([sii], [bc], PERIODO, Config()).resultados

    assert r.categoria == Categoria.DIFERENCIA_MONTO
    assert "monto_iva_recuperable" in r.campos_distintos


def test_mismo_folio_con_distinto_rut_o_tipo_son_documentos_distintos():
    sii = [doc(rut="76100010-1", folio=1001), doc(rut="76200025-3", folio=1001)]
    bc = [doc(rut="76100010-1", folio=1001, nro_movimiento=1)]

    resultado = conciliar(sii, bc, PERIODO, Config())

    assert categoria_de(resultado, "76100010-1|33|1001") == Categoria.CUADRADO
    assert categoria_de(resultado, "76200025-3|33|1001") == Categoria.SOLO_SII


# --- HU-05 · sobre las muestras -------------------------------------------------------------


@pytest.fixture
def conciliacion(docs_sii, docs_erp_todos):
    return conciliar(docs_sii, docs_erp_todos, PERIODO, Config())


def test_muestra_cada_categoria_tiene_la_cantidad_esperada(conciliacion):
    cantidades = {c: len(conciliacion.por_categoria(Categoria[c])) for c in CONTEOS_MUESTRA}

    assert cantidades == CONTEOS_MUESTRA


def test_muestra_cada_documento_cae_en_una_sola_categoria(conciliacion):
    llaves = [r.llave for r in conciliacion.resultados]

    assert len(llaves) == len(set(llaves))  # ninguna llave dos veces
    assert len(llaves) == TOTAL_MUESTRA  # la suma de categorías es el universo filtrado


def test_muestra_diferencias_de_monto_y_sus_campos(conciliacion):
    esperado = {
        "77300031-K|33|2211": {"monto_iva_recuperable", "monto_total"},
        "76800089-1|34|121": {"monto_iva_recuperable", "monto_total"},  # tipo 34 con IVA en BC
        "76400047-1|33|331": {"monto_iva_recuperable", "monto_total"},  # $1 de redondeo (P3)
        "76600068-1|33|16": {"monto_neto", "monto_iva_recuperable", "monto_total"},
        "77700073-K|33|4411": {"fecha_docto"},  # solo la fecha de emisión
        "76100010-1|33|1004": {"monto_total"},
    }
    obtenido = {
        r.llave: set(r.campos_distintos)
        for r in conciliacion.por_categoria(Categoria.DIFERENCIA_MONTO)
    }

    assert obtenido == esperado


def test_muestra_el_mismo_folio_de_dos_proveedores_cuadra_por_separado(conciliacion):
    assert categoria_de(conciliacion, "76100010-1|33|1001") == Categoria.CUADRADO
    assert categoria_de(conciliacion, "76200025-3|33|1001") == Categoria.CUADRADO


def test_muestra_solo_en_sii_y_solo_en_erp(conciliacion):
    assert {r.llave for r in conciliacion.por_categoria(Categoria.SOLO_SII)} == {
        "76600068-1|33|17",
        "76800089-1|34|122",
        "77700073-K|33|4412",
        "76400047-1|33|332",
    }
    assert {r.llave for r in conciliacion.por_categoria(Categoria.SOLO_ERP)} == {
        "76100010-1|33|1005",
        "77300031-K|34|2213",
        "76200025-3|33|1003",
        "77500052-K|33|9004",
        "76400047-1|33|340",
    }


@pytest.mark.parametrize(
    ("tolerancia", "categoria_esperada"),
    [(0, Categoria.DIFERENCIA_MONTO), (1, Categoria.CUADRADO)],
)
def test_pendiente_P3_diferencia_de_un_peso_segun_la_tolerancia(
    docs_sii, docs_erp_todos, tolerancia, categoria_esperada
):
    resultado = conciliar(docs_sii, docs_erp_todos, PERIODO, Config(amount_tolerance=tolerancia))

    assert categoria_de(resultado, "76400047-1|33|331") == categoria_esperada


# --- HU-06 · diferencias de período ---------------------------------------------------------


def test_documento_registrado_en_el_periodo_siguiente(conciliacion):
    r = next(r for r in conciliacion.resultados if r.llave == "76200025-3|33|1002")

    assert r.categoria == Categoria.DIFERENCIA_PERIODO
    assert (r.periodo_sii, r.periodo_erp) == (Periodo(2026, 8), Periodo(2026, 9))


def test_documento_registrado_en_el_periodo_anterior(conciliacion):
    r = next(r for r in conciliacion.resultados if r.llave == "77500052-K|33|9003")

    assert r.categoria == Categoria.DIFERENCIA_PERIODO
    assert r.periodo_erp == Periodo(2026, 7)


def test_diferencia_de_periodo_prevalece_sobre_la_de_monto_y_lista_los_campos(conciliacion):
    r = next(r for r in conciliacion.resultados if r.llave == "77300031-K|33|2212")

    assert r.categoria == Categoria.DIFERENCIA_PERIODO
    assert {"monto_neto", "monto_total"} <= set(r.campos_distintos)


def test_fuera_del_rango_de_busqueda_queda_como_solo_en_sii(docs_sii, docs_erp_todos):
    sin_vecinos = Config(neighbor_periods=(0, 0))

    resultado = conciliar(docs_sii, docs_erp_todos, PERIODO, sin_vecinos)

    assert categoria_de(resultado, "76200025-3|33|1002") == Categoria.SOLO_SII
    # Los documentos de otro mes que no están en el SII tampoco aparecen como "Solo en ERP".
    assert len(resultado.por_categoria(Categoria.DIFERENCIA_PERIODO)) == 0
    assert len(resultado.por_categoria(Categoria.SOLO_ERP)) == 5


# --- HU-07 · calces aproximados -------------------------------------------------------------


def test_sugerencia_por_rut_y_monto_total_sin_cambiar_categorias():
    sii = doc(rut="76123456-7", folio=1050, neto=100000, iva=19000)  # total 119.000
    bc = doc(rut="76123456-7", folio=1005, neto=100000, iva=19000, nro_movimiento=1)

    resultado = conciliar([sii], [bc], PERIODO, Config())

    assert [(s.llave_sii, s.llave_erp) for s in resultado.sugerencias] == [
        ("76123456-7|33|1050", "76123456-7|33|1005")
    ]
    assert {r.categoria for r in resultado.resultados} == {Categoria.SOLO_SII, Categoria.SOLO_ERP}


def test_no_se_sugiere_con_distinto_rut_o_distinto_total():
    sii = [doc(rut="76123456-7", folio=1), doc(rut="76123456-7", folio=2, neto=50000, iva=9500)]
    bc = [
        doc(rut="77777777-7", folio=1, nro_movimiento=1),  # mismo total, otro RUT
        doc(rut="76123456-7", folio=3, neto=1, iva=0, nro_movimiento=2),  # mismo RUT, otro total
    ]

    assert conciliar(sii, bc, PERIODO, Config()).sugerencias == []


def test_muestra_tiene_exactamente_una_sugerencia(conciliacion):
    assert [(s.llave_sii, s.llave_erp) for s in conciliacion.sugerencias] == [
        ("76400047-1|33|332", "76400047-1|33|340")
    ]
    assert sugerir_calces(conciliacion.resultados) == conciliacion.sugerencias


def test_confirmar_sugerencia_pasa_ambos_a_diferencia_de_monto_con_folio_distinto(repo, ejecucion):
    (sugerencia,) = repo.listar_sugerencias(ejecucion.periodo_id)

    confirmar_sugerencia(repo, ejecucion.id, sugerencia, TESORERO)

    por_llave = {r.llave: r for r in repo.listar_resultados(ejecucion.id)}
    for llave in (sugerencia.llave_sii, sugerencia.llave_erp):
        assert por_llave[llave].categoria == Categoria.DIFERENCIA_MONTO
        assert "folio" in por_llave[llave].campos_distintos
    (guardada,) = repo.listar_sugerencias(ejecucion.periodo_id)
    assert guardada.estado == "Confirmada"
    assert guardada.decidido_por == TESORERO.nombre
    assert guardada.decidido_en is not None


def test_descartar_sugerencia_mantiene_categorias_y_no_vuelve_a_aparecer(
    repo, erp, docs_sii, config, ejecucion
):
    (sugerencia,) = repo.listar_sugerencias(ejecucion.periodo_id)

    descartar_sugerencia(repo, ejecucion.id, sugerencia, TESORERO)

    por_llave = {r.llave: r for r in repo.listar_resultados(ejecucion.id)}
    assert por_llave[sugerencia.llave_sii].categoria == Categoria.SOLO_SII
    assert por_llave[sugerencia.llave_erp].categoria == Categoria.SOLO_ERP

    # Al volver a conciliar el período, el descarte persiste y la sugerencia no se vuelve a mostrar.
    nueva = ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)
    assert [s for s in repo.listar_sugerencias(nueva.periodo_id) if s.estado == "Pendiente"] == []


# --- HU-08 · duplicados ---------------------------------------------------------------------


def test_llave_repetida_en_bc_genera_alerta_con_ambos_numeros_internos():
    sii = doc(folio=1050)
    bc = [doc(folio=1050, nro_movimiento=7001), doc(folio=1050, nro_movimiento=7002)]

    (r,) = conciliar([sii], bc, PERIODO, Config()).resultados

    assert r.alerta_duplicado is True
    assert sorted(r.nros_movimiento_duplicados) == [7001, 7002]


def test_sin_duplicados_no_hay_alerta(conciliacion):
    assert not any(r.alerta_duplicado for r in conciliacion.resultados)


def test_documento_corregido_deja_de_ser_diferencia_de_monto():
    # Sanidad del cruce: igualar los montos en BC lo deja en Cuadrado.
    sii = doc(iva=19000, total=119000)
    bc_malo = doc(iva=18900, total=118900, nro_movimiento=1)
    bc_bueno = replace(bc_malo, monto_iva_recuperable=19000, monto_total=119000)

    assert conciliar([sii], [bc_malo], PERIODO, Config()).resultados[0].categoria == (
        Categoria.DIFERENCIA_MONTO
    )
    assert conciliar([sii], [bc_bueno], PERIODO, Config()).resultados[0].categoria == (
        Categoria.CUADRADO
    )


def test_una_version_aprobada_no_admite_cambios_de_sugerencias(repo, ejecucion):
    from .conftest import llevar_a_estado

    (sugerencia,) = repo.listar_sugerencias(ejecucion.periodo_id)
    llevar_a_estado(repo, ejecucion, "Aprobado")

    with pytest.raises(TransicionInvalidaError):
        confirmar_sugerencia(repo, ejecucion.id, sugerencia, TESORERO)
