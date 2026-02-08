from pydantic import BaseModel


class Vector3D(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
