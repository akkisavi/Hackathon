from io import StringIO

import pandas as pd

from app.ingestion.firms_client import CANONICAL_COLUMNS, normalize_firms_df

# a real-shaped VIIRS_SNPP_NRT Area API response
_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
27.95755,96.95478,334.77,0.44,0.39,2026-09-05,44,N,VIIRS,n,2.0NRT,285.13,5.26,D
6.17996,81.00569,341.03,0.40,0.36,2026-09-05,1330,1,VIIRS,h,2.0NRT,302.13,2.48,N
9.99999,80.00000,,0.4,0.4,2026-09-05,120,N,VIIRS,l,2.0NRT,300.0,,D
"""


def test_normalize_shapes_and_parses():
    df = normalize_firms_df(pd.read_csv(StringIO(_CSV)))

    # row 3 dropped: no brightness
    assert len(df) == 2
    assert list(df.columns) == CANONICAL_COLUMNS

    first = df.iloc[0]
    assert first["daynight"] == "D"
    assert first["acquired_at"] == pd.Timestamp("2026-09-05 00:44", tz="UTC")
    assert first["brightness"] == 334.77
    assert first["frp"] == 5.26

    # "1330" -> 13:30 UTC
    assert df.iloc[1]["acquired_at"] == pd.Timestamp("2026-09-05 13:30", tz="UTC")


def test_normalize_empty():
    out = normalize_firms_df(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == CANONICAL_COLUMNS
