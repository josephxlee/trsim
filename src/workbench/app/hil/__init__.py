"""HIL integration package — **placeholder for Phase 8 (post-MVP)**.

The MVP scope explicitly excludes Hardware-in-the-Loop. Phase 8
introduces the full HIL stack:

- ``hil_evaluator.py`` — L5 (Track) / L4 (Paired Detection) / L2
  (Spectrum) / L1 (Raw IQ) 3-way comparison (Simulator vs DUT vs
  GT). plan/18 § 18.5.
- ``time_synchronizer.py`` — sim-time mode + real-time + Lock-step
  Handshake (v0.39). plan/18 § 18.16.4.
- ``dut_session_manager.py`` — adapter lifecycle (handshake / heartbeat /
  reconnect). plan/18 § 18.6.
- ``plugins_builtin/tcp_json_dut_adapter.py`` — reference adapter.

The empty package + matching :mod:`workbench.domain.hil` +
:mod:`workbench.ui.simulator.hil_panel` reserve the directory layout
so the post-MVP cycle can drop modules in without re-shuffling the
namespace. plan/04 § 4.3 Phase 8 lists 14 ✗ rows; see
``docs/MVP_STATUS.md`` § "Post-MVP — Phase 8 HIL" for the current
progress matrix.
"""
