from pydantic import BaseModel


class Twist2D(BaseModel):
    """Differential drive twist"""

    linear: float = 0.0  # m/s
    angular: float = 0.0  # rad/s
