"""FSM states for Master CRM Bot."""

from aiogram.fsm.state import State, StatesGroup


class MasterRegistration(StatesGroup):
    """Master registration flow states."""
    name = State()        # Step 1: Name/nickname
    sphere = State()      # Step 2: Field of activity
    timezone = State()    # Step 3: Timezone selection
    contacts = State()    # Step 4: Contact info for clients
    socials = State()     # Step 5: Social networks and channels
    work_hours = State()  # Step 6: Working hours


class ClientRegistration(StatesGroup):
    """Client registration flow states."""
    consent = State()   # Step 0: Privacy policy consent
    name = State()      # Step 1: Name
    phone = State()     # Step 2: Phone number
    birthday = State()  # Step 3: Birthday (optional)


class ClientDeletion(StatesGroup):
    """Client data deletion flow states."""
    confirm = State()  # Waiting for confirmation


class CreateOrder(StatesGroup):
    """Create order flow states (7 steps)."""
    search_client = State()     # Step 1: Search client by name/phone
    select_client = State()     # Step 1b: Select from search results
    address = State()           # Step 2: Enter or select address
    date = State()              # Step 3: Select date from calendar
    hour = State()              # Step 4a: Select hour (8-19)
    minutes = State()           # Step 4b: Select minutes (00/30)
    services = State()          # Step 5: Select services
    custom_service = State()    # Step 5b: Enter custom service name
    amount = State()            # Step 6: Enter amount
    confirm = State()           # Step 7: Confirmation screen
    edit_field = State()        # Edit mode: select which field to edit


class CreateClientInOrder(StatesGroup):
    """Mini-FSM for creating new client during order creation."""
    name = State()      # Client name
    phone = State()     # Client phone
    birthday = State()  # Client birthday (optional)


class CompleteOrder(StatesGroup):
    """Complete order flow states."""
    confirm_amount = State()    # Step 1: Confirm or change amount
    payment_type = State()      # Step 2: Select payment type
    use_bonus = State()         # Step 3: Use bonus points (if available)
    bonus_amount = State()      # Step 3b: Enter bonus amount to use
    confirm = State()           # Step 4: Final confirmation


class MoveOrder(StatesGroup):
    """Move/reschedule order flow states."""
    date = State()      # Select new date
    hour = State()      # Select new hour
    minutes = State()   # Select new minutes
    confirm = State()   # Confirm changes (show old vs new)


class CancelOrder(StatesGroup):
    """Cancel order flow states."""
    reason = State()        # Select or enter reason
    custom_reason = State() # Enter custom reason
    confirm = State()       # Confirm cancellation


class ClientAdd(StatesGroup):
    """Add new client from Clients menu."""
    name = State()      # Client name
    phone = State()     # Client phone
    birthday = State()  # Client birthday (optional)


class ServiceAdd(StatesGroup):
    """Add new service to catalog."""
    name = State()         # Service name
    price = State()        # Service price
    description = State()  # Service description (optional)


class ServiceEdit(StatesGroup):
    """Edit service in catalog."""
    name = State()         # Edit service name
    price = State()        # Edit service price
    description = State()  # Edit service description


class ProfileEdit(StatesGroup):
    """Edit master profile fields."""
    waiting_value = State()  # Waiting for new field value


class BonusSettingsEdit(StatesGroup):
    """Edit bonus program settings."""
    waiting_value = State()  # Waiting for new setting value


class BonusMessageEdit(StatesGroup):
    """Edit bonus message settings (welcome/birthday)."""
    waiting_amount = State()  # Waiting for bonus amount
    waiting_text = State()    # Waiting for custom text
    waiting_photo = State()   # Waiting for photo upload


class ClientEdit(StatesGroup):
    """Edit client fields."""
    waiting_value = State()  # Waiting for new field value


class ClientNote(StatesGroup):
    """Edit client note."""
    waiting_note = State()  # Waiting for note text


class BonusManual(StatesGroup):
    """Manual bonus add/subtract."""
    waiting_amount = State()   # Waiting for amount
    waiting_comment = State()  # Waiting for comment


class BroadcastFSM(StatesGroup):
    """Broadcast message flow states."""
    text = State()      # Step 1: Message text
    media = State()     # Step 2: Attach photo/video (optional)
    segment = State()   # Step 3: Select recipient segment
    confirm = State()   # Step 4: Preview and confirm


class PromoFSM(StatesGroup):
    """Promo campaign creation flow states."""
    title = State()       # Step 1: Promo title
    description = State() # Step 2: Promo description
    date_from = State()   # Step 3: Start date
    date_to = State()     # Step 4: End date
    confirm = State()     # Step 5: Confirm and optionally broadcast


class ReportPeriodFSM(StatesGroup):
    """Custom report period selection flow."""
    date_from = State()   # Step 1: Start date
    date_to = State()     # Step 2: End date


# =============================================================================
# Client Bot FSM States
# =============================================================================

class OrderRequestFSM(StatesGroup):
    """Order request flow in client_bot."""
    service = State()         # Step 1: Select service
    custom_service = State()  # Step 1b: Enter custom service name
    comment = State()         # Step 2: Add comment (optional)
    confirm = State()         # Step 3: Confirm and send


class QuestionFSM(StatesGroup):
    """Question to master flow in client_bot."""
    text = State()  # Step 1: Enter question text


class MediaFSM(StatesGroup):
    """Media sending flow in client_bot."""
    media = State()    # Step 1: Send photo/video
    comment = State()  # Step 2: Add comment (optional)


class ClientRescheduleOrder(StatesGroup):
    """Client reschedule order flow in client_bot."""
    date = State()       # Step 1: Select new date
    hour = State()       # Step 2: Select hour
    minutes = State()    # Step 3: Select minutes
    confirm = State()    # Step 4: Confirm reschedule


class ClientCancelOrder(StatesGroup):
    """Client cancel order flow in client_bot."""
    reason = State()   # Step 1: Select/enter reason
    confirm = State()  # Step 2: Confirm cancellation
