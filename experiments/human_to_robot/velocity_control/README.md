# Velocity-parameterized commands

The paper uses motion labels `up`, `down`, `left`, `stretch`, and `pack`, together with a requested velocity. MoveIt trajectory timing/joint velocities are scaled to that request; a new command cancels the current motion and replans from the interrupted configuration.

The reported command intervals are 0.5, 1.0, and 1.5 s. Evaluate the realized end-effector trajectory against its reference, keeping other settings constant. This is not simply changing the interval of the position-mode packet sender: payload semantics and robot-side cancellation/replanning must also match.

The complete velocity-mode generator, MoveIt controller, reference trajectory files, and plotting implementation are not yet included. This directory records the experiment protocol rather than claiming a runnable velocity-mode reproduction. See [human-to-robot guide](../../../docs/HUMAN_TO_ROBOT.md).
