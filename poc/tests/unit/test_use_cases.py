"""Tests del caso de uso AnalyzeInventory con puertos de prueba (stubs)."""

from taskbot_advisor.application.use_cases import AnalyzeInventory
from taskbot_advisor.domain.entities import InteractionType, RiskLevel, Taskbot


def _bot(id_):
    return Taskbot(
        id=id_, name=f"Bot {id_}", purpose="p", apps=("A",),
        interactions=(InteractionType.API,), frequency="diaria", risk=RiskLevel.LOW,
    )


class _Repo:
    def __init__(self, bots, errors=None):
        self._bots, self._errors = bots, errors or []

    def load(self):
        return list(self._bots), list(self._errors)


class _Sim:
    # Sin fit(): verifica que el caso de uso no lo exige.
    def score(self, a, b):
        return 0.0


class _TrainableSim(_Sim):
    def __init__(self):
        self.fitted_with = None

    def fit(self, bots):
        self.fitted_with = list(bots)


class _AdvisorOK:
    def explain(self, bot, rec):
        return "ok"


class _AdvisorBoom:
    """Lanza excepcion solo para un taskbot: prueba el fail-soft por item."""

    def __init__(self, boom_id):
        self._boom = boom_id

    def explain(self, bot, rec):
        if bot.id == self._boom:
            raise RuntimeError("fallo justificando")
        return "ok"


def test_ejecuta_y_propaga_errores_de_carga():
    uc = AnalyzeInventory(
        _Repo([_bot("1")], errors=[{"row": 9, "error": "x"}]), _Sim(), _AdvisorOK(), 82.0
    )
    result = uc.execute(run_id="r")
    assert result.total == 1
    assert any(e.get("row") == 9 for e in result.errors)


def test_fail_soft_por_item_no_tumba_el_lote():
    uc = AnalyzeInventory(
        _Repo([_bot("1"), _bot("2")]), _Sim(), _AdvisorBoom("1"), 82.0
    )
    result = uc.execute(run_id="r")
    # El bot "2" se procesa; el "1" queda registrado como error.
    assert result.total == 1
    assert any(e.get("taskbot_id") == "1" for e in result.errors)


def test_run_id_autogenerado_cuando_no_se_pasa():
    uc = AnalyzeInventory(_Repo([_bot("1")]), _Sim(), _AdvisorOK(), 82.0)
    result = uc.execute()
    assert result.run_id and len(result.run_id) >= 6


def test_similarity_trainable_se_calibra_por_puerto_explicito():
    sim = _TrainableSim()
    uc = AnalyzeInventory(_Repo([_bot("1")]), sim, _AdvisorOK(), 82.0)
    uc.execute(run_id="r")
    assert [b.id for b in sim.fitted_with] == ["1"]
