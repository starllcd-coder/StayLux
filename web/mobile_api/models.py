"""
Ensure Django discovers models defined in subpackages of the `mobile_api` app.
This module imports subpackage model modules so the app registry picks them up.
"""
from .auth import models as auth_models  # noqa: F401 (imports mobile_api.auth.models)
from .bookings import models as bookings_models  # noqa: F401 (imports mobile_api.bookings.models)
from .chat import models as chat_models  # noqa: F401
from .concierge import models as concierge_models  # noqa: F401
from .discovery import models as discovery_models  # noqa: F401
from .growth import models as growth_models  # noqa: F401
from .notifications import models as notifications_models  # noqa: F401
from .profile import models as profile_models  # noqa: F401
from .reviews import models as reviews_models  # noqa: F401
from .wishlist import models as wishlist_models  # noqa: F401
