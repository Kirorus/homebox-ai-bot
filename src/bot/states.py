"""
Bot state definitions
"""

from aiogram.fsm.state import State, StatesGroup


class ItemStates(StatesGroup):
    """States for item processing workflow"""
    waiting_for_photo = State()
    confirming_data = State()
    editing_name = State()
    editing_description = State()
    selecting_location = State()
    waiting_for_reanalysis_hint = State()
