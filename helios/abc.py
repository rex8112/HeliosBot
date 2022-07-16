from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tools.settings import Settings


class HasFlags:
    _allowed_flags: list
    flags: list

    def set_flag(self, flag: str, on: bool):
        if flag not in self._allowed_flags:
            raise KeyError(f'{flag} not in {type(self)} allowed flags: {self._allowed_flags}')
        if flag in self.flags and on is False:
            self.flags.remove(flag)
        elif flag not in self.flags and on is True:
            self.flags.append(flag)

    def get_flag(self, flag: str):
        return flag in self.flags


class HasSettings:
    _default_settings: dict
    settings: 'Settings'
