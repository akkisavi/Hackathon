"""Pure measurements and past-only features for OPERA categorical water rasters."""
from datetime import date
import numpy as np

VERSION = 'water-v1'
FEATURES = ['seasonal_residual', 'area_ratio', 'rate_30d', 'trailing_std_ratio']
VALID_CLASSES = [0, 1, 2]  # cloud=253, snow=252, missing=255 are excluded


def measure(array, pixel_area=900.0):
    valid = np.isin(array, VALID_CLASSES)
    return {'valid_fraction': float(valid.mean()),
            'open_water_km2': float(np.count_nonzero(array == 1) * pixel_area / 1e6),
            'partial_water_km2': float(np.count_nonzero(array == 2) * pixel_area / 1e6),
            'valid_pixels': int(valid.sum()), 'total_pixels': int(array.size)}


def seasonal_fit(rows):
    dates = [date.fromisoformat(r['date']) for r in rows]
    y = np.array([r['open_water_km2'] for r in rows])
    x = np.array([[1, np.sin(2*np.pi*d.timetuple().tm_yday/365.25),
                   np.cos(2*np.pi*d.timetuple().tm_yday/365.25)] for d in dates])
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ coef
    return {'coef': coef.tolist(), 'scale': max(float(np.median(np.abs(residual-np.median(residual)))*1.4826), float(np.median(y)*.02), .001),
            'median_area': max(float(np.median(y)), .001)}


def feature_rows(rows, baseline):
    """Input must be chronological; rolling values only use past/current observations."""
    result = []
    areas, dates = [], []
    for row in rows:
        d = date.fromisoformat(row['date'])
        a = row['open_water_km2']
        phase = 2*np.pi*d.timetuple().tm_yday/365.25
        expected = max(0., float(np.dot([1, np.sin(phase), np.cos(phase)], baseline['coef'])))
        recent = [v for t,v in zip(dates, areas) if 0 < (d-t).days <= 60]
        gap = (d-dates[-1]).days if dates else 0
        rate = (a-areas[-1])*30/gap/baseline['median_area'] if gap and gap <= 60 else 0.
        residual = (a-expected)/baseline['scale']
        features = [residual, a/baseline['median_area'], rate,
                    float(np.std(recent+[a]))/baseline['median_area']]
        result.append({**row, 'expected_km2': expected, 'baseline_deviation': residual,
                       'features': features, 'gap_days': gap})
        areas.append(a); dates.append(d)
    return result


def change_masks(before, after):
    valid = np.isin(before, VALID_CLASSES) & np.isin(after, VALID_CLASSES)
    return valid & (before != 1) & (after == 1), valid & (before == 1) & (after != 1), valid
