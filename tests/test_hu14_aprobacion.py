"""HU-14 · Aprobar el período (workflow/approval.py, Capa 2).

Estados: Borrador -> EnRevisionContable -> PendienteJefaContabilidad -> PendienteGAF -> Aprobado.
"""

import pytest
from conciliasii.domain.errors import (
    ComentariosFaltantesError,
    MotivoRequeridoError,
    RolNoAutorizadoError,
    TransicionInvalidaError,
)
from conciliasii.domain.models import Decision
from conciliasii.engine.service import ejecutar_conciliacion
from conciliasii.workflow import approval

from .conftest import (
    ANALISTA,
    DIFERENCIAS_MUESTRA,
    GAF,
    JEFA,
    PERIODO,
    TESORERO,
    llevar_a_estado,
)


def estado_de(repo, ejecucion) -> str:
    return repo.ejecucion_vigente(ejecucion.periodo_id).estado


def decisiones(repo, ejecucion):
    return repo.listar_decisiones(ejecucion.id)


# --- Aprobación de nivel 1 -------------------------------------------------------------------


def test_nivel_1_con_todas_las_diferencias_comentadas_pasa_a_espera_del_gaf(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad")

    approval.aprobar_nivel1(repo, ejecucion.id, JEFA)

    assert estado_de(repo, ejecucion) == "PendienteGAF"
    (decision,) = [d for d in decisiones(repo, ejecucion) if d.decision == Decision.APROBADO_NIVEL1]
    assert (decision.usuario, decision.rol, decision.nivel) == (JEFA.nombre, JEFA.rol, 1)
    assert decision.decidido_en is not None


def test_diferencias_sin_comentario_impiden_aprobar_el_nivel_1_e_informan_cuantas_faltan(
    repo, ejecucion
):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad", comentar=False)

    with pytest.raises(ComentariosFaltantesError) as error:
        approval.aprobar_nivel1(repo, ejecucion.id, JEFA)

    assert len(error.value.faltantes) == DIFERENCIAS_MUESTRA
    assert str(DIFERENCIAS_MUESTRA) in str(error.value)
    assert estado_de(repo, ejecucion) == "PendienteJefaContabilidad"


def test_un_solo_documento_sin_comentar_basta_para_rechazar_la_aprobacion(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "EnRevisionContable", comentar=False)
    from conciliasii.domain.models import Categoria

    con_diferencia = [
        r for r in repo.listar_resultados(ejecucion.id) if r.categoria != Categoria.CUADRADO
    ]
    for r in con_diferencia[:-1]:
        approval.agregar_comentario(repo, ejecucion.id, r.llave, ANALISTA, "Revisado")
    approval.enviar_a_jefa(repo, ejecucion.id, ANALISTA)  # enviar a la Jefa no se bloquea

    with pytest.raises(ComentariosFaltantesError) as error:
        approval.aprobar_nivel1(repo, ejecucion.id, JEFA)

    assert error.value.faltantes == [con_diferencia[-1].llave]


def test_un_comentario_en_blanco_no_cuenta(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad", comentar=False)
    from conciliasii.domain.models import Categoria

    r = next(r for r in repo.listar_resultados(ejecucion.id) if r.categoria != Categoria.CUADRADO)

    with pytest.raises((ValueError, ComentariosFaltantesError)):
        approval.agregar_comentario(repo, ejecucion.id, r.llave, JEFA, "   ")
        approval.aprobar_nivel1(repo, ejecucion.id, JEFA)


# --- Aprobación final y rechazos --------------------------------------------------------------


def test_aprobacion_final_del_gaf(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteGAF")

    approval.aprobar_nivel2(repo, ejecucion.id, GAF)

    assert estado_de(repo, ejecucion) == "Aprobado"
    (decision,) = [d for d in decisiones(repo, ejecucion) if d.decision == Decision.APROBADO_NIVEL2]
    assert (decision.usuario, decision.rol, decision.nivel) == (GAF.nombre, GAF.rol, 2)
    assert decision.decidido_en is not None


def test_el_gaf_rechaza_y_el_periodo_vuelve_a_la_jefa_con_el_motivo(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteGAF")

    approval.rechazar_nivel2(repo, ejecucion.id, GAF, motivo="Falta respaldo de la factura 2211")

    assert estado_de(repo, ejecucion) == "PendienteJefaContabilidad"
    rechazo = decisiones(repo, ejecucion)[-1]
    assert (rechazo.decision, rechazo.nivel) == (Decision.RECHAZADO, 2)
    assert rechazo.motivo == "Falta respaldo de la factura 2211"


def test_la_jefa_rechaza_y_el_periodo_vuelve_al_analista_con_el_motivo(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad")

    approval.rechazar_nivel1(repo, ejecucion.id, JEFA, motivo="Revisar proveedor Comercial Muestra")

    assert estado_de(repo, ejecucion) == "EnRevisionContable"
    rechazo = decisiones(repo, ejecucion)[-1]
    assert (rechazo.decision, rechazo.nivel) == (Decision.RECHAZADO, 1)
    assert rechazo.motivo == "Revisar proveedor Comercial Muestra"


def test_el_analista_devuelve_el_periodo_a_tesoreria_en_borrador_con_el_motivo(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "EnRevisionContable", comentar=False)

    approval.devolver_a_tesoreria(
        repo, ejecucion.id, ANALISTA, motivo="Falta cargar el CSV correcto"
    )

    assert estado_de(repo, ejecucion) == "Borrador"
    devolucion = decisiones(repo, ejecucion)[-1]
    assert devolucion.decision == Decision.DEVUELTO
    assert devolucion.motivo == "Falta cargar el CSV correcto"


@pytest.mark.parametrize(
    ("estado", "accion", "actor"),
    [
        ("EnRevisionContable", approval.devolver_a_tesoreria, ANALISTA),
        ("PendienteJefaContabilidad", approval.rechazar_nivel1, JEFA),
        ("PendienteGAF", approval.rechazar_nivel2, GAF),
    ],
)
@pytest.mark.parametrize("motivo", [None, "", "   "])
def test_rechazos_y_devoluciones_exigen_motivo(repo, ejecucion, estado, accion, actor, motivo):
    llevar_a_estado(repo, ejecucion, estado)
    antes = len(decisiones(repo, ejecucion))

    with pytest.raises(MotivoRequeridoError):
        accion(repo, ejecucion.id, actor, motivo=motivo)

    assert estado_de(repo, ejecucion) == estado
    assert len(decisiones(repo, ejecucion)) == antes


# --- Roles ----------------------------------------------------------------------------------


@pytest.mark.parametrize("actor", [TESORERO, ANALISTA])
def test_tesorero_y_analista_no_aprueban(repo, ejecucion, actor):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad")

    for estado in ("Borrador", "EnRevisionContable", "PendienteJefaContabilidad", "PendienteGAF"):
        acciones = approval.acciones_permitidas(actor.rol, estado)
        assert not {"aprobar_nivel1", "aprobar_nivel2"} & set(acciones)
    with pytest.raises(RolNoAutorizadoError):
        approval.aprobar_nivel1(repo, ejecucion.id, actor)


def test_cada_aprobacion_solo_la_da_su_rol(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad")
    with pytest.raises(RolNoAutorizadoError):
        approval.aprobar_nivel1(repo, ejecucion.id, GAF)  # el GAF no da el nivel 1

    approval.aprobar_nivel1(repo, ejecucion.id, JEFA)
    with pytest.raises(RolNoAutorizadoError):
        approval.aprobar_nivel2(repo, ejecucion.id, JEFA)  # la Jefa no da el nivel 2


def test_solo_el_analista_puede_devolver_a_tesoreria(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "EnRevisionContable", comentar=False)

    for actor in (TESORERO, JEFA, GAF):
        with pytest.raises(RolNoAutorizadoError):
            approval.devolver_a_tesoreria(repo, ejecucion.id, actor, motivo="x")


def test_no_se_puede_saltar_etapas(repo, ejecucion):
    with pytest.raises(TransicionInvalidaError):
        approval.aprobar_nivel1(repo, ejecucion.id, JEFA)  # desde Borrador
    with pytest.raises(TransicionInvalidaError):
        approval.aprobar_nivel2(repo, ejecucion.id, GAF)  # desde Borrador


# --- Período aprobado ------------------------------------------------------------------------


def test_periodo_aprobado_no_se_puede_volver_a_conciliar(repo, erp, docs_sii, config, ejecucion):
    llevar_a_estado(repo, ejecucion, "Aprobado")

    with pytest.raises(TransicionInvalidaError) as error:
        ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)

    assert "Jefa de Contabilidad" in str(error.value)  # indica quién debe reabrirlo
    assert repo.ejecucion_vigente(ejecucion.periodo_id).version == 1


def test_la_jefa_reabre_un_periodo_aprobado_sin_visto_bueno_del_gaf(
    repo, erp, docs_sii, config, ejecucion
):
    llevar_a_estado(repo, ejecucion, "Aprobado")

    approval.reabrir(repo, ejecucion.id, JEFA)
    nueva = ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)

    assert nueva.version == 2
    assert nueva.estado == "Borrador"  # no pasa por PendienteGAF
    original = [e for e in repo.listar_ejecuciones(ejecucion.periodo_id) if e.version == 1][0]
    assert original.estado == "Aprobado"  # la versión aprobada se conserva sin cambios
    assert decisiones(repo, ejecucion)[-1].decision == Decision.REABIERTO


@pytest.mark.parametrize("actor", [TESORERO, ANALISTA, GAF])
def test_solo_la_jefa_reabre(repo, ejecucion, actor):
    llevar_a_estado(repo, ejecucion, "Aprobado")

    with pytest.raises(RolNoAutorizadoError):
        approval.reabrir(repo, ejecucion.id, actor)


def test_no_se_puede_reabrir_un_periodo_no_aprobado(repo, ejecucion):
    with pytest.raises(TransicionInvalidaError):
        approval.reabrir(repo, ejecucion.id, JEFA)


@pytest.mark.parametrize(
    "estado", ["EnRevisionContable", "PendienteJefaContabilidad", "PendienteGAF"]
)
def test_en_revision_o_aprobacion_tampoco_se_reconcilia(
    repo, erp, docs_sii, config, ejecucion, estado
):
    llevar_a_estado(repo, ejecucion, estado)

    with pytest.raises(TransicionInvalidaError):
        ejecutar_conciliacion(repo, erp, docs_sii, PERIODO, TESORERO, config=config)
