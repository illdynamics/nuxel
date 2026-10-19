# Power regressions

The A34 button FSM keeps Power isolated from deferred Bixby actions, translates
touch only at SYN_REPORT, and uses framebuffer powerdown/unblank. Deterministic
FSM tests pass. Physical short/long/double Power behavior remains owner-tested
only; recovery and Download Mode actions were not executed.
