"""API routes for listing runs and manifest details."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

from qaagent.evidence.run_manager import RunManager
from qaagent.analyzers.evidence_reader import EvidenceReader

router = APIRouter(tags=["runs"])


@router.get("/runs")
def list_runs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict:
    manager = RunManager()
    runs_root = manager.base_dir
    run_ids = sorted([p.name for p in runs_root.iterdir() if p.is_dir()], reverse=True)
    sliced = run_ids[offset : offset + limit]

    runs: List[dict] = []
    for run_id in sliced:
        handle = manager.load_run(run_id)
        runs.append(
            {
                "run_id": run_id,
                "created_at": handle.manifest.created_at,
                "target": handle.manifest.target.to_dict(),
                "counts": handle.manifest.counts,
            }
        )

    return {"runs": runs, "total": len(run_ids), "limit": limit, "offset": offset}


@router.get("/runs/trends")
def get_run_trends(limit: int = Query(10, ge=1, le=200)) -> dict:
    """Return high-level metrics per run for trend visualizations."""

    manager = RunManager()
    runs_root = manager.base_dir
    run_ids = sorted([p.name for p in runs_root.iterdir() if p.is_dir()], reverse=True)
    selected = run_ids[:limit]

    points: List[Dict[str, object]] = []
    for run_id in reversed(selected):  # chronological order (oldest first)
        handle = manager.load_run(run_id)
        reader = EvidenceReader(handle)

        coverage_records = reader.read_coverage()
        overall_record = next((record for record in coverage_records if record.component == "__overall__"), None)
        component_values = [record.value for record in coverage_records if record.component != "__overall__"]
        average_coverage = sum(component_values) / len(component_values) if component_values else None

        risks = reader.read_risks()
        risk_counts: Dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        total_risk_score = 0.0
        for risk in risks:
            band = risk.band or "P3"
            if band not in risk_counts:
                risk_counts[band] = 0
            risk_counts[band] += 1
            total_risk_score += risk.score

        points.append(
            {
                "run_id": run_id,
                "created_at": handle.manifest.created_at,
                "average_coverage": average_coverage,
                "overall_coverage": getattr(overall_record, "value", None),
                "high_risk_count": risk_counts.get("P0", 0) + risk_counts.get("P1", 0),
                "risk_counts": risk_counts,
                "total_risks": len(risks),
                "average_risk_score": (total_risk_score / len(risks)) if risks else None,
            }
        )

    points.sort(key=lambda item: item["created_at"])
    return {"trend": points, "total": len(run_ids)}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    manager = RunManager()
    run_path = manager.base_dir / run_id
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    handle = manager.load_run(run_id)
    return handle.manifest.to_dict()
