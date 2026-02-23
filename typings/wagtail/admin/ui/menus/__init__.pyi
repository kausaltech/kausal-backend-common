from django.contrib.auth.models import AbstractBaseUser
from django_stubs_ext import StrOrPromise

class MenuItem:
    label: StrOrPromise
    url: str
    icon_name: str
    priority: int

    def __init__(self, label: StrOrPromise, url: str, icon_name: str = "", priority: int = 1000) -> None: ...
    def is_shown(self, user: AbstractBaseUser) -> bool: ...

    def __lt__(self, other: MenuItem) -> bool: ...
