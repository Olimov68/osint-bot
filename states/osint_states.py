from aiogram.fsm.state import State, StatesGroup

class OSINTStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_email = State()
    waiting_for_dork = State()
    waiting_for_dork_name = waiting_for_dork
    waiting_for_domain = State()
    waiting_for_image = State()
