import base64
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.users import enroll_user_face
from app.core.images import ImagePayloadError, decode_image_payload
from app.core.time import local_date_bounds
from app.models.face_embedding import FaceEmbedding
from app.models.org import Org
from app.models.user import User
from app.schemas.attendance import CheckInRequest
from app.schemas.settings import (
    OrgSettingsPatch,
    OrgSettingsUpdate,
    canonical_org_settings,
)
from app.schemas.user import FaceEnrollmentRequest
from app.services.face_client import (
    FaceAnalysis,
    FaceBoundingBox,
    FaceServiceClient,
    FaceServiceError,
)


def jpeg_payload() -> bytes:
    return b"\xff\xd8\xffsynthetic-jpeg"


def encoded_jpeg() -> str:
    return base64.b64encode(jpeg_payload()).decode()


def analysis(pad_score: float = 0.9) -> FaceAnalysis:
    return FaceAnalysis(
        embedding=[0.0] * 512,
        quality_score=0.9,
        bbox=FaceBoundingBox(x1=1, y1=2, x2=20, y2=24, confidence=0.99),
        pad_live_score=pad_score,
    )


def test_strict_base64_accepts_only_matching_jpeg_or_png() -> None:
    assert decode_image_payload(encoded_jpeg()) == jpeg_payload()
    assert decode_image_payload(f"data:image/jpeg;base64,{encoded_jpeg()}") == jpeg_payload()

    with pytest.raises(ImagePayloadError) as malformed:
        decode_image_payload(f"{encoded_jpeg()}\n")
    assert malformed.value.code == "INVALID_IMAGE"

    with pytest.raises(ImagePayloadError) as mismatch:
        decode_image_payload(f"data:image/png;base64,{encoded_jpeg()}")
    assert mismatch.value.code == "INVALID_IMAGE"

    with pytest.raises(ImagePayloadError) as unsupported:
        decode_image_payload(f"data:image/gif;base64,{encoded_jpeg()}")
    assert (unsupported.value.code, unsupported.value.status_code) == (
        "UNSUPPORTED_MEDIA_TYPE",
        415,
    )


def test_base64_size_is_rejected_before_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.images.MAX_BASE64_CHARACTERS", 4)
    with pytest.raises(ImagePayloadError) as exc_info:
        decode_image_payload(encoded_jpeg())
    assert (exc_info.value.code, exc_info.value.status_code) == ("IMAGE_TOO_LARGE", 413)


@pytest.mark.asyncio
async def test_face_client_parses_strict_analysis_and_preserves_service_error() -> None:
    response_payload = analysis().model_dump(mode="json")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/analyze"
        return httpx.Response(200, json=response_payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://face",
    ) as http_client:
        result = await FaceServiceClient(http_client).analyze(jpeg_payload())
    assert len(result.embedding) == 512
    assert result.pad_live_score == 0.9

    async def error_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"detail": {"code": "INFERENCE_BUSY", "message": "busy"}},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(error_handler),
        base_url="http://face",
    ) as http_client:
        with pytest.raises(FaceServiceError) as exc_info:
            await FaceServiceClient(http_client).analyze(jpeg_payload())
    assert (exc_info.value.status_code, exc_info.value.code) == (429, "INFERENCE_BUSY")


@pytest.mark.asyncio
async def test_face_client_rejects_non_finite_or_short_embedding() -> None:
    payload = analysis().model_dump(mode="json")
    payload["embedding"] = [0.0]

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://face",
    ) as http_client:
        with pytest.raises(FaceServiceError) as exc_info:
            await FaceServiceClient(http_client).analyze(jpeg_payload())
    assert (exc_info.value.status_code, exc_info.value.code) == (500, "INFERENCE_FAILED")


class FakeFaceClient:
    def __init__(self, results: list[FaceAnalysis | FaceServiceError]) -> None:
        self.results = results

    async def analyze(self, _image: bytes) -> FaceAnalysis:
        result = self.results.pop(0)
        if isinstance(result, FaceServiceError):
            raise result
        return result


class EnrollmentSession:
    def __init__(self, user: User, org: Org) -> None:
        self.user = user
        self.org = org
        self.executed = 0
        self.scalar_calls = 0
        self.added: list[FaceEmbedding] = []
        self.commits = 0
        self.rollbacks = 0

    async def get(self, model: type[object], entity_id: object) -> object | None:
        if model is User and entity_id == self.user.id:
            return self.user
        if model is Org and entity_id == self.org.id:
            return self.org
        return None

    async def scalar(self, _statement: object) -> object:
        self.scalar_calls += 1
        return self.user if self.scalar_calls == 1 else self.org

    async def execute(
        self, _statement: object, _parameters: object | None = None
    ) -> list[object]:
        self.executed += 1
        return []

    def add(self, entity: FaceEmbedding) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def enrollment_entities() -> tuple[User, User, Org]:
    org_id = uuid4()
    org = Org(
        id=org_id,
        name="Org",
        slug="org",
        timezone="UTC",
        settings={
            "require_liveness": True,
            "liveness_threshold": 0.8,
        },
        is_active=True,
    )
    actor = User(
        id=uuid4(),
        org_id=org_id,
        name="Admin",
        role="admin",
        is_active=True,
    )
    target = User(
        id=uuid4(),
        org_id=org_id,
        name="Member",
        role="member",
        is_active=True,
    )
    return actor, target, org


@pytest.mark.asyncio
async def test_enrollment_replacement_happens_only_after_every_analysis() -> None:
    actor, target, org = enrollment_entities()
    session = EnrollmentSession(target, org)
    request = FaceEnrollmentRequest(images=[encoded_jpeg(), encoded_jpeg()])
    client = FakeFaceClient(
        [analysis(), FaceServiceError(400, "MULTIPLE_FACES", "one face required")]
    )

    with pytest.raises(HTTPException) as exc_info:
        await enroll_user_face(
            target.id,
            request,
            session,  # type: ignore[arg-type]
            actor,
            client,  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 422
    assert session.executed == 0
    assert session.added == []
    assert session.commits == 0


@pytest.mark.asyncio
async def test_enrollment_replaces_once_with_exactly_one_primary() -> None:
    actor, target, org = enrollment_entities()
    session = EnrollmentSession(target, org)
    request = FaceEnrollmentRequest(images=[encoded_jpeg(), encoded_jpeg()])

    result = await enroll_user_face(
        target.id,
        request,
        session,  # type: ignore[arg-type]
        actor,
        FakeFaceClient([analysis(), analysis()]),  # type: ignore[arg-type]
    )
    assert result.embeddings_count == 2
    assert session.executed == 4
    assert session.commits == 1
    assert [embedding.is_primary for embedding in session.added] == [True, False]
    assert target.enrolled_at is not None and target.enrolled_at.tzinfo is UTC


def test_attendance_request_accepts_only_an_image() -> None:
    request = CheckInRequest(image=encoded_jpeg())
    assert request.model_dump() == {"image": encoded_jpeg()}
    with pytest.raises(ValueError):
        CheckInRequest.model_validate(
            {
                "image": encoded_jpeg(),
                "timestamp": "2026-07-01T09:00:00Z",
                "device_id": str(uuid4()),
            }
        )


def test_schedule_policy_is_not_accepted_as_organization_settings() -> None:
    with pytest.raises(ValueError):
        OrgSettingsPatch.model_validate({"late_threshold_minutes": 0})
    exposed = canonical_org_settings(
        {
            "work_start_time": "09:00",
            "late_threshold_minutes": 15,
            "face_match_threshold": 0.75,
        }
    ).model_dump()
    assert "work_start_time" not in exposed
    assert "late_threshold_minutes" not in exposed
    assert exposed["face_match_threshold"] == 0.75
    with pytest.raises(ValueError):
        OrgSettingsUpdate(timezone="Not/A_Real_Zone")


def test_local_day_boundaries_follow_dst() -> None:
    spring_start, spring_end = local_date_bounds(
        "America/New_York",
        datetime(2026, 3, 8, tzinfo=UTC).date(),
    )
    fall_start, fall_end = local_date_bounds(
        "America/New_York",
        datetime(2026, 11, 1, tzinfo=UTC).date(),
    )
    assert (spring_end - spring_start).total_seconds() == 23 * 3600
    assert (fall_end - fall_start).total_seconds() == 25 * 3600
