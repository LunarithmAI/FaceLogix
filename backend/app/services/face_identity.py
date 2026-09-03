from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_embedding import FaceEmbedding
from app.services.face_client import FaceAnalysis

FACE_AMBIGUITY_MARGIN = 0.02


@dataclass(frozen=True, slots=True)
class FaceIdentityMatch:
    status: Literal["recognized", "unknown", "ambiguous"]
    user_id: UUID | None = None
    score: float | None = None


async def lock_face_identity_namespace(db: AsyncSession, org_id: UUID) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:namespace, 0))"),
        {"namespace": f"face-identity:{org_id}"},
    )


async def find_face_candidates(
    db: AsyncSession,
    *,
    org_id: UUID,
    embedding: list[float],
    threshold: float,
    exclude_user_id: UUID | None = None,
    limit: int = 2,
) -> list[tuple[UUID, float]]:
    embedding_string = f"[{','.join(map(str, embedding))}]"
    rows = await db.execute(
        text(
            """
            SELECT
                fe.user_id,
                MAX(1 - (fe.embedding <=> CAST(:embedding AS vector))) AS score
            FROM face_embeddings fe
            JOIN users u ON u.id = fe.user_id
            WHERE u.org_id = CAST(:org_id AS uuid)
              AND u.is_active = TRUE
              AND (
                CAST(:exclude_user_id AS uuid) IS NULL
                OR u.id <> CAST(:exclude_user_id AS uuid)
              )
              AND 1 - (fe.embedding <=> CAST(:embedding AS vector)) >= :threshold
            GROUP BY fe.user_id
            ORDER BY score DESC, fe.user_id
            LIMIT :limit
            """
        ),
        {
            "embedding": embedding_string,
            "org_id": str(org_id),
            "exclude_user_id": str(exclude_user_id) if exclude_user_id else None,
            "threshold": threshold,
            "limit": limit,
        },
    )
    return [(UUID(str(row[0])), float(row[1])) for row in rows]


async def identify_face(
    db: AsyncSession,
    *,
    org_id: UUID,
    embedding: list[float],
    threshold: float,
) -> FaceIdentityMatch:
    candidates = await find_face_candidates(
        db,
        org_id=org_id,
        embedding=embedding,
        threshold=threshold,
    )
    if not candidates:
        return FaceIdentityMatch(status="unknown")
    if len(candidates) > 1 and candidates[0][1] - candidates[1][1] <= FACE_AMBIGUITY_MARGIN:
        return FaceIdentityMatch(status="ambiguous", score=candidates[0][1])
    return FaceIdentityMatch(
        status="recognized",
        user_id=candidates[0][0],
        score=candidates[0][1],
    )


async def replace_face_identity(
    db: AsyncSession,
    *,
    org_id: UUID,
    user_id: UUID,
    analyses: list[FaceAnalysis],
    collision_threshold: float,
) -> None:
    await lock_face_identity_namespace(db, org_id)
    for analysis in analyses:
        collision = await find_face_candidates(
            db,
            org_id=org_id,
            embedding=analysis.embedding,
            threshold=collision_threshold,
            exclude_user_id=user_id,
            limit=1,
        )
        if collision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "FACE_IDENTITY_CONFLICT",
                    "message": "Face identity matches another active user",
                    "conflicting_user_id": str(collision[0][0]),
                },
            )
    await db.execute(delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id))
    for index, analysis in enumerate(analyses):
        db.add(
            FaceEmbedding(
                user_id=user_id,
                embedding=analysis.embedding,
                quality_score=analysis.quality_score,
                is_primary=index == 0,
            )
        )
    await db.flush()
