from pydantic import BaseModel


class Pose2D(BaseModel):
    x: float = 0.0  # m
    y: float = 0.0  # m
    theta: float = 0.0  # rad
