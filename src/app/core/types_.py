from app.core.db import Db
from app.settings import DConfigSettings, DValueSettings
from mm_base6 import BaseService, BaseServiceParams

AppService = BaseService[DConfigSettings, DValueSettings, Db]
AppServiceParams = BaseServiceParams[DConfigSettings, DValueSettings, Db]
