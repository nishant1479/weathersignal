from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from backend.app.models.models import (
    ReportModel, ClaimModel, InvestigationModel, EvidenceItemModel, EvidenceAssessmentModel, FinalDecisionModel
)
from backend.app.schemas.schemas import ReportCreate, ReportStatus


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_report(self, report_in: ReportCreate) -> ReportModel:
        report = ReportModel(
            original_text=report_in.original_text,
            event_time=report_in.event_time,
            place_text=report_in.place_text,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            attachment_reference=report_in.attachment_reference,
            status=ReportStatus.PENDING
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_report_by_id(self, report_id: str) -> Optional[ReportModel]:
        stmt = (
            select(ReportModel)
            .where(ReportModel.id == report_id)
            .options(selectinload(ReportModel.claims), selectinload(ReportModel.investigations))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_reports(self, skip: int = 0, limit: int = 50) -> List[ReportModel]:
        stmt = (
            select(ReportModel)
            .order_by(ReportModel.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class InvestigationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_investigation(self, report_id: str) -> InvestigationModel:
        inv = InvestigationModel(
            report_id=report_id,
            status=ReportStatus.INVESTIGATING
        )
        self.db.add(inv)
        await self.db.commit()
        await self.db.refresh(inv)
        return inv

    async def get_investigation(self, investigation_id: str) -> Optional[InvestigationModel]:
        stmt = (
            select(InvestigationModel)
            .where(InvestigationModel.id == investigation_id)
            .options(
                selectinload(InvestigationModel.report).selectinload(ReportModel.claims),
                selectinload(InvestigationModel.evidence_items).selectinload(EvidenceItemModel.assessments),
                selectinload(InvestigationModel.decision)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_latest_by_report(self, report_id: str) -> Optional[InvestigationModel]:
        stmt = (
            select(InvestigationModel)
            .where(InvestigationModel.report_id == report_id)
            .order_by(InvestigationModel.created_at.desc())
            .options(
                selectinload(InvestigationModel.report).selectinload(ReportModel.claims),
                selectinload(InvestigationModel.evidence_items),
                selectinload(InvestigationModel.decision)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_review_queue(self, skip: int = 0, limit: int = 50) -> List[InvestigationModel]:
        stmt = (
            select(InvestigationModel)
            .join(FinalDecisionModel, InvestigationModel.id == FinalDecisionModel.investigation_id)
            .where(FinalDecisionModel.review_required == True)  # noqa: E712
            .where(FinalDecisionModel.reviewer_decision == None)  # noqa: E711
            .order_by(InvestigationModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(InvestigationModel.report).selectinload(ReportModel.claims),
                selectinload(InvestigationModel.evidence_items),
                selectinload(InvestigationModel.decision)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
