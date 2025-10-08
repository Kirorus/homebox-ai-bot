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


class SearchStates(StatesGroup):
    """States for search workflow"""
    waiting_for_search_query = State()
    viewing_search_results = State()
    viewing_item_details = State()
    selecting_new_location = State()
    editing_item_name = State()
    editing_item_description = State()
    waiting_for_reanalysis_hint = State()
