import base64
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1 import attendance
from app.api.v1.users import enroll_user_face
from app.core.identity import AuthenticatedIdentity, UserRole
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

    async def execute(self, _statement: object) -> None:
        self.executed += 1

    def add(self, entity: FaceEmbedding) -> None:
        self.added.append(entity)

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
    assert session.executed == 1
    assert session.commits == 1
    assert [embedding.is_primary for embedding in session.added] == [True, False]
    assert target.enrolled_at is not None and target.enrolled_at.tzinfo is UTC


class ScalarValues:
    def __init__(self, values: list[str]) -> None:
        self.values = values

    def all(self) -> list[str]:
        return self.values


class AttendanceSession:
    def __init__(self, org: Org, user: User, existing_types: list[str] | None = None) -> None:
        self.org = org
        self.user = user
        self.existing_types = existing_types or []
        self.added: list[object] = []
        self.commits = 0
        self.scalar_calls = 0

    async def get(self, model: type[object], entity_id: object) -> object | None:
        if model is Org and entity_id == self.org.id:
            return self.org
        if model is User and entity_id == self.user.id:
            return self.user
        return None

    async def scalar(self, _statement: object) -> object:
        self.scalar_calls += 1
        return self.org if self.scalar_calls == 1 else self.user

    async def scalars(self, _statement: object) -> ScalarValues:
        return ScalarValues(self.existing_types)

    def add(self, entity: object) -> None:
        self.added.append(entity)

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("INVALID_IMAGE", "invalid_image"),
        ("NO_FACE", "no_face_detected"),
        ("MULTIPLE_FACES", "multiple_faces"),
        ("LOW_QUALITY", "low_quality"),
    ],
)
def test_attendance_maps_recoverable_face_errors(
    code: str,
    expected_status: str,
) -> None:
    result = attendance.face_failure_response(FaceServiceError(400, code, "retry"))
    assert result.success is False
    assert result.status == expected_status


@pytest.mark.asyncio
async def test_pad_rejection_and_checkout_state_store_no_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor, user, org = enrollment_entities()
    identity = AuthenticatedIdentity(
        subject_id=actor.id,
        org_id=org.id,
        kind="user",
        role=UserRole.ADMIN,
    )
    request = CheckInRequest(image=encoded_jpeg())

    spoof_session = AttendanceSession(org, user)
    spoof = await attendance.process_attendance(
        "check_in",
        request,
        spoof_session,  # type: ignore[arg-type]
        identity,
        FakeFaceClient([analysis(0.2)]),  # type: ignore[arg-type]
    )
    assert spoof.status == "spoof_detected"
    assert spoof_session.added == []
    assert spoof_session.commits == 0

    async def matched(*_args: object, **_kwargs: object) -> list[tuple[object, float]]:
        return [(user.id, 0.95)]

    monkeypatch.setattr(attendance, "find_similar_faces", matched)
    checkout_session = AttendanceSession(org, user)
    checkout = await attendance.process_attendance(
        "check_out",
        request,
        checkout_session,  # type: ignore[arg-type]
        identity,
        FakeFaceClient([analysis()]),  # type: ignore[arg-type]
    )
    assert checkout.status == "not_checked_in"
    assert checkout_session.added == []
    assert checkout_session.commits == 0

    repeated_checkout_session = AttendanceSession(
        org,
        user,
        existing_types=["check_in", "check_out"],
    )
    repeated_checkout = await attendance.process_attendance(
        "check_out",
        request,
        repeated_checkout_session,  # type: ignore[arg-type]
        identity,
        FakeFaceClient([analysis()]),  # type: ignore[arg-type]
    )
    assert repeated_checkout.status == "already_checked_out"
    assert repeated_checkout_session.commits == 0

    duplicate_checkin_session = AttendanceSession(
        org,
        user,
        existing_types=["check_in"],
    )
    duplicate_checkin = await attendance.process_attendance(
        "check_in",
        request,
        duplicate_checkin_session,  # type: ignore[arg-type]
        identity,
        FakeFaceClient([analysis()]),  # type: ignore[arg-type]
    )
    assert duplicate_checkin.status == "already_checked_in"
    assert duplicate_checkin_session.commits == 0


def test_canonical_settings_validate_timezone_and_preserve_zero() -> None:
    patch = OrgSettingsPatch(late_threshold_minutes=0)
    assert patch.model_dump(exclude_none=True)["late_threshold_minutes"] == 0
    exposed = canonical_org_settings(
        {
            "allow_remote_checkin": True,
            "recognition_threshold": 0.2,
        }
    ).model_dump()
    assert "allow_remote_checkin" not in exposed
    assert "recognition_threshold" not in exposed
    with pytest.raises(ValueError):
        OrgSettingsUpdate(timezone="Not/A_Real_Zone")


def test_check_in_deadline_uses_organization_local_time_and_grace() -> None:
    _, _, org = enrollment_entities()
    org.timezone = "America/New_York"
    policy = canonical_org_settings(
        {
            "work_start_time": "09:00",
            "late_threshold_minutes": 15,
        }
    )
    assert (
        attendance.calculate_check_in_status(
            org,
            policy,
            datetime(2026, 7, 1, 13, 15, tzinfo=UTC),
        )
        == "on_time"
    )
    assert (
        attendance.calculate_check_in_status(
            org,
            policy,
            datetime(2026, 7, 1, 13, 16, tzinfo=UTC),
        )
        == "late"
    )


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
