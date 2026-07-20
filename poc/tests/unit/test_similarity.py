"""Tests del algoritmo de clustering (union-find) del dominio."""

from taskbot_advisor.domain.entities import InteractionType, RiskLevel, Taskbot
from taskbot_advisor.domain.similarity import build_clusters, cluster_of


def _bot(id_: str, name: str) -> Taskbot:
    return Taskbot(
        id=id_, name=name, purpose=name, apps=(), interactions=(InteractionType.API,),
        frequency="diaria", risk=RiskLevel.LOW, dependencies=(), known_similarity="",
    )


def _score(a: Taskbot, b: Taskbot) -> float:
    # Similitud de juguete: 100 si comparten prefijo "dup", 0 en otro caso.
    return 100.0 if a.name[:3] == b.name[:3] == "dup" else 0.0


def test_agrupa_duplicados_y_separa_distintos():
    bots = [_bot("1", "dupA"), _bot("2", "dupB"), _bot("3", "otro")]
    clusters = build_clusters(bots, _score, threshold=82.0)
    grupos = {c.member_ids for c in clusters}
    assert ("1", "2") in grupos
    assert ("3",) in grupos


def test_transitividad_union_find():
    # A~B y B~C deben terminar en el mismo cluster.
    def chain_score(a, b):
        pares = {("1", "2"), ("2", "3")}
        return 100.0 if (a.id, b.id) in pares or (b.id, a.id) in pares else 0.0

    bots = [_bot("1", "x"), _bot("2", "y"), _bot("3", "z")]
    clusters = build_clusters(bots, chain_score, threshold=82.0)
    assert len(clusters) == 1
    assert clusters[0].size == 3


def test_cluster_is_duplicate_group():
    bots = [_bot("1", "dupA"), _bot("2", "dupB")]
    clusters = build_clusters(bots, _score, threshold=82.0)
    assert clusters[0].is_duplicate_group is True


def test_cluster_of_localiza_miembro():
    bots = [_bot("1", "dupA"), _bot("2", "dupB"), _bot("3", "solo")]
    clusters = build_clusters(bots, _score, threshold=82.0)
    assert cluster_of("1", clusters).size == 2
    assert cluster_of("3", clusters).size == 1


def test_cluster_of_no_encontrado_devuelve_none():
    bots = [_bot("1", "dupA")]
    clusters = build_clusters(bots, _score, threshold=82.0)
    assert cluster_of("999", clusters) is None
