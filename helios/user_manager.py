from .helios_user import HeliosUser
from .tools import utc_now


class UserManager:
    def __init__(self):
        self.users = {}
        self.last_interaction = {}

    def get(self, _id: int):
        user = self.users.get(_id)
        if user is None:
            return None
        self.last_interaction[_id] = utc_now()
        return user

    def add(self, user: HeliosUser):
        if user.id in self.users:
            raise KeyError("User already exists")
        self.users[user.id] = user
        self.last_interaction[user.id] = utc_now()

    def remove(self, _id: int):
        self.users.pop(_id)
        self.last_interaction.pop(_id)