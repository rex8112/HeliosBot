from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    pass

HeliosChannel = Union['Channel', 'TopicChannel', 'VoiceChannel']
