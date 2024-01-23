"""
Module for the Settings dialog class.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Burger
"""

from pyleco_extras.gui_utils.base_settings import BaseSettings


class Settings(BaseSettings):
    """Define the settings dialog and its methods."""

    def setup_form(self, layout) -> None:
        self.create_file_dialog("")
