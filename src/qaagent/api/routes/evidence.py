"""API routes exposing detailed evidence for a run."""

from __future__ import annotations

from pathlib import Path
from typing import List
import os

from fastapi import APIRouter, HTTPException

from qaagent.analyzers.evidence_reader import EvidenceReader
from qaagent.analyzers.cuj_config import CUJConfig
from qaagent.analyzers.coverage_mapper import CoverageMapper
from qaagent.evidence.run_manager import RunManager

router = APIRouter(tags=["evidence"])


def _get_reader(run_id: str) -> EvidenceReader:
    manager = RunManager()
    run_path = manager.base_dir / run_id
    if not run_path.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    handle = manager.load_run(run_id)
    return EvidenceReader(handle)


def _load_cuj_config() -> CUJConfig:
    config_path = os.getenv("QAAGENT_CUJ_CONFIG")
    if config_path:
        return CUJConfig.load(Path(config_path).expanduser())
    return CUJConfig.load(Path("handoff/cuj.yaml"))


@router.get("/runs/{run_id}/findings")
def get_findings(run_id: str) -> dict:
    reader = _get_reader(run_id)
    return {"findings": [finding.to_dict() for finding in reader.read_findings()]}


@router.get("/runs/{run_id}/coverage")
def get_coverage(run_id: str) -> dict:
    reader = _get_reader(run_id)
    return {"coverage": [record.to_dict() for record in reader.read_coverage()]}


@router.get("/runs/{run_id}/churn")
def get_churn(run_id: str) -> dict:
    reader = _get_reader(run_id)
    return {"churn": [record.to_dict() for record in reader.read_churn()]}


@router.get("/runs/{run_id}/risks")
def get_risks(run_id: str) -> dict:
    reader = _get_reader(run_id)
    risks = [risk.to_dict() for risk in reader.read_risks()]
    return {"risks": risks}


@router.get("/runs/{run_id}/recommendations")
def get_recommendations(run_id: str) -> dict:
    reader = _get_reader(run_id)
    recommendations = [rec.to_dict() for rec in reader.read_recommendations()]
    return {"recommendations": recommendations}


@router.get("/runs/{run_id}/cuj")
def get_cuj_coverage(run_id: str) -> dict:
    reader = _get_reader(run_id)
    config = _load_cuj_config()
    if not config.journeys:
        return {"journeys": []}

    mapper = CoverageMapper(config)
    mapped = mapper.map_coverage(reader.read_coverage())

    payload: List[dict] = []
    for item in mapped:
        components = [
            {"component": component, "coverage": value}
            for component, value in item.components.items()
        ]
        payload.append(
            {
                "id": item.journey.id,
                "name": item.journey.name,
                "coverage": item.coverage,
                "target": item.target,
                "gap": max(0.0, item.target - item.coverage),
                "components": components,
                "apis": item.journey.apis,
                "acceptance": item.journey.acceptance,
            }
        )

    return {"journeys": payload}
