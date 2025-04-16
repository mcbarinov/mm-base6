from app.core.db import Db
from app.settings import DynamicConfigs, DynamicValues
from mm_base6 import BaseService, BaseServiceParams

AppService = BaseService[DynamicConfigs, DynamicValues, Db]
AppServiceParams = BaseServiceParams[DynamicConfigs, DynamicValues, Db]
