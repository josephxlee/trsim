"""TargetsEditor Validate-button wiring controller.

Mirrors :class:`ScenarioComposerController` for the Targets Activity:
the Validate button emits ``validate_requested`` and this controller
runs a shape check on the metadata block (name / motion kind / RCS /
scatterer count) then pushes the result into the validation block.

Real domain-level checks (waypoint coherence, motion-model validity
against the scenario environment) need an actual ScenarioService +
loaded Target dataclass — that wiring is a follow-up cycle. This MVP
keeps the Validate surface live so users see immediate feedback when
they save a half-typed form.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from workbench.ui.editor.targets_editor.widget import MOTION_KINDS, TargetsEditor


class TargetsEditorController(QObject):
    """Validate handler for :class:`TargetsEditor`."""

    def __init__(
        self,
        *,
        editor: TargetsEditor,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._editor.validate_requested.connect(self.run_validation)

    @property
    def editor(self) -> TargetsEditor:
        return self._editor

    def run_validation(self) -> tuple[str, tuple[str, ...]]:
        """Shape-check the four metadata fields + push status.

        Returns:
            ``(status, messages)``. ``status`` is one of
            ``"OK"`` / ``"WARN"`` / ``"ERROR"``. The first message is
            also pushed via :meth:`TargetsEditor.set_validation_status`
            (joined with ``"; "`` when multiple messages exist).
        """
        name = self._editor.name_edit().text().strip()
        motion = self._editor.motion_combo().currentText().strip()
        rcs_raw = self._editor.rcs_edit().text().strip()
        scatterer_raw = self._editor.scatterers_edit().text().strip()

        messages: list[str] = []
        rcs_value: float | None = None
        scatterer_value: int | None = None

        if not name or name == "(unnamed)":
            messages.append("Target name is empty or default '(unnamed)'.")

        if motion not in MOTION_KINDS:
            messages.append(f"Unknown motion kind {motion!r}.")

        try:
            rcs_value = float(rcs_raw)
            if rcs_value <= 0.0:
                messages.append(f"RCS must be > 0 (got {rcs_value}).")
        except ValueError:
            messages.append(f"RCS '{rcs_raw}' is not a float.")

        try:
            scatterer_value = int(scatterer_raw)
            if scatterer_value < 1:
                messages.append(f"Scatterer count must be >= 1 (got {scatterer_value}).")
        except ValueError:
            messages.append(f"Scatterer count '{scatterer_raw}' is not an int.")

        if not messages:
            status = "OK"
            summary = (
                f"name={name}, motion={motion}, "
                f"RCS={rcs_value} m^2, scatterers={scatterer_value}"
            )
            messages.append(summary)
        else:
            # Numeric parse failures + missing fields are errors; bare
            # default-name warnings are demoted to WARN.
            hard_keys = ("RCS", "Scatterer", "motion kind")
            has_hard_error = any(any(k in m for k in hard_keys) for m in messages)
            status = "ERROR" if has_hard_error else "WARN"

        self._editor.set_validation_status(f"{status} - {'; '.join(messages)}")
        return status, tuple(messages)
