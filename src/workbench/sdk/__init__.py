"""TRsim SDK — Public API for DLC authors (plan/17 § 17.4, plan/02 § 2.6b)."""

from workbench.sdk.package_builder import build_package
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
from workbench.sdk.test_harness import PackageTestResult, test_package

__all__ = [
    "AngleEstimatorProtocol",
    "ClassifierProtocol",
    "DUTAdapterProtocol",
    "DataAssociatorProtocol",
    "DetectorProtocol",
    "PackageTestResult",
    "PairingProtocol",
    "PhysicsModelProtocol",
    "PredictorProtocol",
    "ResourceProtocol",
    "TrackerProtocol",
    "UIPanelProtocol",
    "build_package",
    "test_package",
]
