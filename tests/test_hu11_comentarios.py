"""HU-11 · Comentar un documento (workflow/approval.py, Capa 2)."""

import pytest
from conciliasii.domain.errors import RolNoAutorizadoError, TransicionInvalidaError
from conciliasii.domain.models import Categoria, Rol
from conciliasii.workflow import approval

from .conftest import ANALISTA, GAF, JEFA, TESORERO, llevar_a_estado

LLAVE_DIF = "77300031-K|33|2211"  # Diferencia de monto en las muestras


@pytest.mark.parametrize("actor", [TESORERO, ANALISTA, JEFA])
def test_tesorero_analista_y_jefa_pueden_comentar_una_diferencia(repo, ejecucion, actor):
    if actor is ANALISTA:
        llevar_a_estado(repo, ejecucion, "EnRevisionContable", comentar=False)
    if actor is JEFA:
        llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad", comentar=True)

    comentario = approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, actor, "Error de IVA")

    assert comentario.texto == "Error de IVA"
    assert comentario.autor == actor.nombre
    assert comentario.rol == actor.rol
    assert comentario.creado_en is not None


def test_varios_comentarios_se_ven_en_orden_cronologico_con_el_rol_de_cada_autor(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "EnRevisionContable", comentar=False)
    approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, TESORERO, "Primero")
    approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, ANALISTA, "Segundo")

    comentarios = [
        c
        for c in repo.listar_comentarios(ejecucion.periodo_id, hasta_version=1)
        if c.llave == LLAVE_DIF
    ]

    assert [c.texto for c in comentarios] == ["Primero", "Segundo"]
    assert [c.rol for c in comentarios] == [Rol.TESORERO, Rol.ANALISTA_CONTABLE]


def test_los_comentarios_no_se_pueden_eliminar(repo):
    # No existe ninguna operación de borrado ni de edición, ni en el servicio ni en el repositorio.
    publicos = [n for n in dir(approval) if not n.startswith("_")] + [
        n for n in dir(repo) if not n.startswith("_")
    ]
    assert not [n for n in publicos if "eliminar" in n or "borrar" in n or "editar" in n]


def test_la_jefa_comenta_mientras_evalua(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteJefaContabilidad")

    approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, JEFA, "Confirmado con el proveedor")

    ultimo = repo.listar_comentarios(ejecucion.periodo_id, hasta_version=1)[-1]
    assert (ultimo.autor, ultimo.rol) == (JEFA.nombre, Rol.JEFA_CONTABILIDAD)


def test_el_gaf_no_comenta_pero_si_puede_leer(repo, ejecucion):
    llevar_a_estado(repo, ejecucion, "PendienteGAF")

    with pytest.raises(RolNoAutorizadoError):
        approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, GAF, "Opinión del GAF")

    assert "comentar" not in approval.acciones_permitidas(GAF.rol, "PendienteGAF")
    assert repo.listar_comentarios(ejecucion.periodo_id, hasta_version=1)  # puede leerlos


@pytest.mark.parametrize("estado", ["PendienteGAF", "Aprobado"])
def test_no_se_comenta_en_espera_del_gaf_ni_con_el_periodo_aprobado(repo, ejecucion, estado):
    llevar_a_estado(repo, ejecucion, estado)

    with pytest.raises(TransicionInvalidaError):
        approval.agregar_comentario(repo, ejecucion.id, LLAVE_DIF, JEFA, "Tarde")

    assert "comentar" not in approval.acciones_permitidas(JEFA.rol, estado)


@pytest.mark.parametrize("estado", ["Borrador", "EnRevisionContable", "PendienteJefaContabilidad"])
def test_estados_en_que_se_puede_comentar(estado):
    for rol in (Rol.TESORERO, Rol.ANALISTA_CONTABLE, Rol.JEFA_CONTABILIDAD):
        assert "comentar" in approval.acciones_permitidas(rol, estado)


def test_no_se_pueden_comentar_documentos_cuadrados(repo, ejecucion):
    cuadrado = next(
        r for r in repo.listar_resultados(ejecucion.id) if r.categoria == Categoria.CUADRADO
    )

    with pytest.raises(ValueError, match="Cuadrado"):
        approval.agregar_comentario(repo, ejecucion.id, cuadrado.llave, TESORERO, "No corresponde")
