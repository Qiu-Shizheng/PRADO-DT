"""PRADO-DT: prior-anchored residual adaptation for dose-time OOD transfer."""

from .core import (LinearRegressor, conformal_radius, condition_features,
                   feature_map, mse, pearson_rows)

__all__ = [
    "LinearRegressor", "conformal_radius", "condition_features",
    "feature_map", "mse", "pearson_rows",
]

try:
    from .torch_model import (PRADODTModel, InvariantResidualModel,
                              LowRankInteractionModel, MixtureResponseModel)
    __all__ += ["PRADODTModel", "InvariantResidualModel",
                "LowRankInteractionModel", "MixtureResponseModel"]
except ImportError:
    pass
