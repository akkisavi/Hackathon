# Classifier validation - SIH26162

- Thermal sources classified: **4,984**
- Labelable against reference data (EOG flare catalogue + OSM registry): **96** (2%)
- Accuracy on the labelable subset: **93.8%**

Reference labels are derived from proximity to independent authoritative
datasets, not hand annotation; classes without a reliable reference signal
(brick_kiln, wildfire, industrial_fire) are excluded from the matrix.

## Confusion matrix (rows = reference, cols = predicted)

| ref \ pred | agricultural_burning | gas_flare | mining | steel_smelter |
|---|---|---|---|---|
| **agricultural_burning** | 22 | 0 | 0 | 0 |
| **gas_flare** | 0 | 38 | 0 | 1 |
| **mining** | 0 | 0 | 21 | 1 |
| **steel_smelter** | 0 | 1 | 0 | 9 |

## Per-class precision / recall

```
                      precision    recall  f1-score   support

agricultural_burning       1.00      1.00      1.00        22
           gas_flare       0.97      0.97      0.97        39
              mining       1.00      0.88      0.93        24
       steel_smelter       0.82      0.82      0.82        11

           micro avg       0.97      0.94      0.95        96
           macro avg       0.95      0.92      0.93        96
        weighted avg       0.97      0.94      0.95        96

```