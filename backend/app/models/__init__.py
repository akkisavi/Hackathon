"""Import every model so `Base.metadata` is complete for create_all / Alembic."""
from app.models.classification import Classification
from app.models.detection import Detection
from app.models.flare_ref import FlareRef
from app.models.notified_alert import NotifiedAlert
from app.models.osm_infra import OsmInfra
from app.models.thermal_source import ThermalSource
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.password_reset import PasswordResetToken

__all__ = ["Detection", "ThermalSource", "OsmInfra", "Classification",
           "FlareRef", "User", "ApiKey", "PasswordResetToken", "NotifiedAlert"]
