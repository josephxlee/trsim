"""MapEditor validation controller.

Mirrors :class:`ScenarioComposerController` / :class:`TargetsEditor
Controller`: a small QObject that listens to
:attr:`MapEditor.validate_requested` and pushes a coherent
status string into the panel's :meth:`MapEditor.set_validation_status`
hook.

Validation rules (MVP shape check; full Map coherence_validator runs
in a follow-up cycle):

- Origin label must contain real lat/lon text (default is
  ``"Origin: (unset)  Vertical: (unset)"``).
- DomainSettingsPanel must produce a valid SimulationDomain
  (the panel itself rejects degenerate bounds; we just surface
  ``__post_init__`` errors instead of crashing).
- Domain width + height must be > 0 (sanity).

Domain edits + outside-environment edits also trigger the status
to fall back to ``"not yet validated"`` so the user is not misled by a
stale OK after they change inputs.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain
from workbench.ui.editor.map_editor.widget import MapEditor

_ORIGIN_UNSET_MARKER: str = "(unset)"


class MapEditorController(QObject):
    """Validate button handler + auto-stale on domain edits."""

    def __init__(
        self,
        *,
        editor: MapEditor,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor
        self._editor.validate_requested.connect(self.run_validation)
        self._editor.domain_changed.connect(self._on_domain_changed)
        self._editor.outside_environment_changed.connect(self._on_outside_environment_changed)

    @property
    def editor(self) -> MapEditor:
        return self._editor

    def run_validation(self) -> tuple[str, tuple[str, ...]]:
        """Inspect MapEditor state + push status into the panel.

        Returns:
            ``(status, messages)``. ``status`` is one of
            ``"OK"`` / ``"WARN"`` / ``"ERROR"``.
        """
        messages: list[str] = []

        origin_text = self._editor.origin_label().text()
        if _ORIGIN_UNSET_MARKER in origin_text:
            messages.append("Origin is not set.")

        try:
            domain: SimulationDomain | None = self._editor.domain_panel().current_domain()
        except (ValueError, TypeError) as exc:
            messages.append(f"Domain settings are invalid: {exc}")
            domain = None

        if domain is not None:
            if domain.width_m <= 0.0:
                messages.append(f"Domain width must be > 0 (got {domain.width_m}).")
            if domain.height_m <= 0.0:
                messages.append(f"Domain height must be > 0 (got {domain.height_m}).")

        if not messages:
            outside = self._editor.domain_panel().current_outside_environment()
            assert domain is not None  # populated above when no error messages
            status = "OK"
            summary = (
                f"origin set, "
                f"domain {domain.width_m:.0f}x{domain.height_m:.0f} m, "
                f"outside={outside.value}"
            )
            messages.append(summary)
        else:
            hard_keys = ("Domain", "invalid")
            has_hard_error = any(any(k in m for k in hard_keys) for m in messages)
            status = "ERROR" if has_hard_error else "WARN"

        self._editor.set_validation_status(f"{status} - {'; '.join(messages)}")
        return status, tuple(messages)

    def _on_domain_changed(self, _domain: SimulationDomain) -> None:
        # Don't auto-validate (validation has its own button); just
        # demote the status so a stale "OK" doesn't mislead the user
        # after they tweak the domain bounds.
        self._editor.set_validation_status("Status: not yet validated")

    def _on_outside_environment_changed(self, _outside: OutsideEnvironment) -> None:
        self._editor.set_validation_status("Status: not yet validated")
