"""Windows-native WhatsApp Desktop preparation via UI Automation (UIA).

The module intentionally never presses WhatsApp's Send button.  It prepares a
receipt or message for the operator to review and send.
"""
from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pyperclip
from pywinauto import Desktop, keyboard
from pywinauto.timings import TimeoutError as UIATimeoutError, wait_until_passes

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT_SECONDS = 3.0
COLD_START_TIMEOUT_SECONDS = 15.0


class WhatsAppDesktopError(RuntimeError):
    """Base class for WhatsApp Desktop automation failures."""


class PhoneNumberError(WhatsAppDesktopError):
    """The customer number cannot be used to search WhatsApp."""


class WhatsAppLaunchError(WhatsAppDesktopError):
    """WhatsApp Desktop could not be opened or found."""


class ChatNotFoundError(WhatsAppDesktopError):
    """The requested customer chat did not appear in the search results."""


class AttachmentError(WhatsAppDesktopError):
    """The receipt PDF could not be attached."""


@dataclass(frozen=True)
class _Timing:
    started: float

    def elapsed(self) -> float:
        return time.perf_counter() - self.started


def send_receipt(phone_number: str, pdf_path: str, message: str) -> None:
    """Prepare a WhatsApp Desktop receipt message with ``pdf_path`` attached.

    The message is left in WhatsApp's composer.  The cashier must press Send.
    """
    timing = _Timing(time.perf_counter())
    phone = _normalise_phone(phone_number)
    receipt = _validate_pdf(pdf_path)
    window = _main_window(timing)
    _open_chat(window, phone, timing)
    _attach_document(window, receipt, timing)
    _paste_message(window, message)
    LOGGER.info("WhatsApp receipt prepared in %.2fs", timing.elapsed())


def prepare_message(phone_number: str, message: str) -> None:
    """Open a customer chat and prefill a message without attaching a file."""
    timing = _Timing(time.perf_counter())
    window = _main_window(timing)
    _open_chat(window, _normalise_phone(phone_number), timing)
    _paste_message(window, message)
    LOGGER.info("WhatsApp notification prepared in %.2fs", timing.elapsed())


def _normalise_phone(phone_number: str) -> str:
    raw = str(phone_number or "").strip()
    digits = "".join(re.findall(r"\d", raw))
    if raw.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = "91" + digits
    if not 8 <= len(digits) <= 15:
        raise PhoneNumberError(
            "Enter a valid WhatsApp number with country code, or a 10-digit Indian mobile number."
        )
    return digits


def _validate_pdf(pdf_path: str) -> Path:
    path = Path(pdf_path).expanduser().resolve()
    if path.suffix.lower() != ".pdf":
        raise AttachmentError("The receipt must be a PDF file.")
    if not path.is_file():
        raise AttachmentError(f"Receipt PDF was not found: {path}")
    return path


def _main_window(timing: _Timing):
    """Connect to the existing main window or launch WhatsApp Desktop."""
    desktop = Desktop(backend="uia")
    window = _find_main_window(desktop)
    if window is None:
        launch_started = time.perf_counter()
        try:
            os.startfile("whatsapp:")
        except OSError as exc:
            raise WhatsAppLaunchError(
                "WhatsApp Desktop is not installed or its Windows app protocol is unavailable."
            ) from exc
        LOGGER.info("Requested WhatsApp Desktop launch in %.2fs", time.perf_counter() - launch_started)
        window = _wait_for(
            lambda: _find_main_window(desktop),
            "WhatsApp Desktop main window",
            timeout=COLD_START_TIMEOUT_SECONDS,
        )

    # `_find_main_window` has already confirmed this UIA window is visible.
    # Store/MSIX WhatsApp builds can report a disabled window forever while
    # their child UIA controls are usable, so do not reject it here.  Each
    # required child control has its own explicit wait below.
    try:
        window.set_focus()
    except Exception as exc:
        LOGGER.warning("Could not focus WhatsApp Desktop window: %s", exc)
    LOGGER.info("WhatsApp Desktop ready in %.2fs", timing.elapsed())
    return window


def _find_main_window(desktop):
    # Titles differ between Store, MSIX, and standalone builds.
    for candidate in desktop.windows():
        try:
            title = candidate.window_text().strip()
            if candidate.is_visible() and re.search(r"whatsapp", title, re.IGNORECASE):
                return candidate
        except Exception:
            continue
    return None


def _wait_for(factory: Callable[[], object], description: str,
              timeout: float = DEFAULT_TIMEOUT_SECONDS):
    """Return a UIA control using pywinauto's deadline-based explicit wait."""
    class _NotReady(Exception):
        pass

    def wait_attempt():
        try:
            value = factory()
            if value:
                return value
        except Exception as exc:
            raise _NotReady(str(exc)) from exc
        raise _NotReady()

    try:
        return wait_until_passes(
            timeout, 0.05, wait_attempt, exceptions=(_NotReady,)
        )
    except UIATimeoutError as exc:
        raise WhatsAppDesktopError(f"Timed out waiting for {description}.") from exc


def _open_chat(window, phone: str, timing: _Timing) -> None:
    search = _wait_for(lambda: _find_search_box(window), "WhatsApp search box")
    _paste_into(search, phone)

    def result():
        return _find_chat_result(window, phone)

    chat = _wait_for(result, f"customer chat for +{phone}")
    try:
        chat.click_input()
        # WhatsApp Desktop also supports Enter to confirm the highlighted
        # number-search result. This covers builds where the result is exposed
        # as a non-clickable UIA text child.
        keyboard.send_keys("{ENTER}")
    except Exception as exc:
        raise ChatNotFoundError(f"Could not open WhatsApp chat for +{phone}.") from exc
    LOGGER.info("WhatsApp chat opened in %.2fs", timing.elapsed())


def _find_search_box(window):
    edits = window.descendants(control_type="Edit")
    for edit in edits:
        try:
            name = edit.window_text().lower()
            if "search" in name or "new chat" in name:
                return edit
        except Exception:
            continue
    # Current WhatsApp Desktop normally has the search box as the first Edit.
    return edits[0] if edits else None


def _find_chat_result(window, phone: str):
    compact = phone[-10:]
    for control in window.descendants(control_type="ListItem"):
        try:
            name = re.sub(r"\D", "", control.window_text())
            if compact in name or phone in name:
                return control
        except Exception:
            continue
    # Some Desktop builds expose number-search results as a Button or Text
    # rather than a ListItem. Never inspect Edit controls here: the search box
    # itself contains the typed phone number and is not a result.
    for control in window.descendants():
        try:
            control_type = control.element_info.control_type
            if control_type not in {"Button", "Text", "Hyperlink"}:
                continue
            name = re.sub(r"\D", "", control.window_text())
            if compact in name or phone in name:
                return control
        except Exception:
            continue
    return None


def _attach_document(window, pdf_path: Path, timing: _Timing) -> None:
    try:
        attach = _wait_for(lambda: _find_attach_button(window), "WhatsApp Attach button")
        attach.click_input()
        document = _wait_for(lambda: _find_document_option(window), "WhatsApp Document option")
        document.click_input()
        _select_file(pdf_path)
    except Exception as primary_error:
        LOGGER.warning("UIA attachment path failed: %s", primary_error)
        try:
            _dismiss_file_dialog()
            window.set_focus()
            keyboard.send_keys("^o")
            _select_file(pdf_path)
        except Exception as fallback_error:
            LOGGER.warning("Ctrl+O attachment fallback failed: %s", fallback_error)
            try:
                _dismiss_file_dialog()
                _attach_via_clipboard(window, pdf_path)
            except Exception as clipboard_error:
                raise AttachmentError(
                    "Could not attach receipt PDF. "
                    f"UIA: {primary_error}; Ctrl+O: {fallback_error}; clipboard: {clipboard_error}"
                ) from clipboard_error
    LOGGER.info("Receipt attached in %.2fs", timing.elapsed())


def _find_attach_button(window):
    for control in window.descendants(control_type="Button"):
        try:
            name = control.window_text().lower()
            if any(word in name for word in ("attach", "add", "plus")):
                return control
        except Exception:
            continue
    return None


def _find_document_option(window):
    for control in window.descendants():
        try:
            if "document" in control.window_text().lower():
                return control
        except Exception:
            continue
    return None


def _select_file(pdf_path: Path) -> None:
    desktop = Desktop(backend="uia")

    def dialog():
        for candidate in desktop.windows():
            try:
                title = candidate.window_text()
                class_name = candidate.class_name()
                if candidate.is_visible() and (
                    class_name == "#32770"
                    or re.search(r"open|choose|select|file upload", title, re.I)
                ):
                    return candidate
            except Exception:
                continue
        return None

    picker = _wait_for(dialog, "Windows file picker")
    filename = None
    for edit in picker.descendants(control_type="Edit"):
        try:
            if "file name" in edit.window_text().lower():
                filename = edit
                break
        except Exception:
            continue
    if filename is None:
        edits = picker.descendants(control_type="Edit")
        filename = edits[-1] if edits else None
    if filename is None:
        raise AttachmentError("Windows file picker does not expose a File name field.")
    _paste_into(filename, str(pdf_path))

    for button in picker.descendants(control_type="Button"):
        try:
            if button.window_text().strip().lower() in {"open", "select"}:
                button.click_input()
                return
        except Exception:
            continue
    raise AttachmentError("Windows file picker does not expose its Open button.")


def _dismiss_file_dialog() -> None:
    """Close a stalled native file picker before attempting the next fallback."""
    try:
        keyboard.send_keys("{ESC}")
    except Exception:
        pass


def _attach_via_clipboard(window, pdf_path: Path) -> None:
    """Use the native CF_HDROP clipboard format as the final attachment fallback."""
    try:
        import win32clipboard
        import win32con
    except ImportError as exc:
        raise AttachmentError("pywin32 is required for the clipboard attachment fallback.") from exc

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, (str(pdf_path),))
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
    window.set_focus()
    keyboard.send_keys("^v")


def _paste_message(window, message: str) -> None:
    composer = _wait_for(lambda: _find_composer(window), "WhatsApp message composer")
    _paste_into(composer, message)


def _find_composer(window):
    edits = window.descendants(control_type="Edit")
    for edit in reversed(edits):
        try:
            name = edit.window_text().lower()
            if any(text in name for text in ("message", "type")):
                return edit
        except Exception:
            continue
    return edits[-1] if edits else None


def _paste_into(control, text: str) -> None:
    if not control:
        raise WhatsAppDesktopError("Required WhatsApp UI control was not found.")
    try:
        control.set_focus()
        pyperclip.copy(text)
        keyboard.send_keys("^v")
    except Exception as exc:
        raise WhatsAppDesktopError("Could not paste text into WhatsApp Desktop.") from exc
