from pydantic import BaseModel


class Orientation(BaseModel):
    roll: float  # rad
    pitch: float  # rad
    yaw: float  # rad
