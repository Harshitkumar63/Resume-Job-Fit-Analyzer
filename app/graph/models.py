"""
Knowledge graph domain models.

Defines the node/edge schema for the skill knowledge graph.
These models are Neo4j-agnostic — they represent the graph structure
that can be materialized in Neo4j, NetworkX, or any graph store.

Graph Schema:
    (Skill)-[:RELATED_TO {weight}]->(Skill)
    (Skill)-[:BELONGS_TO]->(Category)
    (Resume)-[:HAS_SKILL {proficiency}]->(Skill)
    (Job)-[:REQUIRES_SKILL {importance}]->(Skill)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class NodeType(str, Enum):
    SKILL = "Skill"
    CATEGORY = "Category"
    RESUME = "Resume"
    JOB = "Job"


class EdgeType(str, Enum):
    RELATED_TO = "RELATED_TO"
    BELONGS_TO = "BELONGS_TO"
    HAS_SKILL = "HAS_SKILL"
    REQUIRES_SKILL = "REQUIRES_SKILL"


@dataclass
class GraphNode:
    """A node in the skill knowledge graph."""

    id: str
    node_type: NodeType
    properties: dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None  # Display name

    def to_cypher_props(self) -> dict:
        """Serialize to Neo4j-compatible property dict."""
        props = {"id": self.id, **self.properties}
        if self.label:
            props["name"] = self.label
        return props


@dataclass
class GraphEdge:
    """A directed edge in the knowledge graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)

    def to_cypher_props(self) -> dict:
        """Serialize to Neo4j-compatible property dict."""
        return {"weight": self.weight, **self.properties}


@dataclass
class SkillGraph:
    """
    In-memory skill graph structure.

    Designed for both local computation (via adjacency lists)
    and Neo4j materialization (via Cypher generation).
    """

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    _adjacency: dict[str, list[tuple[str, float]]] = field(
        default_factory=dict, repr=False
    )

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append((edge.target_id, edge.weight))

    def get_neighbors(self, node_id: str) -> list[tuple[str, float]]:
        """Return (neighbor_id, weight) pairs."""
        return self._adjacency.get(node_id, [])

    def get_skill_ids(self) -> set[str]:
        """Return IDs of all Skill-type nodes."""
        return {
            nid for nid, node in self.nodes.items()
            if node.node_type == NodeType.SKILL
        }
