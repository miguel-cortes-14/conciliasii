"""HU-01 (período ya conciliado), HU-12 · Volver a conciliar y HU-13 · Historial (Capa 3)."""

from dataclasses import replace

from conciliasii.domain.models import Categoria, Periodo
from conciliasii.engine.service import ejecutar_conciliacion
from conciliasii.workflow import approval

from .conftest import (
    CONTEOS_MUESTRA,
    JEFA,
    PERIODO,
    TESORERO,
    ErpEnMemoria,
    comentar_todas_las_diferencias,
    llevar_a_estado,
)

LLAVE_2211 = "77300031-K|33|2211"  # Diferencia de monto: IVA 95.000 en SII y 90.000 en BC


def corregir_2211_en_bc(docs_erp):
    """Simula corregir en BC el IVA y el total de la factura 2211."""
    mala = next(d for d in docs_erp if d.llave == LLAVE_2211)
    return [
        replace(d, monto_iva_recuperable=95000, monto_total=595000) if d is mala else d
        for d in docs_erp
    ]


# --- HU-01 · Período ya conciliado -------------------------------------------------------------


def test_al_seleccionar_un_periodo_ya_conciliado_se_ve_la_ultima_version(repo, ejecucion):
    periodo = repo.obtener_o_crear_periodo("76.999.888-8", 2026, 8)

    vigente = repo.ejecucion_vigente(periodo.id)

    assert vigente.version == 1
    resultados = repo.listar_resultados(vigente.id)
    assert {c.name: sum(r.categoria == c for r in resultados) for c in Categoria} == CONTEOS_MUESTRA


def test_un_periodo_sin_conciliar_no_tiene_version_vigente(repo):
    periodo = repo.obtener_o_crear_periodo("76.999.888-8", 2026, 7)

    assert repo.ejecucion_vigente(periodo.id) is None


# --- HU-12 · Volver a conciliar ---------------------------------------------------------------


def test_nueva_version_conserva_los_comentarios_por_llave(repo, erp, docs_sii, config, ejecucion):
    comentar_todas_las_diferencias(repo, ejecucion, TESORERO, "Pendiente de corregir en BC")

    nueva = ejecutar_conciliacion(
        repo,
        ErpEnMemoria(corregir_2211_en_bc(erp.documentos)),
        docs_sii,
        PERIODO,
        TESORERO,
        config=config,
    )

    assert nueva.version == 2
    comentarios = repo.listar_comentarios(nueva.periodo_id, hasta_version=2)
    assert {c.llave for c in comentarios} >= {
        r.llave for r in repo.listar_resultados(nueva.id) if r.categoria != Categoria.CUADRADO
    }


def test_documento_corregido_en_bc_pasa_a_cuadrado_y_sus_comentarios_siguen_visibles(
    repo, erp, docs_sii, config, ejecucion
):
    approval.agregar_comentario(repo, ejecucion.id, LLAVE_2211, TESORERO, "IVA mal digitado en BC")

    nueva = ejecutar_conciliacion(
        repo,
        ErpEnMemoria(corregir_2211_en_bc(erp.documentos)),
        docs_sii,
        PERIODO,
        TESORERO,
        config=config,
    )

    resultado = next(r for r in repo.listar_resultados(nueva.id) if r.llave == LLAVE_2211)
    assert resultado.categoria == Categoria.CUADRADO
    textos = [c.texto for c in repo.listar_comentarios(nueva.periodo_id, hasta_version=2)]
    assert "IVA mal digitado en BC" in textos


def test_con_dos_versiones_la_vigente_es_la_ultima_y_la_anterior_es_de_solo_lectura(
    repo, erp, docs_sii, config, ejecucion
):
    ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)

    versiones = repo.listar_ejecuciones(ejecucion.periodo_id)
    vigente = repo.ejecucion_vigente(ejecucion.periodo_id)

    assert sorted(v.version for v in versiones) == [1, 2]
    assert vigente.version == 2
    anterior = next(v for v in versiones if v.version == 1)
    assert anterior.solo_lectura is True
    assert vigente.solo_lectura is False


def test_una_version_anterior_no_muestra_comentarios_escritos_despues(
    repo, erp, docs_sii, config, ejecucion
):
    ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)
    vigente = repo.ejecucion_vigente(ejecucion.periodo_id)
    approval.agregar_comentario(repo, vigente.id, LLAVE_2211, TESORERO, "Solo en la versión 2")

    assert not [
        c
        for c in repo.listar_comentarios(ejecucion.periodo_id, hasta_version=1)
        if c.texto == "Solo en la versión 2"
    ]


def test_la_nueva_version_nace_en_borrador(repo, erp, docs_sii, config, ejecucion):
    nueva = ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)

    assert nueva.estado == "Borrador"


# --- HU-13 · Historial -----------------------------------------------------------------------


def test_historial_lista_periodos_del_mas_reciente_al_mas_antiguo_con_resumen_y_estado(
    repo, erp, docs_sii, config
):
    # Mismo CSV de muestra conciliado como 2026-08; los otros dos períodos se crean vacíos de datos
    # propios, lo único que importa aquí es el orden y los campos que muestra la lista.
    for mes in (6, 8, 7):
        periodo = Periodo(2026, mes)
        docs = [replace(d, periodo=periodo) for d in docs_sii]
        ejecutar_conciliacion(repo, erp, docs, periodo, TESORERO, config=config)

    historial = repo.listar_periodos()

    assert [(h.periodo.anio, h.periodo.mes) for h in historial] == [(2026, 8), (2026, 7), (2026, 6)]
    for fila in historial:
        assert fila.ultima_conciliacion is not None
        assert fila.resumen is not None
        assert fila.estado == "Borrador"


def test_historial_refleja_el_estado_actual_de_cada_periodo(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "Aprobado")

    (fila,) = repo.listar_periodos()

    assert fila.estado == "Aprobado"


def test_una_version_aprobada_no_cambia_aunque_se_reabra_y_concilie_de_nuevo(
    repo, erp, docs_sii, config, ejecucion
):
    llevar_a_estado(repo, ejecucion, "Aprobado")
    antes = [(r.llave, r.categoria) for r in repo.listar_resultados(ejecucion.id)]

    approval.reabrir(repo, ejecucion.id, JEFA)
    ejecutar_conciliacion(
        repo,
        ErpEnMemoria(corregir_2211_en_bc(erp.documentos)),
        docs_sii,
        PERIODO,
        TESORERO,
        config=config,
    )

    despues = [(r.llave, r.categoria) for r in repo.listar_resultados(ejecucion.id)]
    assert despues == antes
