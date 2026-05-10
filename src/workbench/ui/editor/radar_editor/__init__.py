"""Radar Editor widget (Phase 4.7, plan/05 § 5.3.9 + plan/13 § 13.5).

Editor Activity 3 - one unified form whose Antenna block reshapes
itself based on the Antenna Type dropdown (Parabolic vs Planar Array).
RX Channels block toggles between Single SUM and Monopulse 4-channel
(Sigma / Delta-az / Delta-el / Delta-square).

Phase 4.7 ships the widget shell: dropdowns, dynamic form swap, RX
mode radios, computed-value labels, and a Beam Pattern Preview
placeholder. Phase 5+ wires real beam-pattern computation + Antenna
preset library.
"""

from __future__ import annotations

from workbench.ui.editor.radar_editor.widget import (
    AntennaType,
    RadarEditor,
    RXChannelMode,
)

__all__ = ["AntennaType", "RXChannelMode", "RadarEditor"]
