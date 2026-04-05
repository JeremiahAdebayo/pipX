import flet as ft
from rates import get_rate
from calculator import (
    get_pip_value_per_std_lot,
    calculate_lot_sizes,
    price_to_pips,
)

PAIRS = [
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",   # USD-quoted (simplest)
    "USDJPY", "USDCHF", "USDCAD",              # USD-based
    "EURGBP", "EURJPY", "GBPJPY",              # crosses
    "XAUUSD", "XAGUSD",                        # metals
]

BG      = "#0D0D0D"
SURFACE = "#1A1A1A"
CARD    = "#222222"
ACCENT  = "#00C896"
MUTED   = "#888888"
WHITE   = "#F0F0F0"
RED     = "#FF4C4C"
YELLOW  = "#FFD166"


# ── helpers ───────────────────────────────────────────────────────────────────

def field(label, value="", hint="", keyboard=ft.KeyboardType.NUMBER):
    return ft.TextField(
        label=label,
        value=value,
        hint_text=hint,
        keyboard_type=keyboard,
        bgcolor=SURFACE,
        color=WHITE,
        label_style=ft.TextStyle(color=MUTED),
        border_color=MUTED,
        focused_border_color=ACCENT,
        cursor_color=ACCENT,
    )


def card(label: str, val_ref: ft.Ref, accent=False) -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Text(label, size=10, color=MUTED, weight=ft.FontWeight.W_500),
            ft.Text("—", size=20, color=ACCENT if accent else WHITE,
                    weight=ft.FontWeight.BOLD, ref=val_ref),
        ], spacing=4),
        bgcolor=CARD,
        border_radius=12,
        padding=ft.padding.all(14),
        expand=True,
        border=ft.border.all(1, ACCENT) if accent else None,
    )


def divider():
    return ft.Divider(color=SURFACE, height=20)


# ── splash screen ─────────────────────────────────────────────────────────────

def show_splash(page: ft.Page, on_done):
    splash = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(expand=True),
                ft.Text(
                    "LOT SIZE\nCALCULATOR",
                    size=34,
                    weight=ft.FontWeight.BOLD,
                    color=ACCENT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=12),
                ft.Text(
                    "Professional position sizing\nfor forex & metals",
                    size=14,
                    color=MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(expand=True),
                ft.Divider(color=SURFACE),
                ft.Container(height=10),
                ft.Text(
                    "Created by",
                    size=11,
                    color=MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=4),
                ft.Text(
                    "Jeremiah Adebayo",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "jrmhadebayo@gmail.com",
                    size=12,
                    color=ACCENT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=30),
                ft.ElevatedButton(
                    text="GET STARTED",
                    on_click=lambda e: on_done(),
                    bgcolor=ACCENT,
                    color=BG,
                    width=260,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        text_style=ft.TextStyle(
                            weight=ft.FontWeight.BOLD, size=15
                        ),
                    ),
                ),
                ft.Container(height=30),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=BG,
        expand=True,
        padding=ft.padding.all(30),
    )
    page.controls.clear()
    page.add(splash)
    page.update()


# ── main calculator UI ────────────────────────────────────────────────────────

def show_calculator(page: ft.Page):
    page.controls.clear()
    page.scroll = ft.ScrollMode.AUTO
    page.update()

    current_rate = {"value": None}

    # result refs
    ref_std       = ft.Ref[ft.Text]()
    ref_cent      = ft.Ref[ft.Text]()
    ref_mini      = ft.Ref[ft.Text]()
    ref_micro     = ft.Ref[ft.Text]()
    ref_units     = ft.Ref[ft.Text]()
    ref_pip_sz    = ft.Ref[ft.Text]()
    ref_eff_sl    = ft.Ref[ft.Text]()
    ref_check     = ft.Ref[ft.Text]()

    # inputs
    pair_dd = ft.Dropdown(
        label="Instrument",
        value="AUDUSD",
        options=[ft.dropdown.Option(p) for p in PAIRS],
        bgcolor=SURFACE,
        color=WHITE,
        label_style=ft.TextStyle(color=MUTED),
        border_color=ACCENT,
        focused_border_color=ACCENT,
    )

    rate_text  = ft.Text("Rate: —", size=13, color=ACCENT)
    rate_err   = ft.Text("", size=11, color=RED)

    # SL mode toggle
    sl_mode = ft.RadioGroup(
        value="pips",
        content=ft.Row([
            ft.Radio(value="pips",   label="SL in pips",
                     label_style=ft.TextStyle(color=WHITE)),
            ft.Radio(value="prices", label="Entry & SL price",
                     label_style=ft.TextStyle(color=WHITE)),
        ]),
    )

    sl_pips_field   = field("Stop loss (pips)", "20")
    entry_field     = field("Entry price", "0.71307", "e.g. 0.71307")
    sl_price_field  = field("SL price",    "0.72021", "e.g. 0.72021")
    spread_field    = field("Spread (pips) — optional", "0", "0")

    entry_field.visible    = False
    sl_price_field.visible = False

    def on_sl_mode(e):
        use_prices = sl_mode.value == "prices"
        sl_pips_field.visible  = not use_prices
        entry_field.visible    = use_prices
        sl_price_field.visible = use_prices
        page.update()

    sl_mode.on_change = on_sl_mode

    # risk mode
    risk_mode = ft.RadioGroup(
        value="fixed",
        content=ft.Row([
            ft.Radio(value="fixed", label="Fixed $",
                     label_style=ft.TextStyle(color=WHITE)),
            ft.Radio(value="pct",   label="% of balance",
                     label_style=ft.TextStyle(color=WHITE)),
        ]),
    )

    risk_field    = field("Risk amount ($)", "1")
    balance_field = field("Account balance ($)", "10000")
    pct_field     = field("Risk (%)", "1")
    balance_field.visible = False
    pct_field.visible     = False

    def on_risk_mode(e):
        is_pct = risk_mode.value == "pct"
        risk_field.visible    = not is_pct
        balance_field.visible = is_pct
        pct_field.visible     = is_pct
        page.update()

    risk_mode.on_change = on_risk_mode

    # fetch rate
    fetch_btn = ft.ElevatedButton(
        text="Fetch Rate",
        bgcolor=SURFACE,
        color=ACCENT,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            side=ft.BorderSide(1, ACCENT),
        ),
    )

    def fetch_rate(e):
        rate_text.value = "Fetching…"
        rate_err.value  = ""
        page.update()
        try:
            r = get_rate(pair_dd.value)
            current_rate["value"] = r
            rate_text.value = f"Rate: {r:.5f}"
            rate_text.color = ACCENT
        except Exception as ex:
            rate_text.value = "Rate: unavailable"
            rate_text.color = RED
            rate_err.value  = str(ex)
        page.update()

    fetch_btn.on_click = fetch_rate

    # calculate
    calc_err = ft.Text("", size=12, color=RED)

    def calculate(e):
        calc_err.value = ""
        rate = current_rate["value"]

        if rate is None:
            calc_err.value = "Tap 'Fetch Rate' first."
            page.update()
            return

        try:
            spread = float(spread_field.value or 0)

            # --- stop loss in pips ---
            if sl_mode.value == "prices":
                entry    = float(entry_field.value)
                sl_price = float(sl_price_field.value)
                sl_pips  = price_to_pips(pair_dd.value, entry, sl_price)
            else:
                sl_pips = float(sl_pips_field.value)

            # --- risk amount ---
            if risk_mode.value == "fixed":
                risk = float(risk_field.value)
            else:
                balance = float(balance_field.value)
                pct     = float(pct_field.value)
                risk    = balance * pct / 100

            pip_val = get_pip_value_per_std_lot(pair_dd.value, rate)
            result  = calculate_lot_sizes(risk, sl_pips, spread, pip_val)

            ref_std.current.value    = f"{result['standard']}"
            ref_cent.current.value   = f"{result['cent_lot']}"
            ref_mini.current.value   = f"{result['mini']}"
            ref_micro.current.value  = f"{result['micro']}"
            ref_units.current.value  = f"{result['units']:,}"
            ref_pip_sz.current.value = f"${pip_val:.4f}"
            ref_eff_sl.current.value = f"{result['effective_sl']} pips"
            ref_check.current.value  = f"${result['total_risk_check']}"

        except ValueError as ex:
            calc_err.value = str(ex)
        except Exception as ex:
            calc_err.value = f"Error: {ex}"

        page.update()

    calc_btn = ft.ElevatedButton(
        text="CALCULATE",
        on_click=calculate,
        bgcolor=ACCENT,
        color=BG,
        width=float("inf"),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=15),
        ),
    )

    page.add(
        ft.Text("LOT SIZE CALCULATOR", size=18, weight=ft.FontWeight.BOLD, color=ACCENT),
        ft.Text("by Jeremiah Adebayo", size=11, color=MUTED),
        divider(),

        # instrument + rate
        pair_dd,
        ft.Row([rate_text, ft.Container(expand=True), fetch_btn]),
        rate_err,
        divider(),

        # SL input mode
        ft.Text("Stop loss input", size=12, color=MUTED),
        sl_mode,
        sl_pips_field,
        entry_field,
        sl_price_field,
        spread_field,
        divider(),

        # risk
        ft.Text("Risk", size=12, color=MUTED),
        risk_mode,
        risk_field,
        balance_field,
        pct_field,
        ft.Container(height=8),

        calc_err,
        calc_btn,
        divider(),

        # results
        ft.Text("RESULTS", size=12, color=MUTED, weight=ft.FontWeight.W_500),
        ft.Container(height=6),

        ft.Row([
            card("Standard lot",      ref_std),
            card("Cent lot (MT4)",    ref_cent, accent=True),
        ], spacing=10),
        ft.Container(height=8),
        ft.Row([
            card("Mini lot",          ref_mini),
            card("Micro lot",         ref_micro),
        ], spacing=10),
        ft.Container(height=8),
        ft.Row([
            card("Units",             ref_units),
            card("Pip value / std",   ref_pip_sz),
        ], spacing=10),
        ft.Container(height=8),
        ft.Row([
            card("Effective SL",      ref_eff_sl),
            card("Risk check ($)",    ref_check),
        ], spacing=10),
        ft.Container(height=30),
    )
    page.update()


# ── entry point ───────────────────────────────────────────────────────────────

def build_ui(page: ft.Page):
    page.title   = "Lot Size Calculator"
    page.bgcolor = BG
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK
    show_splash(page, on_done=lambda: show_calculator(page))