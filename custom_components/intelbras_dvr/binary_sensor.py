"""Binary sensors de evento (movimento, IVS, perda de vídeo, etc.)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_CHANNELS,
    CONF_EVENT_AUTO_OFF,
    CONF_EVENT_CODES,
    DATA_COORDINATOR,
    DEFAULT_CHANNELS,
    DEFAULT_EVENT_AUTO_OFF,
    DEFAULT_EVENT_CODES,
    DOMAIN,
    SIGNAL_EVENT,
)
from .coordinator import IntelbrasCoordinator
from .dvr import DvrEvent

# Rótulos em português por código de evento
_CODE_LABELS: dict[str, str] = {
    "VideoMotion": "Movimento",
    "SmartMotionHuman": "Detecção de pessoa",
    "SmartMotionVehicle": "Detecção de veículo",
    "CrossLineDetection": "Cruzamento de linha",
    "CrossRegionDetection": "Invasão de região",
    "VideoLoss": "Perda de vídeo",
    "VideoBlind": "Câmera coberta",
    "AlarmLocal": "Alarme local",
}

_CODE_DEVICE_CLASS: dict[str, BinarySensorDeviceClass] = {
    "VideoMotion": BinarySensorDeviceClass.MOTION,
    # SMD é detecção de objeto, não de pixel. OCCUPANCY separa os dois na UI
    # e nas automações, que é exatamente o ponto de assinar estes códigos.
    "SmartMotionHuman": BinarySensorDeviceClass.OCCUPANCY,
    "SmartMotionVehicle": BinarySensorDeviceClass.OCCUPANCY,
    "CrossLineDetection": BinarySensorDeviceClass.MOTION,
    "CrossRegionDetection": BinarySensorDeviceClass.MOTION,
    "VideoLoss": BinarySensorDeviceClass.PROBLEM,
    "VideoBlind": BinarySensorDeviceClass.PROBLEM,
    "AlarmLocal": BinarySensorDeviceClass.SAFETY,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord: IntelbrasCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    channels = entry.options.get(
        CONF_CHANNELS, entry.data.get(CONF_CHANNELS, DEFAULT_CHANNELS)
    )
    codes = entry.options.get(
        CONF_EVENT_CODES, entry.data.get(CONF_EVENT_CODES, DEFAULT_EVENT_CODES)
    )
    auto_off = entry.options.get(
        CONF_EVENT_AUTO_OFF,
        entry.data.get(CONF_EVENT_AUTO_OFF, DEFAULT_EVENT_AUTO_OFF),
    )
    entities = [
        IntelbrasEventBinarySensor(entry, coord, ch, code, auto_off)
        for ch in range(1, channels + 1)
        for code in codes
    ]
    async_add_entities(entities)


class IntelbrasEventBinarySensor(BinarySensorEntity):
    """Sensor binário de um canal × código de evento."""

    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        coord: IntelbrasCoordinator,
        channel: int,
        code: str,
        auto_off: int,
    ) -> None:
        self._entry = entry
        self._coord = coord
        self._channel = channel
        self._code = code
        self._auto_off = auto_off
        self._attr_unique_id = f"{entry.entry_id}_ch{channel}_{code.lower()}"
        label = _CODE_LABELS.get(code, code)
        self._attr_name = f"DVR Canal {channel} {label}"
        self._attr_device_class = _CODE_DEVICE_CLASS.get(code)
        self._attr_is_on = False
        self._unsub_auto_off = None

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
            "manufacturer": "Intelbras",
            "model": "DVR (Dahua-compatible)",
            "connections": (
                {("mac", self._coord.mac)} if self._coord.mac else set()
            ),
        }

    async def async_added_to_hass(self) -> None:
        signal = SIGNAL_EVENT.format(entry_id=self._entry.entry_id)
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_event)
        )

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_auto_off()

    @callback
    def _handle_event(self, event: DvrEvent) -> None:
        if event.channel != self._channel or event.code != self._code:
            return
        self._attr_is_on = event.active
        self._cancel_auto_off()
        if event.active and self._auto_off > 0:
            self._unsub_auto_off = async_call_later(
                self.hass, self._auto_off, self._auto_off_callback
            )
        self.async_write_ha_state()

    @callback
    def _auto_off_callback(self, _now) -> None:
        self._unsub_auto_off = None
        if self._attr_is_on:
            self._attr_is_on = False
            self.async_write_ha_state()

    def _cancel_auto_off(self) -> None:
        if self._unsub_auto_off is not None:
            self._unsub_auto_off()
            self._unsub_auto_off = None
