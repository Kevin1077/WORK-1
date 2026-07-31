# WhatsApp Desktop migration

The application no longer uses Selenium, Chrome, ChromeDriver, WhatsApp Web, or browser automation.

Receipt and ready-order actions now use Windows UI Automation against WhatsApp Desktop. They open the customer chat, attach the receipt where applicable, and paste the prepared message. The cashier reviews it and presses **Send**.

## Prerequisites

- Windows 10/11
- WhatsApp Desktop installed and logged in
- `pip install -r requirements.txt`

## Operational notes

- Search works best when the customer phone is stored with its country code. Ten-digit numbers are treated as Indian mobile numbers.
- WhatsApp Desktop's UI language should be English for the `Attach`, `Document`, and `Open` control names used by UIA.
- The three-second target applies when WhatsApp Desktop is already running and logged in. A cold app launch or first WhatsApp sign-in can take longer.
- The automation intentionally never sends automatically.

## Removed browser dependencies

`selenium` and `webdriver-manager` were removed from `requirements.txt`; no browser, driver, or Web session is launched by this integration.
