from enum import Enum


class ViolationTypes(Enum):
    Shop = 1


class ViolationStates(Enum):
    New = 0
    Due = 1
    Illegal = 2
    Paid = 3
