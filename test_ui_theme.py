"""
test_ui_theme.py — Comprehensive test for UI theme, branding, and frame initialization.
"""
import unittest
import tkinter as tk

from database import init_db
from ui.theme import COLORS, SHOP_NAME, SHOP_TAGLINE, SHOP_FULL_TITLE
from ui.app_window import AppWindow


class TestUITheme(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.root = tk.Tk()
        cls.root.withdraw()  # keep hidden during tests
        cls.app = AppWindow(cls.root)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_theme_constants(self):
        """Verify theme constants match the Étoffe off-white + gold brand."""
        self.assertEqual(SHOP_NAME, "ÉTOFFE LAUNDRY")
        self.assertEqual(SHOP_TAGLINE, "Management System")
        self.assertEqual(SHOP_FULL_TITLE, "ÉTOFFE LAUNDRY MANAGEMENT SYSTEM")
        self.assertEqual(COLORS["bg"], "#F7F4EE")
        self.assertEqual(COLORS["sidebar_bg"], "#EFEAE1")
        self.assertEqual(COLORS["accent"], "#C9A84E")
        self.assertEqual(COLORS["text"], "#242424")

    def test_window_title(self):
        """Verify application title has the Étoffe brand."""
        self.assertIn("Étoffe Laundry", self.root.title())

    def test_all_frames_instantiation_and_refresh(self):
        """Verify all frames can be instantiated, displayed, and refreshed without errors."""
        frames = [
            "dashboard",
            "new_order",
            "search",
            "date_records",
            "progress",
            "all_orders",
            "customers",
            "price_list",
            "print_settings",
        ]
        for frame_name in frames:
            self.app.show_frame(frame_name)
            self.assertIn(frame_name, self.app.frames)
            frame = self.app.frames[frame_name]
            self.assertTrue(frame.winfo_exists())
            if hasattr(frame, "refresh"):
                frame.refresh()


if __name__ == "__main__":
    unittest.main()
