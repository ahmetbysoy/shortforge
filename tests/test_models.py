"""Script/VideoJob dogrulama ve durum gecisi kurallari."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shortforge.models import JobStatus, Scene, Script, VideoJob


def make_scene(index: int = 1) -> Scene:
    return Scene(index=index, narration="Roma'da bir gun.", image_prompt="ancient rome, cinematic")


def make_script(**overrides: object) -> Script:
    payload: dict[str, object] = {
        "topic": "Antik Roma",
        "hook": "Roma'da bir gun 24 saat degildi.",
        "scenes": [make_scene(i) for i in (1, 2, 3)],
        "hashtags": ["tarih", "bilgi", "shorts"],
        "sources": ["https://example.org/roma"],
    }
    payload.update(overrides)
    return Script(**payload)  # type: ignore[arg-type]


def test_valid_script_normalizes_hashtags() -> None:
    script = make_script()
    assert script.hashtags == ["#tarih", "#bilgi", "#shorts"]
    assert script.warnings == []
    assert script.estimated_duration_s > 0


def test_scene_count_bounds() -> None:
    with pytest.raises(ValidationError):
        make_script(scenes=[make_scene(i) for i in (1, 2)])
    with pytest.raises(ValidationError):
        make_script(scenes=[make_scene(i) for i in range(1, 9)])


def test_hook_length_limit() -> None:
    with pytest.raises(ValidationError):
        make_script(hook="x" * 91)


def test_hashtag_bounds() -> None:
    with pytest.raises(ValidationError):
        make_script(hashtags=["tek", "iki"])
    with pytest.raises(ValidationError):
        make_script(hashtags=["a", "b", "c", "d", "e", "f"])


def test_missing_sources_produces_warning_not_error() -> None:
    script = make_script(sources=[])
    assert any("sources bos" in warning for warning in script.warnings)


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        make_script(bilinmeyen="x")


def test_job_defaults_to_private_and_enforces_flow() -> None:
    job = VideoJob(script=make_script())
    assert job.privacy == "private"
    assert job.status is JobStatus.DRAFT

    job.mark(JobStatus.RENDERED)
    job.mark(JobStatus.UPLOADED)
    job.mark(JobStatus.APPROVED)
    job.mark(JobStatus.PUBLISHED)
    with pytest.raises(ValueError):
        job.mark(JobStatus.DRAFT)


def test_cannot_publish_without_approval() -> None:
    job = VideoJob(script=make_script()).mark(JobStatus.RENDERED).mark(JobStatus.UPLOADED)
    with pytest.raises(ValueError, match="gecersiz durum gecisi"):
        job.mark(JobStatus.PUBLISHED)
