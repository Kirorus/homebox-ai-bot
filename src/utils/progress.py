import asyncio
from typing import List, Tuple, Optional


class AnimatedProgress:
    """Reusable animated progress for editing a Telegram message in-place.

    Usage:
      progress = AnimatedProgress(message, base_text)
      await progress.start()
      ... long op ...
      await progress.stop()
    """

    def __init__(
        self,
        message,
        base_text: str,
        bar_length: int = 14,
        phases: Optional[List[Tuple[str, int]]] = None,
        interval_sec: float = 0.3,
    ) -> None:
        self.message = message
        self.base_text = base_text
        self.bar_length = max(6, bar_length)
        self.phases = phases or [("Working", 10)]
        self.total_ticks = max(1, sum(t for _, t in self.phases))
        self.interval_sec = interval_sec
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._animate())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await self._task
        except Exception:
            pass
        finally:
            self._task = None

    async def _animate(self) -> None:
        filled = 0
        spin_idx = 0
        while not self._stop_event.is_set():
            try:
                filled_cells = min(
                    self.bar_length,
                    int((filled / self.total_ticks) * self.bar_length),
                )
                bar = "█" * filled_cells + "░" * (self.bar_length - filled_cells)

                # Determine current phase label
                acc = 0
                label = self.phases[-1][0]
                for l, t in self.phases:
                    if filled < acc + t:
                        label = l
                        break
                    acc += t

                spin = self._spinner[spin_idx % len(self._spinner)]
                spin_idx += 1
                await self.message.edit_text(f"{self.base_text}\n\n{spin} [{bar}] {label}")
                filled = (filled + 1) % (self.total_ticks + 1)
            except Exception:
                # Ignore edit failures (rate limits or message not modified)
                pass
            await asyncio.sleep(self.interval_sec)


