"""WhatsApp Web automation via Playwright.

Automatically opens customer chats, attaches PDF receipts, and pre-fills messages
so the staff member only needs to click 'Send'.

Uses a persistent browser profile so the QR code login is only needed once.
"""
from __future__ import annotations

import logging
import re
import time
import urllib.parse
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

# Persistent Chromium profile — WhatsApp Web login survives app restarts.
_PROFILE_DIR = Path.home() / ".victory_laundry_wa_profile"

# Timeouts (milliseconds)
_LOGIN_CHECK_MS  = 6_000    # how long to wait to detect chat list on startup
_QR_WAIT_MS      = 120_000  # 2 min for user to scan QR code
_CHAT_LOAD_MS    = 25_000   # chat must open after URL navigation
_ATTACH_READY_MS = 10_000   # wait for attachment preview after upload

# Selectors — ordered for resilience against WhatsApp Web DOM updates
_SEL_CHAT_SIDE = (
    "[data-testid='chat-list'],"
    "div[aria-label='Chat list'],"
    "div[aria-label='Chats'],"
    "#pane-side"
)
_SEL_COMPOSER = (
    "footer div[contenteditable='true'],"
    "div[data-testid='conversation-compose-box-input'],"
    "div[contenteditable='true'][data-tab='10']"
)
_SEL_ATTACH_BTN = (
    "span[data-icon='plus'],"
    "span[data-icon='attach-menu-plus'],"
    "button[aria-label='Attach'],"
    "button[title='Attach']"
)
_SEL_ATTACH_PREVIEW = (
    "div[data-testid='media-caption-input'],"   # image/video caption box
    "div[data-testid='document-thumb'],"         # document thumbnail
    "span[data-testid='document-detail'],"       # document name label
    "div[data-testid='upload-progress'],"        # upload in progress
    "span[data-icon='send']"                     # send button on preview
)
_SEL_QR = "canvas, div[data-ref], [data-testid='qrcode']"


# ── Custom exceptions ──────────────────────────────────────────────────────────

class WhatsAppWebError(RuntimeError):
    """Base class for WhatsApp Web automation failures."""


class PhoneNumberError(WhatsAppWebError):
    """The phone number cannot be used."""


class QRScanTimeout(WhatsAppWebError):
    """QR scan timed out — user did not log in within 2 minutes."""


class ChatLoadError(WhatsAppWebError):
    """Chat window did not load in time."""


# ── Phone / file helpers ───────────────────────────────────────────────────────

def _normalise_phone(phone_number: str) -> str:
    raw = str(phone_number or "").strip()
    digits = "".join(re.findall(r"\d", raw))
    if raw.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10:
        digits = "91" + digits
    if not 8 <= len(digits) <= 15:
        raise PhoneNumberError(
            "Enter a valid WhatsApp number with country code, "
            "or a 10-digit Indian mobile number."
        )
    return digits


def _validate_pdf(pdf_path: str) -> Path:
    path = Path(pdf_path).expanduser().resolve()
    if path.suffix.lower() != ".pdf":
        raise WhatsAppWebError("The receipt must be a PDF file.")
    if not path.is_file():
        raise WhatsAppWebError(f"Receipt PDF not found: {path}")
    return path


# ── Playwright Lifecycle ───────────────────────────────────────────────────────

_context = None   # playwright BrowserContext (persistent)
_playwright = None


def _get_context():
    """Return (or create) the long-lived persistent Playwright context."""
    global _context, _playwright

    if _context is not None:
        try:
            if not _context.is_closed():
                _ = _context.pages  # raises if the browser process has died
                return _context
            else:
                LOGGER.debug("Previous browser context was closed — restarting driver.")
                _context = None
                if _playwright is not None:
                    try:
                        _playwright.stop()
                    except Exception:
                        pass
                    _playwright = None
        except Exception:
            LOGGER.debug("Previous browser context is dead — restarting driver.")
            _context = None
            if _playwright is not None:
                try:
                    _playwright.stop()
                except Exception:
                    pass
                _playwright = None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise WhatsAppWebError(
            "Playwright is not installed.\n\n"
            "Run:  pip install playwright\n"
            "Then: playwright install chromium"
        ) from exc

    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Launching persistent profile at %s", _PROFILE_DIR)

    if _playwright is None:
        _playwright = sync_playwright().start()

    launch_args = {
        "user_data_dir": str(_PROFILE_DIR),
        "headless": False,
        "slow_mo": 0,
        "args": [
            "--disable-notifications",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        "no_viewport": True,
        "ignore_default_args": ["--enable-automation"],
    }

    try:
        try:
            ctx = _playwright.chromium.launch_persistent_context(
                channel="chrome",
                **launch_args
            )
        except Exception:
            LOGGER.info("System Chrome launch failed, using bundled Chromium.")
            ctx = _playwright.chromium.launch_persistent_context(
                **launch_args
            )
    except Exception as exc:
        LOGGER.warning("Failed to launch context with existing playwright driver, restarting driver: %s", exc)
        try:
            _playwright.stop()
        except Exception:
            pass
        _playwright = sync_playwright().start()
        try:
            ctx = _playwright.chromium.launch_persistent_context(
                channel="chrome",
                **launch_args
            )
        except Exception:
            ctx = _playwright.chromium.launch_persistent_context(
                **launch_args
            )

    _context = ctx
    return ctx


def _get_page():
    """Return the WhatsApp Web page, reusing an existing tab if possible."""
    ctx = _get_context()
    try:
        for page in ctx.pages:
            if not page.is_closed() and "web.whatsapp.com" in page.url:
                try:
                    page.bring_to_front()
                except Exception:
                    pass
                return page
        page = ctx.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page
    except Exception as exc:
        LOGGER.warning("Error getting page from context, retrying with fresh context: %s", exc)
        global _context
        _context = None
        ctx = _get_context()
        page = ctx.new_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page





# ── Login / QR handling ────────────────────────────────────────────────────────

def _ensure_logged_in(page) -> None:
    """Block until WhatsApp Web shows the chat list (logged in) or QR code."""
    if "web.whatsapp.com" not in page.url:
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

    # Cold load check: wait up to 25s for either chat list OR QR code to appear
    combined_sel = f"{_SEL_CHAT_SIDE}, {_SEL_QR}"
    try:
        page.wait_for_selector(combined_sel, timeout=25_000)
        # Check if chat list is visible (already logged in)
        if page.query_selector(_SEL_CHAT_SIDE):
            LOGGER.debug("WhatsApp Web: already logged in.")
            return
    except Exception:
        pass

    # If chat list is not visible, QR scan is required.
    LOGGER.info("WhatsApp Web: QR scan required.")
    _show_qr_dialog()

    try:
        page.wait_for_selector(_SEL_CHAT_SIDE, timeout=_QR_WAIT_MS)
        LOGGER.info("WhatsApp Web: login confirmed.")
    except Exception as exc:
        raise QRScanTimeout(
            "WhatsApp Web login timed out after 2 minutes.\n"
            "Please scan the QR code in the browser window."
        ) from exc


def _show_qr_dialog() -> None:
    """Show a Tkinter info dialog so staff know to scan the QR code once."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()
        messagebox.showinfo(
            "WhatsApp Web — Initial Login Required",
            "A browser window has opened for WhatsApp Web.\n\n"
            "Please scan the QR code with your phone to log in.\n\n"
            "This is ONLY needed ONCE — your session will stay logged in permanently.\n\n"
            "Click OK after you see your chat list.",
            parent=root,
        )
    except Exception as exc:
        LOGGER.warning("Could not show QR dialog: %s", exc)


# ── Core actions ───────────────────────────────────────────────────────────────

def _open_chat_url(page, phone: str, text: str = "") -> None:
    """Navigate directly to WhatsApp Web chat for a phone number."""
    encoded_text = urllib.parse.quote(text, safe="")
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
    LOGGER.debug("Navigating to %s", url)
    page.goto(url, wait_until="domcontentloaded")

    try:
        page.wait_for_selector(_SEL_COMPOSER, timeout=_CHAT_LOAD_MS)
    except Exception as exc:
        raise ChatLoadError(
            f"Chat for +{phone} did not load within "
            f"{_CHAT_LOAD_MS // 1000}s — check the phone number and internet connection."
        ) from exc


def _attach_pdf(page, pdf_path: Path) -> None:
    """Attach a PDF document into WhatsApp Web using the Document attachment input."""
    attached = False

    # Ensure composer is ready
    try:
        page.wait_for_selector(_SEL_COMPOSER, timeout=5_000)
    except Exception:
        pass

    # Method 1: Click Attach '+' menu -> 'Document' using Playwright file_chooser
    try:
        LOGGER.debug("Attempting Document attachment via Attach menu...")
        attach_btn = page.wait_for_selector(_SEL_ATTACH_BTN, timeout=5_000)
        if attach_btn:
            attach_btn.click()
            page.wait_for_timeout(500)

            doc_option_sel = (
                "span[data-icon='attach-document'],"
                "li[data-testid='attach-document'],"
                "div[aria-label='Document'],"
                "button[aria-label='Document'],"
                "div[data-testid='attach-document'],"
                "li:has-text('Document')"
            )
            doc_option = page.wait_for_selector(doc_option_sel, timeout=5_000)
            if doc_option:
                with page.expect_file_chooser(timeout=7_000) as fc_info:
                    doc_option.click()
                file_chooser = fc_info.value
                file_chooser.set_files(str(pdf_path))
                LOGGER.info("Successfully attached PDF via Document file chooser.")
                attached = True
    except Exception as exc:
        LOGGER.debug("File chooser attachment method failed, trying strict DOM document input targeting: %s", exc)

    # Method 2 (Fallback): Target ONLY document-specific <input type="file"> element (accept="*")
    if not attached:
        try:
            # Wait for any file input that accepts documents (* or pdf) and NOT restricted to image/video
            page.wait_for_timeout(500)
            inputs = page.query_selector_all('input[type="file"]')
            target_input = None

            for inp in inputs:
                accept = (inp.get_attribute("accept") or "").lower()
                # Strictly exclude image, video, and audio inputs
                if "image" not in accept and "video" not in accept and "audio" not in accept:
                    target_input = inp
                    break

            if target_input:
                page.evaluate("""
                    (el) => {
                        el.style.cssText = 'display:block!important;opacity:1!important;visibility:visible!important;';
                    }
                """, target_input)
                target_input.set_input_files(str(pdf_path))
                LOGGER.info("Attached PDF via direct DOM document input element targeting.")
                attached = True
            else:
                # Retry by opening attach menu once more
                LOGGER.debug("No document input found, opening attach menu again...")
                attach_btn = page.query_selector(_SEL_ATTACH_BTN)
                if attach_btn:
                    attach_btn.click()
                    page.wait_for_timeout(600)
                    doc_btn = page.query_selector("span[data-icon='attach-document'], button[aria-label='Document'], li:has-text('Document')")
                    if doc_btn:
                        with page.expect_file_chooser(timeout=5_000) as fc_info:
                            doc_btn.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(str(pdf_path))
                        attached = True

            if not attached:
                raise WhatsAppWebError("Could not locate Document file input in WhatsApp Web.")
        except Exception as exc:
            raise WhatsAppWebError(f"Could not attach receipt PDF: {exc}") from exc

    # Wait for attachment preview screen to appear
    try:
        page.wait_for_selector(_SEL_ATTACH_PREVIEW, timeout=_ATTACH_READY_MS)
        LOGGER.debug("Attachment preview visible.")
    except Exception:
        LOGGER.debug("Attachment preview loading slowly — please verify before pressing Send.")

    try:
        page.bring_to_front()
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────────

def send_receipt(phone_number: str, pdf_path: str, message: str) -> None:
    """Open WhatsApp Web chat for phone_number, attach pdf_path,
    and pre-fill message.

    Leaves the chat open with text and PDF attached.
    Staff only needs to click 'Send'.
    """
    t0 = time.perf_counter()
    phone   = _normalise_phone(phone_number)
    receipt = _validate_pdf(pdf_path)

    try:
        page = _get_page()
        _ensure_logged_in(page)
        _open_chat_url(page, phone, message)
        _attach_pdf(page, receipt)
    except Exception as exc:
        if "closed" in str(exc).lower():
            raise WhatsAppWebError("The browser tab was closed before the operation could finish.") from exc
        raise

    LOGGER.info("WhatsApp receipt prepared & attached in %.2fs", time.perf_counter() - t0)


def prepare_message(phone_number: str, message: str) -> None:
    """Open WhatsApp Web chat for phone_number and pre-fill message. No file attached.

    Leaves the chat open with text pre-filled.
    Staff only needs to click 'Send'.
    """
    t0 = time.perf_counter()
    phone = _normalise_phone(phone_number)

    try:
        page = _get_page()
        _ensure_logged_in(page)
        _open_chat_url(page, phone, message)

        try:
            page.bring_to_front()
        except Exception:
            pass
    except Exception as exc:
        if "closed" in str(exc).lower():
            raise WhatsAppWebError("The browser tab was closed before the operation could finish.") from exc
        raise

    LOGGER.info("WhatsApp message prepared in %.2fs", time.perf_counter() - t0)
