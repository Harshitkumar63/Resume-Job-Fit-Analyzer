"""
Knowledge graph service.

Provides a graph abstraction layer that:
1. Builds an in-memory skill graph from normalized skills
2. Computes graph-based similarity metrics
3. Can optionally materialize to Neo4j (when available)

Design decision: We compute graph metrics in-memory (NetworkX-style)
rather than requiring a running Neo4j instance. This keeps the system
functional in lightweight deployments while being Neo4j-ready.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.graph.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    SkillGraph,
)

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for building and querying skill knowledge graphs.

    Neo4j integration:
        When neo4j driver is available, the service can push the
        in-memory graph to Neo4j for persistent storage and
        complex Cypher queries. Without Neo4j, all computation
        is done in-memory.
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
    ):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None  # Neo4j driver, lazily initialized

    def _get_neo4j_driver(self):
        """
        Attempt to create a Neo4j driver connection.

        Returns None if neo4j package is not installed or connection fails.
        This makes Neo4j optional — the system degrades gracefully.
        """
        if self._driver is not None:
            return self._driver
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            self._driver.verify_connectivity()
            logger.info("Neo4j connected at %s", self._uri)
            return self._driver
        except ImportError:
            logger.info("neo4j package not installed — using in-memory graph only")
            return None
        except Exception as exc:
            logger.warning("Neo4j connection failed: %s — using in-memory graph", exc)
            return None

    def build_skill_graph(
        self,
        resume_skills: list[str],
        job_skills: list[str],
        skill_categories: Optional[dict[str, str]] = None,
    ) -> SkillGraph:
        """
        Build a bipartite-ish skill graph for resume–job matching.

        Nodes:
            - One node per unique skill (from resume + job)
            - Optional category nodes

        Edges:
            - RELATED_TO between skills that co-occur in resume and job
            - BELONGS_TO from skill to its category (if categories provided)

        Args:
            resume_skills: Canonical skill names from the resume.
            job_skills: Required + preferred skills from the JD.
            skill_categories: Optional mapping of skill → category.

        Returns:
            Populated SkillGraph.
        """
        graph = SkillGraph()
        categories = skill_categories or {}

        # Create skill nodes
        all_skills = set(resume_skills) | set(job_skills)
        for skill in all_skills:
            node = GraphNode(
                id=f"skill:{skill.lower()}",
                node_type=NodeType.SKILL,
                label=skill,
                properties={
                    "in_resume": skill in resume_skills,
                    "in_job": skill in job_skills,
                },
            )
            graph.add_node(node)

        # Create category nodes and edges
        if categories:
            seen_categories: set[str] = set()
            for skill in all_skills:
                cat = categories.get(skill, "Unknown")
                cat_id = f"category:{cat.lower()}"
                if cat_id not in seen_categories:
                    graph.add_node(GraphNode(
                        id=cat_id,
                        node_type=NodeType.CATEGORY,
                        label=cat,
                    ))
                    seen_categories.add(cat_id)
                graph.add_edge(GraphEdge(
                    source_id=f"skill:{skill.lower()}",
                    target_id=cat_id,
                    edge_type=EdgeType.BELONGS_TO,
                ))

        # Create RELATED_TO edges between overlapping skills
        overlap = set(resume_skills) & set(job_skills)
        overlap_list = sorted(overlap)
        for i, s1 in enumerate(overlap_list):
            for s2 in overlap_list[i + 1:]:
                graph.add_edge(GraphEdge(
                    source_id=f"skill:{s1.lower()}",
                    target_id=f"skill:{s2.lower()}",
                    edge_type=EdgeType.RELATED_TO,
                    weight=1.0,
                ))

        logger.info(
            "Built skill graph: %d nodes, %d edges",
            len(graph.nodes), len(graph.edges),
        )
        return graph

    def compute_graph_similarity(
        self,
        graph: SkillGraph,
        resume_skills: list[str],
        job_skills: list[str],
    ) -> float:
        """
        Compute graph-based similarity score.

        Uses a combination of:
        1. Jaccard overlap on skill sets
        2. Category overlap bonus (shared categories boost score)
        3. Graph connectivity score (dense connections = better fit)

        Returns:
            Float in [0, 1].
        """
        if not job_skills:
            return 0.0

        resume_set = {s.lower() for s in resume_skills}
        job_set = {s.lower() for s in job_skills}

        # 1. Jaccard overlap
        intersection = resume_set & job_set
        union = resume_set | job_set
        jaccard = len(intersection) / len(union) if union else 0.0

        # 2. Coverage: fraction of job skills present in resume
        coverage = len(intersection) / len(job_set) if job_set else 0.0

        # 3. Category overlap bonus
        resume_categories = set()
        job_categories = set()
        for nid, node in graph.nodes.items():
            if node.node_type == NodeType.SKILL:
                neighbors = graph.get_neighbors(nid)
                for neighbor_id, _ in neighbors:
                    neighbor_node = graph.nodes.get(neighbor_id)
                    if neighbor_node and neighbor_node.node_type == NodeType.CATEGORY:
                        if node.properties.get("in_resume"):
                            resume_categories.add(neighbor_id)
                        if node.properties.get("in_job"):
                            job_categories.add(neighbor_id)

        cat_overlap = 0.0
        if job_categories:
            cat_overlap = len(resume_categories & job_categories) / len(job_categories)

        # Weighted combination
        score = 0.4 * coverage + 0.35 * jaccard + 0.25 * cat_overlap

        logger.debug(
            "Graph similarity: coverage=%.3f, jaccard=%.3f, cat_overlap=%.3f → %.3f",
            coverage, jaccard, cat_overlap, score,
        )
        return min(score, 1.0)

    async def push_to_neo4j(self, graph: SkillGraph) -> bool:
        """
        Materialize the in-memory graph to Neo4j.

        Returns True if successful, False if Neo4j is unavailable.
        """
        driver = self._get_neo4j_driver()
        if driver is None:
            return False

        try:
            async with driver.session() as session:
                # Create nodes
                for node in graph.nodes.values():
                    await session.run(
                        f"MERGE (n:{node.node_type.value} {{id: $id}}) SET n += $props",
                        id=node.id,
                        props=node.to_cypher_props(),
                    )
                # Create edges
                for edge in graph.edges:
                    await session.run(
                        f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
                        f"MERGE (a)-[r:{edge.edge_type.value}]->(b) "
                        f"SET r += $props",
                        src=edge.source_id,
                        tgt=edge.target_id,
                        props=edge.to_cypher_props(),
                    )
            logger.info("Graph pushed to Neo4j: %d nodes, %d edges", len(graph.nodes), len(graph.edges))
            return True
        except Exception as exc:
            logger.error("Failed to push graph to Neo4j: %s", exc)
            return False
