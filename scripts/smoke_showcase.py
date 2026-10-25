"""HTTP checks against the built container; Python standard library only."""
import json
import sys
from urllib.request import urlopen
from urllib.error import HTTPError

base = sys.argv[1].rstrip("/")
def fetch(path):
    with urlopen(base + path, timeout=30) as response:
        return response.read()

assert json.loads(fetch("/health"))["showcase"]
for page in ("/orbit", "/orbit/water", "/orbit/thermal"):
    assert b"<html" in fetch(page)
for site in json.loads(fetch("/api/v1/water/sites")):
    prefix = "/api/v1/water/sites/" + site["id"]
    rows = json.loads(fetch(prefix + "/observations"))["observations"]
    date = rows[-1]["date"]
    assessment = json.loads(fetch(prefix + "/assessment?date=" + date))
    assert assessment["model_status"] == "experimental" and assessment["forecast"] is None
    assert fetch(prefix + "/image?date=" + date).startswith(bytes([137,80,78,71]))
assert json.loads(fetch("/api/v1/change/thermal"))["features"]
assert json.loads(fetch("/api/v1/change/fixtures"))
try:
    fetch("/api/v1/missing")
except HTTPError as error:
    assert error.code == 404
else:
    raise AssertionError("Unknown API route must return 404")
print("Showcase HTTP checks passed for all three sites and page routes")
