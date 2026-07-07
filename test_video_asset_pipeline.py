from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from video_generation.providers.serpapi_image_provider import SerpApiImageCandidate, SerpApiImageProvider
from video_generation.schemas import MedicineVideoInput
from video_generation.services.asset_resolver import StrictAssetResolver, _images_are_duplicate_like
from video_generation.services.assets.gallery import AssetCandidateRecord, CandidateEvaluation, CandidateGallery
from video_generation.services.assets.identity import build_medicine_identity, normalize_text
from video_generation.services.assets.ocr_verifier import verify_candidate_text
from video_generation.services.assets.query_builder import build_asset_queries
from video_generation.services.assets.scorer import source_category, score_candidate


def _medicine(name: str, salts: str = "", form: str = "") -> MedicineVideoInput:
    return MedicineVideoInput(
        medicine_name=name,
        active_salts=salts,
        dosage="1 unit",
        frequency="As prescribed",
        timing="As directed",
        form=form,
    )


def test_identity_normalizes_strength_and_form_aliases():
    identity = build_medicine_identity(_medicine("Dolo 650 Tab", "Paracetamol 650mg"))
    assert identity.normalized_brand_name == "dolo"
    assert "650 mg" in identity.strength
    assert identity.dosage_form == "tablet"
    assert "blister" in identity.aliases


def test_package_query_generation_uses_exact_identity_terms():
    identity = build_medicine_identity(_medicine("Aerocort Inhaler 200 MDI", "Levosalbutamol + Beclometasone", "inhaler"))
    queries = build_asset_queries(identity, "package")
    joined = "\n".join(queries).casefold()
    assert "aerocort" in joined
    assert "inhaler" in joined
    assert "box pack" in joined
    assert "site:1mg.com" in joined


def test_dosage_query_generation_is_separate_from_package_query():
    identity = build_medicine_identity(_medicine("Aerocort Inhaler 200 MDI", "Levosalbutamol + Beclometasone", "inhaler"))
    queries = build_asset_queries(identity, "dosage")
    joined = "\n".join(queries).casefold()
    assert "device canister" in joined
    assert "box pack" not in joined


def test_wrong_brand_candidate_is_rejected_before_download():
    resolver = StrictAssetResolver()
    medicine = _medicine("Aerotaz Inhaler", "Salbutamol", "inhaler")
    candidate = SerpApiImageCandidate(
        url="https://5.imimg.com/data5/aerocort-inhaler-200mdi.jpg",
        provider="serpapi_google_images",
        source_domain="indiamart.com",
        title="Aerocort Inhaler 200Mdi",
        page_url="https://www.indiamart.com/proddetail/aerocort-inhaler.html",
        source="IndiaMART",
    )
    assert "different medicine" in resolver._candidate_reject_reason(medicine, "package", candidate)


def test_metadata_ocr_scores_brand_and_strength():
    identity = build_medicine_identity(_medicine("Dolo 650 Tablet", "Paracetamol 650mg", "tablet"))
    result = verify_candidate_text(None, identity, "Buy Dolo 650 Tablet strip Paracetamol online", enable_ocr=False)
    assert result.brand_match
    assert result.strength_match
    assert result.score >= 0.6
    assert not result.complete


def test_review_required_sources_are_lower_confidence():
    trusted_score, trusted_review = source_category("1mg.com")
    review_score, review_review = source_category("indiamart.com")
    assert trusted_score > review_score
    assert not trusted_review
    assert review_review


def test_scoring_blocks_missing_brand_identity():
    identity = build_medicine_identity(_medicine("Aerotaz Inhaler", "Salbutamol", "inhaler"))
    ocr = verify_candidate_text(None, identity, "Aerocort inhaler device image", enable_ocr=False)
    score = score_candidate(identity, "dosage", "indiamart.com", "Aerotaz inhaler device", "Aerocort inhaler device image", ocr, None, 0.8)
    assert score.final_score == 0
    assert score.hard_reject_reason


def test_duplicate_image_detector_rejects_same_visual(tmp_path: Path):
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    Image.new("RGB", (400, 400), "#ffffff").save(first)
    Image.new("RGB", (400, 400), "#ffffff").save(second)
    assert _images_are_duplicate_like(first, second)


def test_candidate_gallery_persists_ranked_json(tmp_path: Path):
    gallery = CandidateGallery(tmp_path, "dolo_650_tablet", "package")
    record = AssetCandidateRecord(
        image_url="https://example.com/dolo.jpg",
        thumbnail_url="",
        source_page_url="https://example.com/dolo",
        source_domain="example.com",
        title="Dolo 650 Tablet",
        snippet="",
        query_used="Dolo 650 Tablet box pack",
        asset_slot="package",
        raw_rank=1,
        provider="mock",
    )
    gallery.add(CandidateEvaluation(candidate=record, score=0.9))
    gallery.mark_selected(record.image_url)
    path = gallery.save()
    payload = path.read_text(encoding="utf-8")
    assert "dolo_650_tablet_package" in payload
    assert '"selected": true' in payload


def test_serpapi_search_collects_multiple_query_candidates_without_network(monkeypatch):
    provider = SerpApiImageProvider(SimpleNamespace(serpapi_api_key="test"))

    def fake_search_query(query: str):
        return [
            SerpApiImageCandidate(
                url=f"https://example.com/{normalize_text(query).replace(' ', '-')}.jpg",
                provider="serpapi_google_images",
                source_domain="example.com",
                title=query,
                query_used=query,
                raw_rank=1,
            )
        ]

    monkeypatch.setattr(provider, "_search_query", fake_search_query)
    results = provider.search("Dolo 650 Tablet", "package", queries=["Dolo 650 box", "Dolo 650 pack"], max_candidates=10)
    assert len(results) == 2
    assert {item.query_used for item in results} == {"Dolo 650 box", "Dolo 650 pack"}
