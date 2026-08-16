"""ADW -- the agent runtime for the master catalogue.

815 automation units, 14 engines, 60 verticals, 10 archetypes.  The catalogue is
data; the engines are the only code that runs; a customer's roster is resolved
from their vertical, archetype and country pack.
"""

from adw.models import (
    BusinessProfile,
    CountryPack,
    RunContext,
    Unit,
    UnitType,
)

__version__ = "2.0.0"

__all__ = [
    "BusinessProfile",
    "CountryPack",
    "RunContext",
    "Unit",
    "UnitType",
    "__version__",
]
