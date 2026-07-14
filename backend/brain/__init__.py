"""HTM brain for the creature, built on htm.core (community fork of NuPIC).

htm.core is a C++ library built from source, so it may be absent in some
deployments (e.g. small cloud tiers). Everything degrades gracefully: when the
import fails, `available` is False and the app runs in no-brain mode.
"""

try:
    from .cortex import Cortex

    available = True
except Exception:  # ImportError or any binding load failure
    Cortex = None
    available = False


def build(world):
    if not available:
        return None
    try:
        return Cortex()
    except Exception:
        return None
