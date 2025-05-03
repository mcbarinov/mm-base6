from mm_base6 import BaseService, BaseServiceParams

from app.core.db import Db
from app.settings import DynamicConfigs, DynamicValues

AppService = BaseService[DynamicConfigs, DynamicValues, Db]
AppServiceParams = BaseServiceParams[DynamicConfigs, DynamicValues, Db]
