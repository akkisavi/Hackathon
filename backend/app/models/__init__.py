"""Import every model so `Base.metadata` is complete for create_all / Alembic."""
from app.models.classification import Classification
from app.models.detection import Detection
from app.models.flare_ref import FlareRef
from app.models.osm_infra import OsmInfra
from app.models.thermal_source import ThermalSource

__all__ = ["Detection", "ThermalSource", "OsmInfra", "Classification", "FlareRef"]
