import sys, inspect

from .criterions import *
from .utils import check_criterions


CRITERIONS = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
