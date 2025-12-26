from floorcast.domain.models import Area, Device, Entity, Floor, Registry


class TestEntity:
    def test_from_dict(self):
        data = {
            "entity_id": "light.living_room",
            "entity_category": None,
            "device_id": "dev123",
            "name": "Living Room Light",
            "original_name": "Light",
            "area_id": "living_room",
        }

        entity = Entity.from_dict(data)

        assert entity.id == "light.living_room"
        assert entity.domain == "light"
        assert entity.display_name == "Living Room Light"
        assert entity.area_id == "living_room"

    def test_from_dict_falls_back_to_original_name(self):
        data = {
            "entity_id": "sensor.temp",
            "entity_category": None,
            "device_id": None,
            "name": None,
            "original_name": "Temperature",
            "area_id": None,
        }

        entity = Entity.from_dict(data)

        assert entity.display_name == "Temperature"

    def test_from_dict_falls_back_to_entity_id(self):
        data = {
            "entity_id": "sensor.temp",
            "entity_category": None,
            "device_id": None,
            "name": None,
            "original_name": None,
            "area_id": None,
        }

        entity = Entity.from_dict(data)

        assert entity.display_name == "sensor.temp"


class TestDevice:
    def test_from_dict(self):
        data = {
            "id": "abc123",
            "name": "Hue Bridge",
            "name_by_user": "My Bridge",
            "area_id": "office",
        }

        device = Device.from_dict(data)

        assert device.id == "abc123"
        assert device.display_name == "My Bridge"
        assert device.area_id == "office"

    def test_from_dict_falls_back_to_name(self):
        data = {
            "id": "abc123",
            "name": "Hue Bridge",
            "name_by_user": None,
            "area_id": None,
        }

        device = Device.from_dict(data)

        assert device.display_name == "Hue Bridge"


class TestArea:
    def test_from_dict(self):
        data = {
            "area_id": "living_room",
            "name": "Living Room",
            "floor_id": "floor_1",
        }

        area = Area.from_dict(data)

        assert area.id == "living_room"
        assert area.display_name == "Living Room"
        assert area.floor_id == "floor_1"


class TestFloor:
    def test_from_dict(self):
        data = {
            "floor_id": "floor_1",
            "name": "First Floor",
            "level": 1,
        }

        floor = Floor.from_dict(data)

        assert floor.id == "floor_1"
        assert floor.display_name == "First Floor"
        assert floor.level == 1

    def test_from_dict_level_optional(self):
        data = {
            "floor_id": "floor_1",
            "name": "First Floor",
        }

        floor = Floor.from_dict(data)

        assert floor.level is None


class TestRegistry:
    def test_to_dict(self):
        registry = Registry(
            entities={
                "light.a": Entity(
                    id="light.a",
                    entity_category="",
                    domain="light",
                    display_name="A",
                    device_id="fake",
                    area_id=None,
                )
            },
            devices={"dev1": Device(id="dev1", area_id=None, display_name="Device 1")},
            areas={"area1": Area(id="area1", display_name="Area 1", floor_id=None)},
            floors={"floor1": Floor(id="floor1", display_name="Floor 1", level=0)},
        )

        result = registry.to_dict()

        assert "light.a" in result["entities"]
        assert result["entities"]["light.a"]["display_name"] == "A"
        assert "dev1" in result["devices"]
        assert "area1" in result["areas"]
        assert "floor1" in result["floors"]

    def test_empty(self):
        assert Registry.empty().to_dict() == {
            "entities": {},
            "devices": {},
            "areas": {},
            "floors": {},
        }
