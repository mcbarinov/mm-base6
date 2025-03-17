def get_registered_public_attributes(obj: object) -> list[str]:
    return [x for x in dir(obj) if not x.startswith("_")]
