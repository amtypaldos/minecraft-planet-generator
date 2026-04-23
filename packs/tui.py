"""
Planet Generator TUI — manage Bedrock planet items interactively.

Usage:
    uv run tui.py

Keys:
    a / n   Add a new planet
    e       Edit selected planet
    d       Delete selected planet
    r       Refresh planet list
    q       Quit
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static
try:
    from textual.worker import work
except ImportError:
    from textual._work_decorator import work  # textual >=1.0 / 8.x

from add_planet import add_planet, delete_planet, edit_planet, parse_planets


class PlanetFormScreen(ModalScreen):
    """Add or edit a planet."""

    DEFAULT_CSS = """
    PlanetFormScreen {
        align: center middle;
    }
    PlanetFormScreen > Vertical {
        width: 62;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    PlanetFormScreen #form-title {
        text-style: bold;
        width: 1fr;
        content-align: center middle;
        padding-bottom: 1;
        border-bottom: solid $primary-darken-2;
        margin-bottom: 1;
    }
    PlanetFormScreen Label {
        margin-top: 1;
        color: $text-muted;
    }
    PlanetFormScreen Input {
        margin-top: 0;
    }
    PlanetFormScreen #hint {
        color: $text-disabled;
        margin-top: 1;
    }
    PlanetFormScreen #form-buttons {
        margin-top: 2;
        height: 3;
        align: right middle;
    }
    PlanetFormScreen Button {
        margin-left: 1;
    }
    """

    def __init__(self, planet: dict | None = None) -> None:
        super().__init__()
        self.planet = planet

    def compose(self) -> ComposeResult:
        editing = self.planet is not None
        with Vertical():
            yield Static(
                "✏  Edit Planet" if editing else "✦  Add Planet",
                id="form-title",
            )
            if editing:
                yield Static(
                    f"[bold]{self.planet['name']}[/bold]"
                    f"  ·  ID: [dim]{self.planet['id']}[/dim]",
                    id="hint",
                )
                yield Label("Radius (leave blank to keep current)")
                yield Input(
                    placeholder=str(self.planet["radius"]),
                    id="radius",
                )
            else:
                yield Label("Name [bold red]*[/bold red]")
                yield Input(placeholder="Haumea", id="name")
                yield Label("Radius (blocks) [bold red]*[/bold red]")
                yield Input(placeholder="3", id="radius")

            yield Label(
                "Block [bold red]*[/bold red]" if not editing
                else "Block (leave blank to keep current)"
            )
            yield Input(
                value=self.planet["block"] if editing else "",
                placeholder="white_wool",
                id="block",
            )
            yield Label("Ring block [dim](optional — leave blank for none)[/dim]")
            yield Input(
                value=(self.planet["ring_block"] or "") if editing else "",
                placeholder="white_wool",
                id="ring_block",
            )
            yield Label("Icon color hex [dim](optional — auto-detected from block)[/dim]")
            yield Input(placeholder="e.g. 4488ff", id="color")

            with Horizontal(id="form-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        editing = self.planet is not None
        name       = self.planet["name"] if editing else self.query_one("#name", Input).value.strip()
        radius_str = self.query_one("#radius", Input).value.strip()
        block      = self.query_one("#block", Input).value.strip() or None
        ring_block = self.query_one("#ring_block", Input).value.strip() or None
        color      = self.query_one("#color", Input).value.strip() or None

        if not editing:
            if not name:
                self.notify("Name is required", severity="error")
                return
            if not block:
                self.notify("Block is required", severity="error")
                return
            if not radius_str:
                self.notify("Radius is required", severity="error")
                return

        if radius_str:
            try:
                radius = int(radius_str)
                if radius < 1 or radius > 150:
                    self.notify("Radius must be between 1 and 150", severity="error")
                    return
            except ValueError:
                self.notify("Radius must be a whole number", severity="error")
                return
        else:
            radius = None

        self.dismiss({
            "name": name,
            "radius": radius,
            "block": block,
            "ring_block": ring_block,
            "color": color,
        })

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class ConfirmDeleteScreen(ModalScreen):
    """Confirm planet deletion."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    ConfirmDeleteScreen > Vertical {
        width: 46;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }
    ConfirmDeleteScreen #confirm-message {
        width: 1fr;
        content-align: center middle;
        padding: 1 0;
    }
    ConfirmDeleteScreen Horizontal {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    ConfirmDeleteScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self, planet_name: str) -> None:
        super().__init__()
        self.planet_name = planet_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                f"Delete [bold]{self.planet_name}[/bold]?\n"
                "[dim]This cannot be undone.[/dim]",
                id="confirm-message",
            )
            with Horizontal():
                yield Button("Delete", variant="error", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)


class PlanetApp(App):
    """Planet Generator — manage Bedrock solar system planet items."""

    TITLE = "Planet Generator"
    SUB_TITLE = "Bedrock add-on manager"

    CSS = """
    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("a,n", "add",     "Add",     show=True),
        Binding("e",   "edit",    "Edit",    show=True),
        Binding("d",   "delete",  "Delete",  show=True),
        Binding("r",   "refresh", "Refresh", show=False),
        Binding("q",   "quit",    "Quit",    show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "ID", "Radius", "Block", "Rings")
        table.cursor_type = "row"
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for p in parse_planets():
            table.add_row(
                p["name"],
                p["id"],
                str(p["radius"]),
                p["block"],
                p["ring_block"] or "—",
                key=p["id"],
            )

    def action_refresh(self) -> None:
        self.refresh_table()

    def get_selected_planet(self) -> dict | None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        from textual.coordinate import Coordinate
        cell_key = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0))
        row_key = str(cell_key.row_key.value)
        for p in parse_planets():
            if p["id"] == row_key:
                return p
        return None

    # ── add ────────────────────────────────────────────────────────────────────

    def action_add(self) -> None:
        def on_result(data: dict | None) -> None:
            if data:
                self._do_add(data)
        self.push_screen(PlanetFormScreen(), on_result)

    @work(thread=True)
    def _do_add(self, data: dict) -> None:
        try:
            full_id = add_planet(
                name=data["name"],
                radius=data["radius"],
                block=data["block"],
                ring_block=data["ring_block"],
                color=data["color"],
            )
            self.call_from_thread(self.refresh_table)
            self.call_from_thread(
                self.notify, f"Added {full_id} — restart server to apply"
            )
        except ValueError as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    # ── edit ───────────────────────────────────────────────────────────────────

    def action_edit(self) -> None:
        planet = self.get_selected_planet()
        if not planet:
            self.notify("Select a planet first", severity="warning")
            return

        def on_result(data: dict | None) -> None:
            if data:
                self._do_edit(planet["name"], data)
        self.push_screen(PlanetFormScreen(planet=planet), on_result)

    @work(thread=True)
    def _do_edit(self, name: str, data: dict) -> None:
        try:
            full_id = edit_planet(
                name=name,
                block=data.get("block"),
                radius=data.get("radius"),
                ring_block=data.get("ring_block"),
                color=data.get("color"),
            )
            self.call_from_thread(self.refresh_table)
            self.call_from_thread(
                self.notify, f"Updated {full_id} — restart server to apply"
            )
        except ValueError as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    # ── delete ─────────────────────────────────────────────────────────────────

    def action_delete(self) -> None:
        planet = self.get_selected_planet()
        if not planet:
            self.notify("Select a planet first", severity="warning")
            return

        def on_result(confirmed: bool) -> None:
            if confirmed:
                self._do_delete(planet["name"])
        self.push_screen(ConfirmDeleteScreen(planet["name"]), on_result)

    @work(thread=True)
    def _do_delete(self, name: str) -> None:
        try:
            full_id = delete_planet(name)
            self.call_from_thread(self.refresh_table)
            self.call_from_thread(
                self.notify, f"Deleted {full_id} — restart server to apply"
            )
        except ValueError as e:
            self.call_from_thread(self.notify, str(e), severity="error")


if __name__ == "__main__":
    PlanetApp().run()
