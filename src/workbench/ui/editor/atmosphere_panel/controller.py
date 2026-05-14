"""AtmospherePanel state propagator (Phase 9 cycle).

Listens to :attr:`AtmospherePanel.state_changed` and forwards a short
human-readable summary to :meth:`ScenarioComposer.set_atmosphere_hint`
so the Composer's Composition block always reflects whatever the user
is currently editing in the Atmosphere Activity.

The propagator is a one-way data feed: it does not alter the
Composer's atmosphere combo (which still picks one of the four named
presets ``Clear / Light Rain / Heavy Rain / Fog``). The combo + hint
together give the user both a coarse preset choice + the live state
of the detailed editor.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from workbench.ui.editor.atmosphere_panel.widget import AtmospherePanel, AtmosphereState
from workbench.ui.editor.composer.widget import ScenarioComposer


def format_atmosphere_hint(state: AtmosphereState) -> str:
    """Render an :class:`AtmosphereState` as a compact hint string.

    Example output: ``"editor: Clear, vis=20.0 km, rain=0.0 mm/h"``.
    """
    return (
        f"editor: {state.sky_condition}, "
        f"vis={state.visibility_km:.1f} km, "
        f"rain={state.rain_rate_mm_per_h:.1f} mm/h"
    )


class AtmospherePropagator(QObject):
    """Forward AtmospherePanel.state_changed into ScenarioComposer."""

    def __init__(
        self,
        *,
        panel: AtmospherePanel,
        composer: ScenarioComposer,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = panel
        self._composer = composer
        self._panel.state_changed.connect(self._on_state_changed)
        # Paint once on construction so the Composer hint starts from
        # the panel's current values rather than the static placeholder.
        try:
            initial = panel.current_state()
        except ValueError:
            initial = None
        if initial is not None:
            self._composer.set_atmosphere_hint(format_atmosphere_hint(initial))

    @property
    def panel(self) -> AtmospherePanel:
        return self._panel

    @property
    def composer(self) -> ScenarioComposer:
        return self._composer

    def _on_state_changed(self, state: AtmosphereState) -> None:
        self._composer.set_atmosphere_hint(format_atmosphere_hint(state))
