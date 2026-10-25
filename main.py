import asyncio
import os
import flet as ft
import app


async def main(page: ft.Page):
    # ==================================================
    # PAGE CONFIGURATION
    # ==================================================

    page.title = "AuraIntelligence"
    page.padding = 10
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_900
    )
    page.scroll = ft.ScrollMode.AUTO

    # ==================================================
    # LOCAL STORAGE
    # ==================================================

    storage = ft.SharedPreferences()

    theme = await storage.get("theme_mode") or "SYSTEM"
    system_message = await storage.get("sys_message") or ""

    page.theme_mode = theme

    # ==================================================
    # PAGE NAVIGATION
    # ==================================================

    async def show_drawer(e=None):
        await page.show_drawer()

    async def drawer_click(e: ft.Event[ft.NavigationDrawer]):
        await page.close_drawer()

        if e.control.selected_index == 0:
            app.change_page(
                e,
                sett_page,
                chat_page,
                bottom_cont,
                page,
                chat_page,
            )
        else:
            app.change_page(
                e,
                chat_page,
                sett_page,
                bottom_cont,
                page,
                chat_page,
            )

    async def theme_change(e):
        page.theme_mode = e.control.value

        await storage.set(
            "theme_mode",
            e.control.value,
        )

        page.update()

    async def open_link(e, link):
        await ft.UrlLauncher().launch_url(link)

    # ==================================================
    # NAVIGATION DRAWER
    # ==================================================

    page.drawer = ft.NavigationDrawer(
        on_change=drawer_click,
        width=250,
        controls=[
            ft.Container(
                content=ft.Text(
                    "AuraIntelligence",
                    size=25,
                    weight=ft.FontWeight.W_100,
                    italic=True,
                ),
                padding=20,
            ),

            ft.NavigationDrawerDestination(
                label="Chat",
                icon=ft.Icons.CHAT,
            ),

            ft.NavigationDrawerDestination(
                label="Settings",
                icon=ft.Icons.SETTINGS,
            ),
        ],
    )

    # ==================================================
    # GENERATION SETTINGS
    # ==================================================

    gen_sett = ft.BottomSheet(
        fullscreen=True,
        show_drag_handle=True,
        content=ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Generation Settings",
                        size=25,
                        weight=ft.FontWeight.BOLD,
                    ),

                    ft.Column(
                        controls=[
                            ft.Text(
                                "Creativity",
                                size=20,
                            ),

                            ft.Text(
                                "Choose how creative AI will be.",
                                color=ft.Colors.SECONDARY,
                            ),

                            ft.SegmentedButton(
                                selected=["normal"],
                                segments=[
                                    ft.Segment(
                                        value="creative",
                                        label="Creative",
                                    ),

                                    ft.Segment(
                                        value="normal",
                                        label="Normal",
                                    ),

                                    ft.Segment(
                                        value="predictable",
                                        label="Predictable",
                                    ),
                                ],
                                allow_empty_selection=False,
                            ),
                        ],
                        spacing=2,
                    ),
                ],
            ),
        ),
    )

    # ==================================================
    # APP BAR
    # ==================================================

    page.appbar = ft.AppBar(
        leading=ft.IconButton(
            ft.Icons.MENU,
            on_click=show_drawer,
        ),
        title_spacing=0,
        visible=False,
        force_material_transparency=True,
        actions=[
            new_chat_butt := ft.Button(
                "New Chat",
                icon=ft.Icons.ADD,
            ),

            ft.PopupMenuButton(
                key="popup",
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.AUTO_AWESOME
                                ),
                                ft.Text(
                                    "Generation Settings"
                                ),
                            ],
                        ),
                        on_click=lambda e: page.show_dialog(
                            gen_sett
                        ),
                    ),
                ],
            ),
        ],
    )

    # ==================================================
    # MODEL DOWNLOAD UI
    # ==================================================

    download_text = ft.Text(
        "Waiting to start",
        size=15,
    )

    download_prog = ft.ProgressBar(
        height=20,
        border_radius=30,
        value=0,
    )

    status_text = ft.Text(
        "Download the AI model to get started.",
        size=16,
        selectable=True,
    )

    # These references are resolved when the button is clicked.
    download_button = ft.OutlinedButton(
        "Download",
        icon=ft.Icons.DOWNLOAD,
        on_click=lambda e: page.run_task(
            app.download_model,
            download_prog,
            download_text,
            status_text,
            download_button,
            download_page,
            chat_page,
            bottom_cont,
            page,
        ),
    )

    download_page = ft.Container(
        content=ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.DOWNLOAD
                                ),

                                ft.Text(
                                    "Download AI model",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),

                        status_text,

                        ft.Divider(),

                        download_text,

                        download_prog,

                        download_button,
                    ],
                    spacing=10,
                ),
                padding=20,
            ),
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
        visible=False,
    )

    # ==================================================
    # CHAT INTRODUCTION
    # ==================================================
    intro = ft.Container(
        content=ft.Column(
            controls=[
                ft.Image(
                    src="assets/icon.png",
                    width=90,
                    height=90,
                    fit=ft.BoxFit.CONTAIN,
                ),

                ft.Text(
                    "Feel the Aura",
                    size=32,
                    weight=ft.FontWeight.W_300,
                    italic=True,
                ),
            ],
            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    # ==================================================
    # CHAT MESSAGES
    # ==================================================

    chats = ft.Column(
        controls=[intro],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=15,
        horizontal_alignment=(
            ft.CrossAxisAlignment.STRETCH
        ),
    )

    def intro_invisible():
        intro.visible = False

    def check_chats():
        if len(chats.controls) <= 1:
            intro.visible = True

    # ==================================================
    # MESSAGE INPUT
    # ==================================================

    def send_message(e):
        page.run_thread(
            app.send,
            e,
            page,
            inp,
            intro,
            chats,
        )

    bottom_cont_row = ft.Row(
        controls=[
            inp := ft.TextField(
                hint_text="Ask anything",
                multiline=True,
                min_lines=1,
                max_lines=3,
                expand=True,
                on_focus=lambda e: intro_invisible(),
                on_blur=lambda e: check_chats(),
                on_change=lambda e: intro_invisible(),
                border_color=ft.Colors.SECONDARY,
                filled=True,
                border_radius=20,
            ),

            ft.FilledIconButton(
                ft.Icons.SEND,
                on_click=send_message,
            ),
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    # Floating-style input container.
    # IMPORTANT: It is NOT absolutely positioned.
    bottom_cont = ft.Container(
        content=bottom_cont_row,
        padding=8,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=30,
        margin=ft.Margin(
            left=2,
            top=4,
            right=2,
            bottom=4,
        ),
        visible=False,
    )

    # ==================================================
    # CHAT PAGE
    # ==================================================

    chat_page = ft.Container(
        content=ft.Column(
            controls=[
                # Message area takes the available space.
                ft.Container(
                    content=chats,
                    expand=True,
                    padding=ft.Padding(
                        10,
                        10,
                        10,
                        10,
                    ),
                ),

                # Input stays inside the page layout.
                # SafeArea handles the system navigation area.
                ft.SafeArea(
                    content=bottom_cont,
                    avoid_intrusions_top=False,
                    avoid_intrusions_left=False,
                    avoid_intrusions_right=False,
                    avoid_intrusions_bottom=True,
                    maintain_bottom_view_padding=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        expand=True,
        visible=False,
        padding=0,
    )

    new_chat_butt.on_click = (
        lambda e: app.new_chat(
            e,
            chats,
            intro,
        )
    )

    # ==================================================
    # SETTINGS: THEME
    # ==================================================

    theme_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.DARK_MODE
                            ),

                            ft.Text(
                                "Theme",
                                size=24,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),

                    ft.Dropdown(
                        value=theme,
                        on_select=theme_change,
                        options=[
                            ft.dropdown.Option("SYSTEM"),
                            ft.dropdown.Option("LIGHT"),
                            ft.dropdown.Option("DARK"),
                        ],
                        border_color=ft.Colors.SECONDARY,
                    ),
                ],
                spacing=12,
            ),
            padding=20,
        ),
    )

    # ==================================================
    # SETTINGS: SYSTEM MESSAGE
    # ==================================================

    sys_message = ft.TextField(
        hint_text=(
            "Tell the AI how to respond "
            "or what context to use."
        ),
        multiline=True,
        max_lines=4,
        border_color=ft.Colors.SECONDARY,
        border_radius=20,
        value=system_message,
    )

    status_saved = ft.Text(
        size=13,
        color=ft.Colors.SECONDARY,
    )

    async def change_sys_message(e):
        value = sys_message.value or ""

        await storage.set(
            "sys_message",
            value,
        )

        app.SYSTEM_MESSAGE = (
            value.strip()
            or "You are AuraIntelligence, a helpful assistant."
        )

        app.reset_history()

        status_saved.value = (
            "System message saved. "
            "It will apply to new responses."
        )

        page.update()

    message_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.MEMORY
                            ),

                            ft.Text(
                                "System Message",
                                size=24,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),

                    sys_message,

                    ft.OutlinedButton(
                        "Save",
                        icon=ft.Icons.SAVE,
                        on_click=change_sys_message,
                    ),

                    status_saved,
                ],
                spacing=12,
            ),
            padding=20,
        ),
    )

    app.SYSTEM_MESSAGE = (
        system_message.strip()
        or "You are AuraIntelligence, a helpful assistant."
    )

    app.reset_history()

    # ==================================================
    # SETTINGS: ABOUT
    # ==================================================

    about_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.INFO
                            ),

                            ft.Text(
                                "About",
                                size=24,
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                    ),

                    ft.Markdown(
                        "**Version:** 0.1.0\n\n"
                        "**Contact and Feedback:** "
                        "auraway.dev@gmail.com\n\n"
                        "© 2026 [AuraWay]"
                        "(https://aura-way.github.io)",
                        selectable=True,
                        on_tap_link=lambda e: page.run_task(
                            open_link,
                            e,
                            e.data,
                        ),
                    ),
                ],
                spacing=12,
            ),
            padding=20,
        ),
    )

    # ==================================================
    # SETTINGS PAGE
    # ==================================================

    sett_page = ft.Container(
        content=ft.Column(
            controls=[
                theme_card,
                message_card,
                about_card,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        visible=False,
        expand=True,
    )

    # ==================================================
    # INITIALIZE APP
    # ==================================================

    page.add(
        download_page,
        chat_page,
        sett_page,
    )

    # ==================================================
    # LOAD EXISTING MODEL
    # ==================================================

    try:
        if (
            os.path.isfile(app.MODEL_PATH)
            and os.path.getsize(app.MODEL_PATH) > 0
        ):
            status_text.value = (
                "Model found. Loading…"
            )

            download_page.visible = True
            page.update()

            await asyncio.to_thread(
                app.load_model,
                app.MODEL_PATH,
            )

            download_page.visible = False
            chat_page.visible = True
            bottom_cont.visible = True
            page.appbar.visible = True

            status_text.value = "Model ready."

        else:
            download_page.visible = True
            chat_page.visible = False
            bottom_cont.visible = False

    except Exception as exc:
        print(
            f"Existing model could not be loaded: {exc}"
        )

        status_text.value = (
            f"The existing model could not be loaded: "
            f"{exc}. Download it again."
        )

        download_page.visible = True
        chat_page.visible = False
        bottom_cont.visible = False
        download_button.disabled = False

    page.update()


# ======================================================
# RUN APP
# ======================================================

if __name__ == "__main__":
    ft.run(main)
