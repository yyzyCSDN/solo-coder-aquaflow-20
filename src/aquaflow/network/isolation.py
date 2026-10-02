"""Bidirectional isolation analysis for a water distribution network.

Open pipes are treated as *undirected* connections: water can cross a pipe
from either endpoint regardless of the order in which the topology record
names them.  A node counts as supplied when it can reach at least one
available source through a chain of open pipes whose valves are not closed;
every other declared node is reported as isolated.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Pipe:
    id: str
    a: str
    b: str
    open: bool = True


# ---------------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------------

def _as_id_set(values: Iterable[Any]) -> set[str]:
    """Coerce any iterable of node/pipe identifiers into a set of strings."""
    return {str(v) for v in values}


def _as_pipe(record: Any) -> Pipe:
    """Normalize one topology record into a :class:`Pipe`."""
    if isinstance(record, Pipe):
        return Pipe(str(record.id), str(record.a), str(record.b), bool(record.open))
    if isinstance(record, dict):
        return Pipe(
            str(record["id"]),
            str(record["a"]),
            str(record["b"]),
            bool(record.get("open", True)),
        )
    if isinstance(record, (tuple, list)):
        if len(record) == 3:
            pid, a, b = record
            return Pipe(str(pid), str(a), str(b), True)
        if len(record) >= 4:
            pid, a, b, is_open = record[:4]
            return Pipe(str(pid), str(a), str(b), bool(is_open))
    raise TypeError(f"unsupported pipe record: {record!r}")


def normalize_inputs(
    nodes: Iterable[Any],
    pipes: Iterable[Any],
    closed: Iterable[Any],
    sources: Iterable[Any],
) -> tuple[set[str], list[Pipe], set[str], set[str]]:
    """Normalize raw topology input into typed, order-independent values."""
    node_set = _as_id_set(nodes)
    pipe_rows = [_as_pipe(record) for record in pipes]
    closed_set = _as_id_set(closed)
    source_set = _as_id_set(sources)
    return node_set, pipe_rows, closed_set, source_set


# ---------------------------------------------------------------------------
# Connectivity traversal
# ---------------------------------------------------------------------------

def _adjacency(nodes: set[str], pipes: list[Pipe], closed: set[str]) -> dict[str, set[str]]:
    """Build the undirected graph of open pipes.

    A pipe connects its two endpoints in both directions.  Shut pipes
    (``open=False``) and pipes whose valve is in ``closed`` are omitted, so a
    closed valve severs the connection even when the topology record still
    lists the pipe.
    """
    adj: dict[str, set[str]] = defaultdict(set)
    adj.update((node, set()) for node in nodes)
    for pipe in pipes:
        if not pipe.open or pipe.id in closed:
            continue
        adj[pipe.a].add(pipe.b)
        adj[pipe.b].add(pipe.a)
    return adj


def _supplied(adj: dict[str, set[str]], sources: set[str]) -> set[str]:
    """Multi-source traversal: every node reachable from any source is fed."""
    seen = set(sources)
    queue: deque[str] = deque(sorted(seen))
    while queue:
        node = queue.popleft()
        for neighbor in sorted(adj.get(node, ())):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen


def isolated(nodes, pipes, closed, sources) -> set[str]:
    """Return the declared nodes that no available source can supply."""
    node_set, pipe_rows, closed_set, source_set = normalize_inputs(nodes, pipes, closed, sources)
    adj = _adjacency(node_set, pipe_rows, closed_set)
    return node_set - _supplied(adj, source_set)


# ---------------------------------------------------------------------------
# Final isolation report
# ---------------------------------------------------------------------------

def isolation_report(nodes, pipes, closed, sources) -> dict[str, Any]:
    """Produce a deterministic isolation report.

    All node lists in the report are sorted, so callers can compare or emit
    them without depending on unordered set iteration.
    """
    node_set, pipe_rows, closed_set, source_set = normalize_inputs(nodes, pipes, closed, sources)
    adj = _adjacency(node_set, pipe_rows, closed_set)
    supplied = _supplied(adj, source_set)
    cut = node_set - supplied
    return {
        "isolated": sorted(cut),
        "isolated_count": len(cut),
        "supplied": sorted(node_set & supplied),
        "sources": sorted(source_set),
        "closed": sorted(closed_set),
    }
