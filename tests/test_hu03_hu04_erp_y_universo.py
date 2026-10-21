"""HU-03 · Traer el libro de BC (erp/, servicio) y HU-04 · Filtrar el universo (engine/matcher)."""

import pytest
from conciliasii.domain.errors import ErpNoDisponibleError
from conciliasii.domain.models import Periodo
from conciliasii.engine.matcher import filtrar_universo
from conciliasii.engine.service import ejecutar_conciliacion
from conciliasii.erp.csv_adapter import CsvLedgerAdapter
from conciliasii.ingest.sii_csv import leer_rcv

from .conftest import (
    LIBRO_BC,
    PERIODO,
    RUT_EMPRESA,
    TESORERO,
    ErpCaido,
    csv_bc_modificado,
    csv_sii_modificado,
    doc,
    fila_sii,
)

# --- HU-03 ---------------------------------------------------------------------------------


def test_extraccion_exitosa_trae_las_facturas_del_periodo(adaptador_bc):
    libro = adaptador_bc.get_purchase_ledger(PERIODO)

    # Con posting_date, 3 de las 26 facturas están registradas en julio o septiembre (P2).
    assert len(libro) == 23
    assert all(d.periodo == PERIODO for d in libro)
    assert all(d.nro_movimiento is not None for d in libro)


def test_el_campo_que_define_el_periodo_es_configurable_P2():
    por_fecha_documento = CsvLedgerAdapter(LIBRO_BC, erp_period_date_field="document_date")

    # Con document_date las 26 facturas pertenecen a agosto.
    assert len(por_fecha_documento.get_purchase_ledger(PERIODO)) == 26


def test_la_ejecucion_guarda_fecha_hora_y_cantidad_de_la_extraccion(ejecucion):
    assert ejecucion.extraido_erp_en is not None
    assert ejecucion.cantidad_docs_erp > 0


def test_bc_no_disponible_informa_la_causa_y_permite_reintentar_sin_perder_el_csv(
    repo, erp, docs_sii, config
):
    with pytest.raises(ErpNoDisponibleError) as error:
        ejecutar_conciliacion(
            repo, ErpCaido("503 Service Unavailable"), docs_sii, PERIODO, TESORERO, config=config
        )
    assert "503 Service Unavailable" in str(error.value)

    # El CSV ya leído (docs_sii) se reutiliza tal cual en el reintento.
    reintento = ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)
    assert reintento.version == 1


def test_factura_de_bc_sin_llave_se_informa_con_su_numero_interno(tmp_path):
    libro = csv_bc_modificado(
        tmp_path / "libro.csv",
        vaciar_en_entry={5001: {"DTE Folio": ""}, 5002: {"VAT Registration No.": ""}},
    )
    docs_erp = CsvLedgerAdapter(libro, erp_period_date_field="posting_date").get_purchase_ledger(
        PERIODO
    )

    universo = filtrar_universo([], docs_erp)

    assert sorted(d.nro_movimiento for d in universo.sin_llave) == [5001, 5002]
    assert all(
        d.nro_movimiento not in (5001, 5002) for d in universo.erp
    )  # no participan del cruce


# HU-03 · "Documento sin datos de llave" dentro de una conciliación completa:
def test_documento_sin_llave_queda_fuera_de_las_categorias(tmp_path, repo, docs_sii, config):
    libro = csv_bc_modificado(tmp_path / "libro.csv", vaciar_en_entry={5001: {"DTE Folio": ""}})
    adaptador = CsvLedgerAdapter(libro, erp_period_date_field="posting_date")

    ejecucion = ejecutar_conciliacion(repo, adaptador, docs_sii, PERIODO, TESORERO, config=config)

    assert [d.nro_movimiento for d in ejecucion.sin_llave] == [5001]
    assert all("5001" not in r.llave for r in repo.listar_resultados(ejecucion.id))


# --- HU-04 ---------------------------------------------------------------------------------


def test_solo_quedan_documentos_tipo_33_y_34_y_del_sii_solo_estado_registro(docs_sii):
    universo = filtrar_universo(docs_sii, [doc(tipo_doc=61, folio=1), doc(folio=2)])

    assert {d.tipo_doc for d in universo.sii} <= {33, 34}
    assert {d.estado for d in universo.sii} == {"Registro"}
    assert {d.tipo_doc for d in universo.erp} == {33}


def test_informe_de_excluidos_por_tipo_y_por_estado():
    contenido = csv_sii_modificado(
        agregar_filas=[
            fila_sii(**{"Tipo Doc": "61", "Folio": "8001"}),
            fila_sii(**{"Tipo Doc": "61", "Folio": "8002"}),
            fila_sii(Folio="8003", Estado="Pendiente"),
        ]
    )
    docs_sii = leer_rcv(contenido, periodo=PERIODO, rut_empresa=RUT_EMPRESA)

    universo = filtrar_universo(docs_sii, [])

    assert universo.excluidos_por_tipo == 2
    assert universo.excluidos_por_estado == 1
    assert len(universo.sii) == 25  # los 25 documentos originales de la muestra siguen dentro


def test_universo_de_la_muestra_no_excluye_nada(docs_sii):
    universo = filtrar_universo(docs_sii, [])

    assert (universo.excluidos_por_tipo, universo.excluidos_por_estado) == (0, 0)


# --- HU-15 (lo que se puede construir sin BC real; el resto depende de P7) -------------------


def test_stub_de_la_api_de_bc_falla_con_mensaje_claro():
    from conciliasii.erp.bc_api_adapter import BcApiAdapter

    with pytest.raises(NotImplementedError, match="Business Central"):
        BcApiAdapter().get_purchase_ledger(Periodo(2026, 8))


def test_las_credenciales_no_aparecen_en_texto_plano():
    from conciliasii.config import Config

    config = Config(bc_client_secret="s3creto-super-privado")

    assert "s3creto-super-privado" not in repr(config)
    assert "s3creto-super-privado" not in str(config)


@pytest.mark.skip(reason="HU-15: requiere el adaptador real de BC, bloqueado por la decisión P7")
@pytest.mark.parametrize(
    "escenario", ["conexión válida", "credenciales inválidas", "campos de llave disponibles"]
)
def test_probar_conexion_con_bc(escenario):
    raise NotImplementedError
