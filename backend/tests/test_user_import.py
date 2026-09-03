import io
import json
import os
import zipfile
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.deps import require_operator
from app.api.v1 import users
from app.core.database import get_db
from app.core.identity import UserRole
from app.models.face_embedding import FaceEmbedding
from app.models.org import Org
from app.models.organizational_unit import OrganizationalUnit
from app.models.user import User
from app.services.face_client import (
    FaceAnalysis,
    FaceBoundingBox,
    FaceServiceError,
    get_face_client,
)
from app.services.user_import import UserImportPackageError, parse_user_import_archive


def import_package(csv_text: str, images: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("people.csv", csv_text)
        for path, content in images.items():
            archive.writestr(path, content)
    return output.getvalue()


def face_analysis(index: int = 0) -> FaceAnalysis:
    embedding = [0.0] * 512
    embedding[index] = 1.0
    return FaceAnalysis(
        embedding=embedding,
        quality_score=0.9,
        bbox=FaceBoundingBox(x1=1, y1=1, x2=20, y2=20, confidence=0.99),
        pad_live_score=0.95,
    )


class FakeFaceClient:
    def __init__(self, fail_on_call: int | None = None) -> None:
        self.calls = 0
        self.fail_on_call = fail_on_call

    async def analyze(self, image: bytes) -> FaceAnalysis:
        assert image.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n"))
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise FaceServiceError(400, "LOW_QUALITY", "Face quality is too low")
        return face_analysis(self.calls - 1)


def test_import_package_parser_validates_rows_and_images() -> None:
    package = import_package(
        "external_id,name,email,unit,image_1,image_2\n"
        "EMP-1,Ada Lovelace,ada@example.com,Engineering,faces/ada.jpg,faces/ada-2.png\n",
        {
            "faces/ada.jpg": b"\xff\xd8\xffjpeg",
            "faces/ada-2.png": b"\x89PNG\r\n\x1a\npng",
        },
    )

    parsed = parse_user_import_archive(io.BytesIO(package))

    assert parsed.total_rows == 1
    assert parsed.errors == ()
    assert parsed.rows[0].external_id == "EMP-1"
    assert parsed.rows[0].unit == "Engineering"
    assert parsed.rows[0].image_paths == ("faces/ada.jpg", "faces/ada-2.png")
    assert set(parsed.images) == {"faces/ada.jpg", "faces/ada-2.png"}


def test_import_package_reports_all_row_errors_in_one_preview() -> None:
    package = import_package(
        "external_id,name,email,image_1\n"
        "EMP-1,Ada Lovelace,not-an-email,faces/missing.jpg\n",
        {},
    )

    parsed = parse_user_import_archive(io.BytesIO(package))

    assert parsed.total_rows == 1
    assert {error.code for error in parsed.errors} == {"INVALID_EMAIL", "IMAGE_NOT_FOUND"}
    assert parsed.images == {}


def test_import_package_rejects_unsafe_archive_paths() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("people.csv", "external_id,name,image_1\nEMP-1,Ada,face.jpg\n")
        archive.writestr("../face.jpg", b"\xff\xd8\xffjpeg")

    with pytest.raises(UserImportPackageError) as exc_info:
        parse_user_import_archive(io.BytesIO(output.getvalue()))

    assert exc_info.value.code == "UNSAFE_ARCHIVE"


@pytest.mark.asyncio
async def test_import_preview_manual_replace_and_atomic_face_failure() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    org = Org(name="Import Test", slug=f"import-{uuid4().hex}", settings={})
    actor = User(
        org=org,
        name="Import Admin",
        email=f"admin-{uuid4().hex}@example.com",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    existing = User(
        org=org,
        name="Existing Person",
        external_id="EXIST-1",
        email=f"existing-{uuid4().hex}@example.com",
        role=UserRole.MEMBER.value,
        is_active=True,
    )
    package = import_package(
        "external_id,name,email,unit,image_1\n"
        "EXIST-1,Updated Person,updated@example.com,Operations,faces/existing.jpg\n"
        "NEW-1,New Person,new@example.com,Engineering,faces/new.png\n",
        {
            "faces/existing.jpg": b"\xff\xd8\xffexisting",
            "faces/new.png": b"\x89PNG\r\n\x1a\nnew",
        },
    )
    operations = OrganizationalUnit(
        org=org,
        name="Operations",
        kind="department",
        is_active=True,
    )
    engineering = OrganizationalUnit(
        org=org,
        name="Engineering",
        kind="department",
        is_active=True,
    )

    try:
        async with session_factory() as session:
            session.add_all([org, actor, existing, operations, engineering])
            await session.commit()

            app = FastAPI()
            app.include_router(users.router)

            async def override_db():  # type: ignore[no-untyped-def]
                yield session

            app.dependency_overrides[get_db] = override_db
            app.dependency_overrides[require_operator] = lambda: actor
            app.dependency_overrides[get_face_client] = lambda: FakeFaceClient()

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                preview_response = await client.post(
                    "/users/import/preview",
                    files={"package": ("people.zip", package, "application/zip")},
                )
                assert preview_response.status_code == 200
                preview = preview_response.json()
                assert preview["ready_count"] == 1
                assert preview["conflict_count"] == 1
                assert preview["errors"] == []
                assert preview["conflicts"][0]["row"] == 2
                assert preview["conflicts"][0]["allowed_actions"] == ["skip", "replace"]

                options = json.dumps(
                    {
                        "package_sha256": preview["package_sha256"],
                        "resolutions": [{"row": 2, "action": "replace"}],
                    }
                )
                app.dependency_overrides[get_face_client] = lambda: FakeFaceClient(fail_on_call=2)
                failed_response = await client.post(
                    "/users/import",
                    files={"package": ("people.zip", package, "application/zip")},
                    data={"options": options},
                )
                assert failed_response.status_code == 422
                assert failed_response.json()["detail"]["code"] == "LOW_QUALITY"

                people_after_failure = list(
                    (
                        await session.execute(
                            select(User).where(User.org_id == org.id).order_by(User.name)
                        )
                    )
                    .scalars()
                    .all()
                )
                assert [person.name for person in people_after_failure] == [
                    "Existing Person",
                    "Import Admin",
                ]
                assert (
                    await session.scalar(
                        select(func.count(FaceEmbedding.id))
                        .join(User, FaceEmbedding.user_id == User.id)
                        .where(User.org_id == org.id)
                    )
                    == 0
                )

                app.dependency_overrides[get_face_client] = lambda: FakeFaceClient()
                imported_response = await client.post(
                    "/users/import",
                    files={"package": ("people.zip", package, "application/zip")},
                    data={"options": options},
                )
                assert imported_response.status_code == 200
                assert imported_response.json() == {
                    "total_rows": 2,
                    "created_count": 1,
                    "replaced_count": 1,
                    "skipped_count": 0,
                    "embeddings_count": 2,
                }

            imported_people = list(
                (
                    await session.execute(
                        select(User).where(User.org_id == org.id).order_by(User.external_id)
                    )
                )
                .scalars()
                .all()
            )
            assert [(person.external_id, person.name) for person in imported_people] == [
                ("EXIST-1", "Updated Person"),
                ("NEW-1", "New Person"),
                (None, "Import Admin"),
            ]
            assert all(
                person.role == UserRole.MEMBER.value
                for person in imported_people
                if person.external_id is not None
            )
            assert (
                await session.scalar(
                    select(func.count(FaceEmbedding.id))
                    .join(User, FaceEmbedding.user_id == User.id)
                    .where(User.org_id == org.id)
                )
                == 2
            )
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(delete(Org).where(Org.id == org.id))
            await cleanup_session.commit()
        await engine.dispose()
