"""Nuxel Home — GTK4 Launcher Grid (FlowBox + DragSource/DropTarget)"""

import logging
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GLib

logger = logging.getLogger(__name__)


class AppCard(Gtk.Box):
    """Single app icon + label, with GTK4 drag source + drop target."""

    __gtype_name__ = "NuxelAppCard"

    def __init__(self, app, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4, **kwargs)
        self._app = app
        self._drag_active = False
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.get_style_context().add_class("app-card")
        self.set_hexpand(False)
        self.set_vexpand(False)

        # Icon
        self._icon = Gtk.Label(label=app.icon)
        self._icon.get_style_context().add_class("app-icon")
        self._icon.set_halign(Gtk.Align.CENTER)
        self.append(self._icon)

        # Name
        self._label = Gtk.Label(label=app.name)
        self._label.get_style_context().add_class("app-label")
        self._label.set_halign(Gtk.Align.CENTER)
        self._label.set_max_width_chars(8)
        self._label.set_ellipsize(True)
        self.append(self._label)

        # ---- GTK4 Drag Source ----
        drag_source = Gtk.DragSource.new()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_drag_prepare)
        drag_source.connect("drag-begin", self._on_drag_begin)
        drag_source.connect("drag-end", self._on_drag_end)
        self.add_controller(drag_source)

        # ---- GTK4 Drop Target ----
        # GTK4 positional API: Gtk.DropTarget.new(type, actions)
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.connect("drop", self._on_drop)
        self.add_controller(drop_target)

    @property
    def app(self):
        return self._app

    @property
    def drag_active(self):
        return self._drag_active

    def _on_drag_prepare(self, source, x, y):
        """Provide the app ID as drag content."""
        val = GObject.Value(str, self._app.id)
        return Gdk.ContentProvider.new_for_value(val)

    def _on_drag_begin(self, source, drag):
        """Visual feedback: dim the dragged card."""
        self._drag_active = True
        self.set_opacity(0.4)
        self.get_style_context().add_class("app-card-dragging")

    def _on_drag_end(self, source, drag, delete_data):
        self._drag_active = False
        self.set_opacity(1.0)
        self.get_style_context().remove_class("app-card-dragging")

    def _on_drop(self, target, value, x, y):
        """Handle drop — emit signal for reorder."""
        dragged_id = value if isinstance(value, str) else str(value)
        flowbox = self.get_parent()
        if flowbox and hasattr(flowbox, 'get_parent'):
            grid = flowbox.get_parent()  # the LauncherGrid or FlowBox wrapper
            # walk up to find LauncherGrid
            p = grid
            for _ in range(3):
                if hasattr(p, '_handle_drop'):
                    p._handle_drop(dragged_id, self._app.id)
                    return True
                p = p.get_parent() if hasattr(p, 'get_parent') else None
                if p is None:
                    break
        logger.debug("Drop: %s → %s", dragged_id, self._app.id)
        return True


class LauncherGrid(Gtk.ScrolledWindow):
    """Scrollable app grid with GTK4 FlowBox + GestureClick for launch."""

    __gtype_name__ = "NuxelLauncherGrid"
    __gsignals__ = {
        "app-launch": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, registry, **kwargs):
        super().__init__(**kwargs)
        self._registry = registry
        self._cards = {}

        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.get_style_context().add_class("grid-scroll")

        # Vertical layout
        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self._vbox)

        # Header
        self._header = Gtk.Label(label="Nuxel")
        self._header.get_style_context().add_class("app-grid-header")
        self._header.set_halign(Gtk.Align.START)
        self._header.set_margin_start(24)
        self._vbox.append(self._header)

        # FlowBox
        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_max_children_per_line(4)
        self._flowbox.set_min_children_per_line(3)
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_homogeneous(True)
        self._flowbox.set_row_spacing(0)
        self._flowbox.set_column_spacing(0)
        self._flowbox.set_activate_on_single_click(True)
        self._flowbox.get_style_context().add_class("launcher-grid")
        self._flowbox.connect("child-activated", self._on_child_activated)
        self._vbox.append(self._flowbox)

        # Toast overlay
        self._toast = Gtk.Label()
        self._toast.get_style_context().add_class("toast-label")
        self._toast.set_halign(Gtk.Align.CENTER)
        self._toast_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._toast_box.set_valign(Gtk.Align.END)
        self._toast_box.set_halign(Gtk.Align.CENTER)
        self._toast_box.get_style_context().add_class("toast-overlay")
        self._toast_box.set_visible(False)
        self._toast_box.append(self._toast)
        self._vbox.append(self._toast_box)

        self._rebuild()

    def show_toast(self, message, duration_ms=2500):
        self._toast.set_label(message)
        self._toast_box.set_visible(True)
        GLib.timeout_add(duration_ms, self._hide_toast)

    def _hide_toast(self):
        self._toast_box.set_visible(False)
        return False

    def refresh(self):
        self._rebuild()

    def _rebuild(self):
        """Clear and repopulate the FlowBox."""
        # GTK4: remove all children
        child = self._flowbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._flowbox.remove(child)
            child = next_child

        self._cards.clear()

        for app in self._registry.get_all():
            card = AppCard(app)
            self._flowbox.append(card)
            self._cards[app.id] = card

    def _on_child_activated(self, flowbox, child):
        """Emit app-launch when tapped, but skip if a drag is active."""
        # child is the FlowBoxChild, get the AppCard inside
        widget = child.get_child()
        if isinstance(widget, AppCard):
            # Anti-launch-during-drag: skip activation while dragging
            if widget.drag_active:
                logger.debug("Skipping launch for %s — drag in progress", widget.app.id)
                return
            self.emit("app-launch", widget.app.id)

    def _handle_drop(self, dragged_id, target_id):
        logger.info("Drag-drop reorder: %s ↔ %s", dragged_id, target_id)
        all_apps = self._registry.get_all()
        ids = [a.id for a in all_apps]
        if dragged_id not in ids or target_id not in ids or dragged_id == target_id:
            return

        ids.remove(dragged_id)
        target_idx = ids.index(target_id)
        ids.insert(target_idx, dragged_id)

        self._registry.save_order(ids)
        self._rebuild()
