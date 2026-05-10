"""Scenario Composer widget (Phase 4.5, plan/13 section 13.3).

Editor Activity 1 - the **main** Editor activity. Lets the user pick
a Map + Radar + Targets, set the Installation position + azimuth,
choose Composition options (sea state, atmosphere), and validate the
coherence of the resulting scenario.

Phase 4.5 ships the four-block shell + Save / Save As / Validate /
Export Bundle action row. References / Installation / Composition
fields are placeholder QComboBox / QLineEdit widgets fed by stub data
- Phase 5+ wires them to the real ResourceLibrary + ScenarioService.
The Validation block displays a static "no messages" hint until a
real Coherence Validator is connected.
"""

from __future__ import annotations

from workbench.ui.editor.composer.widget import ScenarioComposer

__all__ = ["ScenarioComposer"]
