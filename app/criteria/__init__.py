import sys, inspect

from .criterions import *
from .utils import check_criterions, create_criterion
from .preconfigured_criterions import add_preconfigured_criterions_to_db



CRITERIONS = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))
