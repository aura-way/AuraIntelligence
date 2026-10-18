import flet as ft


def check_pylolm() -> str:
    try:
        import pylolm

        version = getattr(pylolm, "__version__", "unknown")

        from pylolm import _lib

        _lib.load()

        return f"SUCCESS!\npylolm {version} loaded successfully."

    except Exception as exc:
        return (
            "PYLOLM TEST FAILED\n\n"
            f"Error type: {type(exc).__name__}\n"
            f"Error: {exc}"
        )


def main(page: ft.Page):
    page.title = "pylolm Android Test"

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "pylolm Android Compatibility Test",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        check_pylolm(),
                        selectable=True,
                    ),
                ],
                spacing=20,
            )
        )
    )


ft.run(main)
