from pydantic import BaseModel

from .vector_3d import Vector3D
from .vector_4d import Vector4D  # quaternion (x, y, z, w)


class Pose3D(BaseModel):
    position: Vector3D = Vector3D()
    orientation: Vector4D = Vector4D()  # quaternion (x, y, z, w), unit quaternion
