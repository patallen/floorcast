import uuid

from floorcast.models import Event
from floorcast.protocol import HAEvent


class EventEnricher:
    async def enrich(self, ha_event: HAEvent) -> Event:
        data = ha_event.data
        entity_id = data["entity_id"]
        new_state = data["new_state"]
        state = new_state["state"] if new_state else None
        external_id = ha_event.context["id"]

        return Event(
            id=None,
            external_id=external_id,
            entity_id=entity_id,
            event_id=uuid.uuid4(),
            state=state,
            event_type=ha_event.event_type,
            timestamp=ha_event.time_fired,
            data=new_state,
        )
