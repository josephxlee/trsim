"""ScenarioComposer validation wiring controller.

Hooks the Composer's :attr:`ScenarioComposer.validate_requested`
signal to a minimal pre-flight check and pushes the result into the
panel's validation block via :meth:`ScenarioComposer.set_validation`.

Real domain-level coherence checks (:mod:`workbench.domain.
coherence_validator`) require loaded :class:`Map` / :class:`Target`
instances - this MVP controller validates only the combobox shape
("user picked a Map, a Radar, and at least one target") so the
validation surface starts working end-to-end without dragging the
loader chain in. Domain wiring is a follow-up cycle.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from workbench.ui.editor.composer.widget import ScenarioComposer


class ScenarioComposerController(QObject):
    """Minimal validator + status push for the Composer Activity.

    Attributes:
        composer: The :class:`ScenarioComposer` widget this
            controller drives.
    """

    def __init__(
        self,
        *,
        composer: ScenarioComposer,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._composer = composer
        self._composer.validate_requested.connect(self.run_validation)

    @property
    def composer(self) -> ScenarioComposer:
        return self._composer

    def run_validation(self) -> tuple[str, tuple[str, ...]]:
        """Inspect the current Composer state + push status into the panel.

        Returns:
            ``(status, messages)`` — the same pair forwarded to
            :meth:`ScenarioComposer.set_validation`. Useful for tests
            and CLI surface.
        """
        map_id = self._composer.map_combo().currentText().strip()
        radar_id = self._composer.radar_combo().currentText().strip()
        targets_id = self._composer.targets_combo().currentText().strip()

        messages: list[str] = []
        if not map_id:
            messages.append("Map resource is not selected.")
        if not radar_id:
            messages.append("Radar resource is not selected.")
        if not targets_id:
            messages.append("No targets selected.")

        if messages:
            status = "ERROR" if (not map_id or not radar_id) else "WARN"
        else:
            status = "OK"
            messages.append(f"Map={map_id}, Radar={radar_id}, Targets={targets_id}")

        self._composer.set_validation(status, messages)
        return status, tuple(messages)
