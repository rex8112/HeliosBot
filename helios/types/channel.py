from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..channel import Channel, TopicChannel

HeliosChannel = Union['Channel', 'TopicChannel']
