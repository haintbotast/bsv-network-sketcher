from pydantic import ValidationError

from app.schemas.device import DeviceCreate, DeviceUpdate


def test_device_create_accepts_cloud_types() -> None:
    for device_type in (
        "Cloud",
        "Cloud-Network",
        "Cloud-Security",
        "Cloud-Service",
    ):
        payload = DeviceCreate(
            name=f"{device_type}-1",
            area_name="Edge",
            device_type=device_type,
        )
        assert payload.device_type == device_type


def test_device_update_rejects_unknown_cloud_type() -> None:
    try:
        DeviceUpdate(device_type="Cloud-Other")
    except ValidationError:
        return
    raise AssertionError("DeviceUpdate phải từ chối device_type ngoài danh sách preset")
