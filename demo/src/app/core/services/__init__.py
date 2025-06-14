from .data import DataService
from .misc import MiscService


class ServiceRegistry:
    data: DataService
    misc: MiscService
