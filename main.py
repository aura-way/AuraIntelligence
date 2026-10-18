import flet as ft


def check_pylolm() -> str:
    try:
        import pylolm
        from pylolm import _lib

        _lib.load()
        return "pylolm %s OK" % pylolm.__version__
    except Exception as exc:
        return "pylolm FAILED: %s" % exc


def main(page: ft.Page):
    page.add(ft.SafeArea(content=ft.Text(check_pylolm(), selectable=True)))


ft.run(main)
