from aiogram.fsm.state import StatesGroup, State


class AdminState(StatesGroup):
    waiting_for_admin_id = State()


class AdminStateChannel(StatesGroup):
    channel_for_admin_id = State()


class PostState(StatesGroup):
    title = State()
    message = State()
    video_url = State()
    image_url = State()
    confirm = State()
