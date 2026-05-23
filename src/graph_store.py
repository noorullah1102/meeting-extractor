"""
Knowledge Graph Store
NetworkX-based graph for cross-meeting entity-relationship querying.
"""

import json
import os
from collections import defaultdict

import networkx as nx

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "data", "graph.json")


def _get_graph() -> nx.DiGraph:
    """Load graph from disk, or return a fresh one."""
    if os.path.exists(GRAPH_PATH):
        with open(GRAPH_PATH) as f:
            return nx.node_link_graph(json.load(f), directed=True)
    return nx.DiGraph()


def _save_graph(graph: nx.DiGraph) -> None:
    """Persist graph to disk."""
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    with open(GRAPH_PATH, "w") as f:
        json.dump(nx.node_link_data(graph), f, indent=2)


def add_triples(triples: list[dict], meeting_id: str) -> nx.DiGraph:
    """Add extracted triples to the graph, tagged with a meeting ID."""
    graph = _get_graph()
    for triple in triples:
        subj = triple["subject"]
        obj = triple["object"]
        graph.add_edge(subj, obj, predicate=triple["predicate"], meeting_id=meeting_id)
    _save_graph(graph)
    return graph


def get_person_tasks(name: str) -> list[dict]:
    """All outgoing edges from a person node (tasks they own)."""
    graph = _get_graph()
    results = []
    for _u, v, data in graph.out_edges(name, data=True):
        results.append({"predicate": data["predicate"], "object": v, "meeting_id": data["meeting_id"]})
    for u, _v, data in graph.in_edges(name, data=True):
        results.append({"subject": u, "predicate": data["predicate"], "meeting_id": data["meeting_id"]})
    return results


def get_project_status(project: str) -> list[dict]:
    """All edges connected to a project/client node."""
    graph = _get_graph()
    results = []
    for u, v, data in graph.out_edges(project, data=True):
        results.append({"subject": u, "predicate": data["predicate"], "object": v, "meeting_id": data["meeting_id"]})
    for u, v, data in graph.in_edges(project, data=True):
        results.append({"subject": u, "predicate": data["predicate"], "object": v, "meeting_id": data["meeting_id"]})
    return results


def get_pending() -> list[dict]:
    """All triples whose predicate suggests open/pending status."""
    pending_keywords = {"owns_task", "handles", "pending", "waiting", "requires", "requested", "follow_up"}
    graph = _get_graph()
    results = []
    for u, v, data in graph.edges(data=True):
        if data["predicate"].lower() in pending_keywords:
            results.append({"subject": u, "predicate": data["predicate"], "object": v, "meeting_id": data["meeting_id"]})
    return results


def get_overloaded(threshold: int = 3) -> dict[str, list[str]]:
    """People with N or more outgoing 'owns_task' / 'handles' edges."""
    graph = _get_graph()
    counts = defaultdict(list)
    for u, v, data in graph.edges(data=True):
        if data["predicate"] in ("owns_task", "handles"):
            counts[u].append(v)
    return {person: tasks for person, tasks in counts.items() if len(tasks) >= threshold}
