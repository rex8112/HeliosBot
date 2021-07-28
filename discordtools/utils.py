from typing import List, Union

import discord


def mention_string(seq: List[Union[discord.Member, discord.User]], seperator: str = '\n') -> str:
    """Converts a list of users/members into a string of their mentions."""
    return seperator.join(x.mention for x in seq)
