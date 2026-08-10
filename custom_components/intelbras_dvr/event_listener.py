"""Listener de background para o stream de eventos do DVR."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    EVENT_BACKOFF_MAX,
    EVENT_BACKOFF_MIN,
    SIGNAL_EVENT,
)
from .dvr import EventStreamError, IntelbrasClient

_LOGGER = logging.getLogger(__name__)


class IntelbrasEventListener:
    """Consome stream_events e dispara sinais no dispatcher."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: IntelbrasClient,
        codes: list[str],
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.codes = codes
        self._task: asyncio.Task | None = None
        self._signal = SIGNAL_EVENT.format(entry_id=entry.entry_id)

    def start(self) -> None:
        """Inicia a task de background (idempotente)."""
        if not self.codes:
            _LOGGER.debug("Nenhum código de evento configurado — listener inativo")
            return
        if self._task is not None and not self._task.done():
            return
        self._task = self.entry.async_create_background_task(
            self.hass,
            self._run(),
            name=f"intelbras_dvr_events_{self.entry.entry_id}",
        )

    async def stop(self) -> None:
        """Cancela a task e aguarda o encerramento limpo."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        """Loop de conexão com backoff exponencial."""
        backoff = EVENT_BACKOFF_MIN
        while True:
            try:
                _LOGGER.debug(
                    "Conectando eventManager em %s (codes=%s)",
                    self.client.host,
                    self.codes,
                )
                async for event in self.client.stream_events(self.codes):
                    backoff = EVENT_BACKOFF_MIN
                    async_dispatcher_send(self.hass, self._signal, event)
            except asyncio.CancelledError:
                raise
            except EventStreamError as ex:
                _LOGGER.warning(
                    "Stream de eventos do DVR %s caiu: %s — reconectando em %ss",
                    self.client.host,
                    ex,
                    backoff,
                )
            except Exception as ex:  # noqa: BLE001
                _LOGGER.exception(
                    "Erro inesperado no listener do DVR %s: %s — reconectando em %ss",
                    self.client.host,
                    ex,
                    backoff,
                )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, EVENT_BACKOFF_MAX)
