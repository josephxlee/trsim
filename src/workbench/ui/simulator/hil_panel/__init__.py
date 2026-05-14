"""HIL panel — **placeholder for Phase 8 (post-MVP)**.

Phase 8 lands the UI surface:

- ``comparison_view.py`` — 3-way Track plot (Simulator vs DUT vs GT).
- ``stage_compare_view.py`` — L2/L4 layer comparison views (Phase 8.2).
- ``dut_status_view.py`` — adapter handshake / heartbeat / lock-step
  readout.

The empty package reserves the directory so post-MVP cycles can drop
new panel modules in without touching the parent
:mod:`workbench.ui.simulator` namespace. The Phase 4 sweep deliberately
leaves the HIL bottom-tab unmounted — the L1-L6 wiring covers only
the eight production Simulator panels. See ``docs/MVP_STATUS.md``
§ "Post-MVP — Phase 8 HIL".
"""
