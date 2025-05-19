from typing import cast

from mm_std import async_synchronized, http_request, utc_now

from mm_base6.core.dynamic_config import DynamicConfigStorage
from mm_base6.core.dynamic_value import DynamicValueStorage
from mm_base6.core.services.system import SystemService


class ProxyService:
    def __init__(self, system_service: SystemService) -> None:
        self.system_service = system_service

    def has_proxies_settings(self) -> bool:
        proxies_url = DynamicConfigStorage.storage.get("proxies_url")
        return (
            isinstance(proxies_url, str)
            and proxies_url.strip() != ""
            and "proxies" in DynamicValueStorage.storage
            and "proxies_updated_at" in DynamicValueStorage.storage
        )

    @async_synchronized
    async def update_proxies(self) -> int | None:
        proxies_url = cast(str, DynamicConfigStorage.storage.get("proxies_url"))
        res = await http_request(proxies_url)
        if res.is_err():
            await self.system_service.system_log("update_proxies", {"error": res.error})
            return -1
        proxies = (res.body or "").strip().splitlines()
        proxies = [p.strip() for p in proxies if p.strip()]
        await DynamicValueStorage.update_value("proxies", proxies)
        await DynamicValueStorage.update_value("proxies_updated_at", utc_now())
        return len(proxies)
