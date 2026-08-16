"""The fourteen mechanism-family engines.

One module per family, ``mf01_*`` through ``mf14_*``.  Each registers exactly one
:class:`~engines.base.Engine` subclass, and between them they carry all 815 units
in the catalogue.  Nothing in this package knows about an individual agent.
"""

from engines.base import Engine, Profile, all_engines, get_engine, load_engines, register

__all__ = ["Engine", "Profile", "all_engines", "get_engine", "load_engines", "register"]
