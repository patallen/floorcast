import uuid

from floorcast.ha_protocol import HAEvent
from floorcast.models import Event


class EnrichmentService:
    async def enrich(self, ha_event: HAEvent) -> Event:
        data = ha_event.data
        entity_id = data["entity_id"]
        new_state = data.get("new_state") or {}
        state = new_state.get("state")
        external_id = ha_event.context["id"]

        return Event(
            external_id=external_id,
            entity_id=entity_id,
            event_id=uuid.uuid4(),
            state=state,
            event_type=ha_event.event_type,
            timestamp=ha_event.time_fired,
            data=new_state,
        )
