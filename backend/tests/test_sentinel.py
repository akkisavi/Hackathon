from app.ingestion.sentinel import classify_dnbr


def test_dnbr_thresholds():
    assert classify_dnbr(0.55) == "confirmed"   # high burn
    assert classify_dnbr(0.30) == "confirmed"   # moderate
    assert classify_dnbr(0.15) == "low"
    assert classify_dnbr(0.02) == "none"
    assert classify_dnbr(-0.1) == "none"        # regrowth / no burn
