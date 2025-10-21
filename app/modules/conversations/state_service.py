
import json
from app.core.redis import redis_manager

class ConversationStateService:
    """
    Manages the state of an intake conversation in Redis.
    """
    def __init__(self, conversation_id: str):
        self.redis = redis_manager.redis
        self.convo_id = conversation_id
        self.required_fields_key = f"convo_state:{self.convo_id}:required_fields"
        self.extracted_data_key = f"convo_state:{self.convo_id}:extracted_data"

    async def initialize_session(self, user_phone: str):
        """
        Initializes a new conversation session in Redis if it doesn't exist.
        Sets the initial list of required fields and the user's phone number.
        """
        if await self.redis.exists(self.required_fields_key):
            return False # Session already exists

        initial_required_fields = [
            "patient.name",
            "patient.dob",
            "intake.chief_complaint.text",
            "intake.symptoms",
            "intake.condition_history",
            "intake.allergies",
            "intake.medications",
            "intake.family_history",
            "appointment_request.preferred_location",
            "appointment_request.preferred_day",
            "appointment_request.preferred_time"
        ]
        
        # Use a pipeline to ensure atomicity
        pipe = self.redis.pipeline()
        pipe.rpush(self.required_fields_key, *initial_required_fields)
        # Store the user's phone number along with any other initial data
        pipe.hset(self.extracted_data_key, mapping={"user_phone": user_phone})
        await pipe.execute()
        return True

    async def get_required_fields(self) -> list[str]:
        """Retrieves the current list of required fields."""
        return await self.redis.lrange(self.required_fields_key, 0, -1)

    async def get_extracted_data(self) -> dict:
        """Retrieves all extracted data for the conversation."""
        return await self.redis.hgetall(self.extracted_data_key)

    async def update_state(self, new_data: dict, required_fields_before_update: list[str], next_field_from_gpt: str | None):
        """
        Updates the conversation state with newly extracted data.
        Applies special logic to differentiate between a 'current' field answer and other secondary fields.
        """
        if not new_data:
            return

        # Determine the field that the user was actually asked about.
        # This is typically the field just before the `next_field` in the required list.
        current_field_key = None
        if next_field_from_gpt:
            try:
                idx = required_fields_before_update.index(next_field_from_gpt)
                if idx > 0:
                    current_field_key = required_fields_before_update[idx - 1]
            except ValueError:
                # This can happen if next_field is the last one, or not in the list.
                # Fallback: consider the first key in new_data as the current field.
                if new_data:
                    current_field_key = list(new_data.keys())[0]
        elif new_data: # If no next_field, assume first key is the primary one.
            current_field_key = list(new_data.keys())[0]

        keys_to_remove = set()
        for key, value in new_data.items():
            key = key.strip()
            # The current field is always a valid answer, even if "none".
            if key == current_field_key:
                keys_to_remove.add(key)
            # For all other secondary fields, only accept the answer if it's not "none".
            elif value is not None and str(value).lower().strip() != 'none':
                keys_to_remove.add(key)

        # Fetch, Filter, and Replace the required_fields list
        updated_fields = [field for field in required_fields_before_update if field not in keys_to_remove]

        pipe = self.redis.pipeline()

        # Replace the old list with the new one
        pipe.delete(self.required_fields_key)
        if updated_fields:
            pipe.rpush(self.required_fields_key, *updated_fields)

        # Update the hash data
        for key, value in new_data.items():
            if isinstance(value, (dict, list)):
                pipe.hset(self.extracted_data_key, key.strip(), json.dumps(value))
            else:
                pipe.hset(self.extracted_data_key, key.strip(), str(value))
        
        await pipe.execute()

    async def is_complete(self) -> bool:
        """DEPRECATED: Completion is now determined by n8n sending an empty next_question."""
        count = await self.redis.llen(self.required_fields_key)
        return count == 0

    async def set_user_phone(self, user_phone: str):
        """
        Ensures the user's phone number is stored in the extracted data.
        """
        await self.redis.hset(self.extracted_data_key, "user_phone", user_phone)
