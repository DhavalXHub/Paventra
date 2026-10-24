"""Import all models so SQLAlchemy registers them with Base.metadata."""
from app.models.user import User, UserRole  # noqa: F401
from app.models.team import RepairTeam  # noqa: F401
from app.models.report import (  # noqa: F401
    Report, MediaAsset, ReportStatusHistory, RepairAssignment,
    FuzzyPriorityAssessment, DuplicateLink,
    ReportStatus, ReportSource, LocationSource, DamageType, SeverityLevel,
)
from app.models.inspection import InspectionJob, InspectionFrame, InspectionStatus  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.audit import AuditEvent  # noqa: F401

# Convenience alias used by init_db
all_models = [User, RepairTeam, Report, MediaAsset, ReportStatusHistory,
              RepairAssignment, FuzzyPriorityAssessment, DuplicateLink,
              InspectionJob, InspectionFrame, Notification, AuditEvent]
