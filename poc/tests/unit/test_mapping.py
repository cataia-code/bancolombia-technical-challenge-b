"""Tests del mapper y del parseo de tipos de interaccion multivaluados."""

from taskbot_advisor.domain.entities import InteractionType
from taskbot_advisor.infrastructure.mapping import to_taskbot

I = InteractionType


def test_parse_many_multivalor():
    assert set(I.parse_many("email, archivo, UI legacy")) == {I.EMAIL, I.FILE, I.UI_LEGACY}


def test_parse_many_deduplica_y_descarta_desconocidos():
    assert I.parse_many("API, api, cosa-rara") == (I.API,)


def test_parse_many_vacio_es_unknown():
    assert I.parse_many("") == (I.UNKNOWN,)
    assert I.parse_many("   ") == (I.UNKNOWN,)


def test_to_taskbot_mapea_campos_reales():
    record = {
        "id": "TB01",
        "nombre": "TB_Recepcion_Facturas",
        "proposito": "Descargar facturas",
        "aplicaciones": "Outlook, SharePoint, SAP ECC",
        "tipo_interaccion": "email, archivo, UI legacy",
        "frecuencia": "Cada hora",
        "riesgo": "Medio",
        "dependencias": "Buzon AP, credenciales SAP",
    }
    bot = to_taskbot(record)
    assert bot.id == "TB01"
    assert bot.apps == ("Outlook", "SharePoint", "SAP ECC")
    assert bot.has(I.UI_LEGACY)
    assert len(bot.dependencies) == 2
