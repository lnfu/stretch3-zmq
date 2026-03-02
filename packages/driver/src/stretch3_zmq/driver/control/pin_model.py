import numpy as np
import pinocchio as pin


class PinModel:
    def __init__(self) -> None:
        self.model = pin.buildModelFromUrdf("./data/ik_chain.urdf")
        self.data = self.model.createData()
        self.q = pin.neutral(self.model)

    def update_q(self, joint_position: dict[str, float]) -> None:
        for joint_name, position in joint_position.items():
            joint_id = self.model.getJointId(joint_name)
            q_idx = self.model.joints[joint_id].idx_q
            self.q[q_idx] = position

        pin.forwardKinematics(self.model, self.data, self.q)
        pin.updateFramePlacements(self.model, self.data)

    def get_transform(self, from_frame: str, to_frame: str) -> np.ndarray:
        """Returns 4x4 homogeneous transformation matrix from `from_frame` to `to_frame`."""
        if not self.model.existFrame(from_frame):
            raise ValueError(f"Frame '{from_frame}' not found!")
        if not self.model.existFrame(to_frame):
            raise ValueError(f"Frame '{to_frame}' not found!")
        from_id = self.model.getFrameId(from_frame)
        to_id = self.model.getFrameId(to_frame)
        T_world_from = self.data.oMf[from_id]
        T_world_to = self.data.oMf[to_id]
        return (T_world_from.inverse() * T_world_to).homogeneous

    def ik(
        self,
        target_pose: np.ndarray,
        ee_frame: str = "link_grasp_center",
        max_iter: int = 200,
        dt: float = 0.1,
        eps: float = 1e-4,
    ) -> np.ndarray | None:
        """
        Compute inverse kinematics for the given end-effector frame.

        Args:
            target_pose: 4x4 homogeneous transformation matrix (world frame).
            ee_frame: Name of the end-effector frame.
            max_iter: Maximum number of iterations.
            dt: Step size (damping factor).
            eps: Convergence threshold on the error norm.

        Returns:
            Joint configuration q if converged, else None.
        """
        if not self.model.existFrame(ee_frame):
            raise ValueError(f"Frame '{ee_frame}' not found!")

        target_se3 = pin.SE3(target_pose)
        frame_id = self.model.getFrameId(ee_frame)
        q = self.q.copy()

        for i in range(max_iter):
            pin.forwardKinematics(self.model, self.data, q)
            pin.updateFramePlacements(self.model, self.data)

            oMf = self.data.oMf[frame_id]
            err = pin.log6(oMf.actInv(target_se3)).vector

            if np.linalg.norm(err) < eps:
                print(f"IK converged in {i} iterations")
                self.q = q
                return q

            J = pin.computeFrameJacobian(self.model, self.data, q, frame_id, pin.LOCAL)

            damping = 1e-6
            JtJ = J.T @ J + damping * np.eye(self.model.nv)
            dq = np.linalg.solve(JtJ, J.T @ err)

            q = pin.integrate(self.model, q, dq * dt)
            q = np.clip(q, self.model.lowerPositionLimit, self.model.upperPositionLimit)

        print(f"IK did not converge after {max_iter} iterations, error: {np.linalg.norm(err):.6f}")
        return None
