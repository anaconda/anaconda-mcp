from collections.abc import Sequence

import readchar
from rich.console import Console
from rich.live import Live
from rich.style import Style
from rich.table import Table

console = Console(highlight=False)

_CURSOR = Style(color="cyan", bold=True)
_CHECK = "[bold green]✔︎[/bold green]"
_UNCHECK = "[   ]"


def _checkbox_table(header: str, rows: list[str], cursor: int, checked: set[int]) -> Table:
    table = Table(box=None, show_header=True, padding=(0, 1))
    table.add_column(header)

    for i, row in enumerate(rows):
        at_cursor = i == cursor
        mark = f"[ {_CHECK} ]" if i in checked else _UNCHECK
        pointer = "▶" if at_cursor else " "
        style = _CURSOR if at_cursor else None
        table.add_row(f"  {pointer}  {mark}  {row}", style=style)

    return table


def _select_table(header: str, rows: list[str], cursor: int) -> Table:
    table = Table(box=None, show_header=True, padding=(0, 1))
    table.add_column(header)

    for i, row in enumerate(rows):
        at_cursor = i == cursor
        pointer = "▶" if at_cursor else " "
        style = _CURSOR if at_cursor else None
        table.add_row(f"  {pointer}  {row}", style=style)

    return table


def multiselect_checkbox(
    header: str,
    choices: Sequence[str],
    checked: Sequence[str] = (),
) -> list[str]:
    """Arrow keys to navigate, Space to toggle, Enter to confirm, q to abort.

    Returns the selected values, or raises KeyboardInterrupt on q/Ctrl-C.
    """
    rows = list(choices)
    checked_set: set[int] = {i for i, v in enumerate(rows) if v in set(checked)}
    cursor = 0

    console.print("[dim]↑↓ navigate  Space toggle  Enter confirm  q cancel[/dim]")

    with Live(_checkbox_table(header, rows, cursor, checked_set), auto_refresh=False, console=console) as live:
        while True:
            keypress = readchar.readkey()

            if keypress in (readchar.key.UP, "k"):
                cursor = max(0, cursor - 1)
            elif keypress in (readchar.key.DOWN, "j"):
                cursor = min(len(rows) - 1, cursor + 1)
            elif keypress == readchar.key.SPACE:
                if cursor in checked_set:
                    checked_set.discard(cursor)
                else:
                    checked_set.add(cursor)
            elif keypress in ("\n", "\r", readchar.key.ENTER):
                live.stop()
                return [rows[i] for i in sorted(checked_set)]
            elif keypress in ("q", readchar.key.CTRL_C):
                live.stop()
                raise KeyboardInterrupt

            live.update(_checkbox_table(header, rows, cursor, checked_set), refresh=True)


def single_select(
    header: str,
    choices: Sequence[str],
    default: str | None = None,
) -> str:
    """Arrow keys to navigate, Enter to confirm, q to abort.

    Returns the selected value, or raises KeyboardInterrupt on q/Ctrl-C.
    """
    rows = list(choices)
    cursor = rows.index(default) if default and default in rows else 0

    console.print("[dim]↑↓ navigate  Enter confirm  q cancel[/dim]")

    with Live(_select_table(header, rows, cursor), auto_refresh=False, console=console) as live:
        while True:
            keypress = readchar.readkey()

            if keypress in (readchar.key.UP, "k"):
                cursor = max(0, cursor - 1)
            elif keypress in (readchar.key.DOWN, "j"):
                cursor = min(len(rows) - 1, cursor + 1)
            elif keypress in ("\n", "\r", readchar.key.ENTER):
                live.stop()
                return rows[cursor]
            elif keypress in ("q", readchar.key.CTRL_C):
                live.stop()
                raise KeyboardInterrupt

            live.update(_select_table(header, rows, cursor), refresh=True)
