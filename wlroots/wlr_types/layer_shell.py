# Copyright (c) Ruben Ruiz & Joshua Ryon 2020

import enum
import weakref
from typing import Callable, Optional, Tuple, TypeVar

from pywayland.server import Display, Signal

from wlroots import ffi, lib
from wlroots.util.edges import Edges
from .box import Box
from .output import Output
from .surface import Surface

@ffi.def_extern()
def surface_iterator_callback(surface_ptr, sx, sy, data_ptr):
    """Callback used to invoke the for_each_surface method"""
    func, py_data = ffi.from_handle(data_ptr)
    surface = Surface(surface_ptr)
    func(surface, sx, sy, py_data)

class LayerShell:
    def __init__(self, display: Display) -> None:
        """Create the shell for Graphical Elements

        :param display:
            The Wayland server display to create the shell on.
        """
        self._ptr = lib.wlr_layer_shell_v1_create(display._ptr)

        self.new_surface_event = Signal(
            ptr=ffi.addressof(self._ptr.events.new_surface), data_wrapper=LayerSurface
        )
        self.destroy_event = Signal(ptr=ffi.addressof(self._ptr.events.destroy))

class LayerSurface:
    def __init__(self, ptr) -> None:
        """A user interface element requiring management by the compositor

        """
        self._ptr = ffi.cast("struct wlr_layer_surface_v1 *", ptr)
        # lib.wlr_layer_surface_configure(self._ptr,40,40)
        self.map_event = Signal(ptr=ffi.addressof(self._ptr.events.map))
        self.unmap_event = Signal(ptr=ffi.addressof(self._ptr.events.unmap))
        self.destroy_event = Signal(ptr=ffi.addressof(self._ptr.events.destroy))
        self.new_popup_event = Signal(ptr=ffi.addressof(self._ptr.events.new_popup))

    @classmethod
    def from_surface(cls, surface: Surface):
        """Get the layer surface associated with the given surface"""
        surface_ptr = lib.wlr_layer_surface_v1_from_wlr_surface(surface._ptr)
        return LayerSurface(surface_ptr)

    @property
    def surface(self):
        """The surface associated with the layer surface"""
        return Surface(self._ptr.surface)

    def surface_at(
        self, surface_x: float, surface_y: float
    ) -> Tuple[Optional[Surface], float, float]:
        """Find a surface within this xdg-surface tree at the given surface-local coordinates

        Returns the surface and coordinates in the leaf surface coordinate
        system or None if no surface is found at that location.
        """
        sub_x_data = ffi.new("double*")
        sub_y_data = ffi.new("double*")
        surface_ptr = lib.wlr_layer_surface_v1_surface_at(
            self._ptr, surface_x, surface_y, sub_x_data, sub_y_data
        )
        if surface_ptr == ffi.NULL:
            return None, 0.0, 0.0

        return Surface(surface_ptr), sub_x_data[0], sub_y_data[0]

    def for_each_surface(self, iterator, data = None):
        """Call iterator on each surface and popup in the xdg-surface tree

        Call `iterator` on each surface and popup in the xdg-surface tree, with
        the surface's position relative to the root xdg-surface. The function
        is called from root to leaves (in rendering order).

        :param iterator:
            The method that should be invoked
        :param data:
            The data that is passed as the last argument to the iterator method
        """
        py_handle = (iterator, data)
        handle = ffi.new_handle(py_handle)
        lib.wlr_layer_surface_v1_for_each_surface(self._ptr, lib.surface_iterator_callback, handle)