"""FSM states for Master CRM Bot."""

from aiogram.fsm.state import State, StatesGroup


class MasterRegistration(StatesGroup):
    """Master registration flow states."""
    name = State()        # Step 1: Name/nickname
    sphere = State()      # Step 2: Field of activity
    contacts = State()    # Step 3: Contact info for clients
    socials = State()     # Step 4: Social networks and channels
    work_hours = State()  # Step 5: Working hours


class ClientRegistration(StatesGroup):
    """Client registration flow states."""
    name = State()      # Step 1: Name
    phone = State()     # Step 2: Phone number
    birthday = State()  # Step 3: Birthday (optional)
