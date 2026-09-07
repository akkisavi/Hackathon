"""Pure tag-parsing / classification logic for the OSM loader (no .pbf needed)."""
from app.ingestion.osm_loader import classify, parse_other_tags


def test_parse_other_tags():
    raw = '"landuse"=>"industrial","name"=>"MIDC Zone","operator"=>"MIDC"'
    assert parse_other_tags(raw) == {
        "landuse": "industrial", "name": "MIDC Zone", "operator": "MIDC",
    }
    assert parse_other_tags(None) == {}
    assert parse_other_tags("") == {}


def test_classify():
    assert classify({"landuse": "industrial"}) == "industrial"
    assert classify({"landuse": "quarry"}) == "quarry"
    assert classify({"power": "plant"}) == "power_plant"
    assert classify({"man_made": "works"}) == "works"
    # priority: landuse wins over a co-present power tag
    assert classify({"landuse": "industrial", "power": "plant"}) == "industrial"
    # irrelevant tags -> skip
    assert classify({"building": "yes"}) is None
    assert classify({}) is None
