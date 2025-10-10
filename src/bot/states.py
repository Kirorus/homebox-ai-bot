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


class LocationStates(StatesGroup):
    """States for location management workflow"""
    viewing_locations = State()
    selecting_locations_for_marking = State()
    selecting_locations_for_description = State()
    confirming_description_update = State()
    
    # Creation flow
    creating_location_name = State()
    creating_location_description = State()
    creating_location_ai_hint = State()
    confirming_ai_description = State()
    selecting_parent_location = State()
    confirming_location_creation = State()