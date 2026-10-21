"""HU-02 · Cargar el CSV del Registro de Compras (ingest/sii_csv.py)."""

import pytest
from conciliasii.domain.errors import ArchivoInvalidoError
from conciliasii.domain.models import Periodo
from conciliasii.ingest.sii_csv import leer_rcv, normalizar_rut

from .conftest import PERIODO, RCV_SII, RUT_EMPRESA, csv_sii_modificado


def test_carga_valida_devuelve_todos_los_documentos_del_archivo():
    docs = leer_rcv(RCV_SII.read_bytes(), periodo=PERIODO, rut_empresa=RUT_EMPRESA)

    assert len(docs) == 25  # el sistema muestra "cantidad de documentos leídos"
    primero = docs[0]
    assert (primero.tipo_doc, primero.folio) == (33, 1001)
    assert primero.monto_neto == 100000
    assert primero.monto_iva_recuperable == 19000
    assert primero.monto_total == 119000


def test_rut_receptor_distinto_al_de_la_empresa_se_rechaza():
    contenido = csv_sii_modificado(reemplazos={"RUT Receptor": "11.111.111-1"})

    with pytest.raises(ArchivoInvalidoError) as error:
        leer_rcv(contenido, periodo=PERIODO, rut_empresa=RUT_EMPRESA)

    assert "El RUT del archivo no corresponde a la empresa" in str(error.value)


def test_periodo_distinto_al_seleccionado_se_rechaza_indicando_ambos_periodos():
    with pytest.raises(ArchivoInvalidoError) as error:
        # El archivo es de 2026-08 y el usuario seleccionó 2026-09.
        leer_rcv(RCV_SII.read_bytes(), periodo=Periodo(2026, 9), rut_empresa=RUT_EMPRESA)

    mensaje = str(error.value)
    assert "2026-08" in mensaje  # período del archivo
    assert "2026-09" in mensaje  # período seleccionado


def test_formato_no_reconocido_informa_las_columnas_que_faltan():
    contenido = csv_sii_modificado(quitar_columnas=("Monto Neto", "Folio"))

    with pytest.raises(ArchivoInvalidoError) as error:
        leer_rcv(contenido, periodo=PERIODO, rut_empresa=RUT_EMPRESA)

    mensaje = str(error.value)
    assert "Monto Neto" in mensaje
    assert "Folio" in mensaje


def test_archivo_que_no_es_un_rcv_se_rechaza():
    with pytest.raises(ArchivoInvalidoError):
        leer_rcv(b"a,b,c\n1,2,3\n", periodo=PERIODO, rut_empresa=RUT_EMPRESA)


# HU-02 · "Reemplazar un archivo ya cargado" pide confirmación al usuario: es un comportamiento de
# la página (pages/1_Cargar_y_Conciliar.py) y no se verifica con pytest.


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("76.123.456-7", "76123456-7"),
        ("76123456-7", "76123456-7"),
        ("76.123.456-k", "76123456-K"),  # HU-05: dígito verificador siempre en mayúscula
        ("76123456-K", "76123456-K"),
        (" 77.300.031-k ", "77300031-K"),
    ],
)
def test_normalizar_rut(entrada, esperado):
    assert normalizar_rut(entrada) == esperado
