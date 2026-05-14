"""TRsim SDK — Public API for DLC authors (plan/17 § 17.4, plan/02 § 2.6b)."""

from workbench.sdk.manifest import (
    CompatibilitySpec,
    PackageManifest,
    PackageMeta,
    PythonDeps,
    load_manifest_from_toml,
)
from workbench.sdk.package_builder import build_package
from workbench.sdk.package_validator import (
    KNOWN_ENTRY_POINT_SLOTS,
    validate_entry_point_slots,
)
from workbench.sdk.protocols import (
    AngleEstimatorProtocol,
    ClassifierProtocol,
    DataAssociatorProtocol,
    DetectorProtocol,
    DUTAdapterProtocol,
    PairingProtocol,
    PhysicsModelProtocol,
    PredictorProtocol,
    ResourceProtocol,
    TrackerProtocol,
    UIPanelProtocol,
)
from workbench.sdk.resource_schemas import (
    ResourceCategory,
    known_resource_categories,
    validate_resource_toml_blob,
)
from workbench.sdk.test_harness import PackageTestResult, test_package

__all__ = [
    "KNOWN_ENTRY_POINT_SLOTS",
    "AngleEstimatorProtocol",
    "ClassifierProtocol",
    "CompatibilitySpec",
    "DUTAdapterProtocol",
    "DataAssociatorProtocol",
    "DetectorProtocol",
    "PackageManifest",
    "PackageMeta",
    "PackageTestResult",
    "PairingProtocol",
    "PhysicsModelProtocol",
    "PredictorProtocol",
    "PythonDeps",
    "ResourceCategory",
    "ResourceProtocol",
    "TrackerProtocol",
    "UIPanelProtocol",
    "build_package",
    "known_resource_categories",
    "load_manifest_from_toml",
    "test_package",
    "validate_entry_point_slots",
    "validate_resource_toml_blob",
]
