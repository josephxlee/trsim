"""HIL DUT messages + 3-way comparison data model — **placeholder for
Phase 8 (post-MVP)**.

Phase 8 lands the data model:

- ``dut_messages.py`` — :class:`DUTTrack` (L5), :class:`DUTPairedDetection`
  (L4), :class:`DUTSpectrum` (L2), :class:`DUTRawIQ` (L1). plan/18 § 18.5.
- ``tx_signal.py`` — :class:`TXSignalDigital`, :class:`TXSignalAnalog`.
- ``comparison.py`` — :class:`HILComparisonResult` 3-way bundle.

The empty package reserves the layout so post-MVP work can add files
without breaking the import surface for any consumer that wants to
``from workbench.domain.hil import ...`` later. Stays empty until
Phase 8 starts. See ``docs/MVP_STATUS.md`` § "Post-MVP — Phase 8 HIL".
"""
