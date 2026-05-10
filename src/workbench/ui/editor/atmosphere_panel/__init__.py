"""Atmosphere Panel widget (Phase 4.8, plan/15 § 15.4.3 + plan/05).

Editor-side panel that lets the user pick the atmospheric envelope
applied to the current scenario - sky condition, visibility, rain
rate, and the standard ISA inputs (temperature / pressure). It is
referenced from the Scenario Composer's Composition block; this
module owns the form widget itself.

Phase 4.8 ships the form shell. Phase 5+ wires the values to
domain.atmosphere via ScenarioService.
"""

from __future__ import annotations

from workbench.ui.editor.atmosphere_panel.widget import (
    SKY_CONDITIONS,
    AtmospherePanel,
)

__all__ = ["SKY_CONDITIONS", "AtmospherePanel"]
