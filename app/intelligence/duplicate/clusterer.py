"""
app.intelligence.duplicate.clusterer
====================================
Graph-based connected components clustering for duplicate candidate pairs.
Consolidates transitive pairwise relationships (A <-> B, B <-> C) into unified clusters.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set

from app.intelligence.common.enums import DuplicateMatchType
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster


class DuplicateClusterer:
    """
    Groups pairwise duplicate candidate matches into canonical clusters using connected components.
    Avoids redundant independent alerts for multi-invoice duplicate groups.
    """

    @staticmethod
    def cluster_candidates(candidates: List[DuplicateCandidate]) -> List[DuplicateCluster]:
        """
        Takes pairwise candidates and returns consolidated DuplicateClusters.
        """
        # Filter to qualifying duplicate matches
        qualifying = [
            c for c in candidates
            if c.match_type in (
                DuplicateMatchType.EXACT_DUPLICATE,
                DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE,
                DuplicateMatchType.POSSIBLE_DUPLICATE,
            )
            and not c.is_recurring_legitimate
        ]

        if not qualifying:
            return []

        # Build adjacency graph
        adj: Dict[str, Set[str]] = defaultdict(set)
        edge_map: Dict[Tuple[str, str], DuplicateCandidate] = {}

        for c in qualifying:
            src = c.source_invoice_id
            dst = c.matched_invoice_id
            adj[src].add(dst)
            adj[dst].add(src)
            edge_map[(min(src, dst), max(src, dst))] = c

        # Find connected components via BFS
        visited: Set[str] = set()
        clusters: List[DuplicateCluster] = []
        cluster_idx = 1

        for node in sorted(adj.keys()):
            if node in visited:
                continue

            # BFS traversal
            component: List[str] = []
            queue = [node]
            visited.add(node)

            while queue:
                curr = queue.pop(0)
                component.append(curr)
                for neighbor in sorted(adj[curr]):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(component) >= 2:
                sorted_invoices = sorted(component)
                cid = f"CLUST-DUP-{cluster_idx:03d}"
                cluster_idx += 1

                # Gather candidates belonging to this cluster
                cluster_candidates: List[DuplicateCandidate] = []
                scores: List[float] = []
                has_exact = False
                has_high = False

                for i in range(len(sorted_invoices)):
                    for j in range(i + 1, len(sorted_invoices)):
                        pair_key = (sorted_invoices[i], sorted_invoices[j])
                        cand = edge_map.get(pair_key)
                        if cand:
                            cand.cluster_id = cid
                            cluster_candidates.append(cand)
                            scores.append(cand.similarity_score)
                            if cand.match_type == DuplicateMatchType.EXACT_DUPLICATE:
                                has_exact = True
                            elif cand.match_type == DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE:
                                has_high = True

                avg_sim = round(sum(scores) / len(scores), 2) if scores else 0.0

                if has_exact:
                    match_type = DuplicateMatchType.EXACT_DUPLICATE
                elif has_high:
                    match_type = DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE
                else:
                    match_type = DuplicateMatchType.POSSIBLE_DUPLICATE

                # Extract common attributes from candidate evidence
                common_attrs: Dict[str, Any] = {
                    "cluster_size": len(sorted_invoices),
                    "candidate_pair_count": len(cluster_candidates),
                }
                if cluster_candidates and cluster_candidates[0].evidence:
                    ev = cluster_candidates[0].evidence
                    if "supplier_gstin" in ev:
                        common_attrs["supplier_gstin"] = ev["supplier_gstin"]
                    if "taxable_value_source" in ev:
                        common_attrs["taxable_value"] = ev["taxable_value_source"]

                clusters.append(
                    DuplicateCluster(
                        cluster_id=cid,
                        invoice_ids=sorted_invoices,
                        primary_invoice_id=sorted_invoices[0],
                        match_type=match_type,
                        average_similarity=avg_sim,
                        common_attributes=common_attrs,
                        candidates=cluster_candidates,
                    )
                )

        return clusters
