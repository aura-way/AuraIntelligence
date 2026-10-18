"""AuraIntelligence demo: offline streaming chat with pylolm inside a Flet app.

Flow: tap "Choose model" -> pick a .gguf file -> chat. Generation runs on a worker thread and
text is streamed into the UI; "Stop" cancels it.
"""

import asyncio
import os
import platform
import time

import flet as ft

# Palette: dark navy + cyan.
BG = "#0B1220"
SURFACE = "#111B2E"
USER_BUBBLE = "#0E7490"
BOT_BUBBLE = "#16233B"
CYAN = "#22D3EE"
MUTED = "#8FA3BF"
DANGER = "#F87171"

SYSTEM_PROMPT = (
    "You are AuraIntelligence, a helpful offline assistant. Reply in the same language the user "
    "writes in. Keep answers short and in plain text, without markdown or formulas."
)
HISTORY_LIMIT = 12  # most recent messages sent to the model
UI_REFRESH_SECONDS = 0.08  # how often streamed text is pushed to the screen


def diagnostics() -> str:
    lines = [
        "python %s on %s" % (platform.python_version(), platform.machine()),
        "ANDROID_NATIVE_LIBRARY_DIR=%s" % os.environ.get("ANDROID_NATIVE_LIBRARY_DIR"),
    ]
    try:
        from pylolm import __version__, _lib

        _lib.load()
        where = _lib.loaded_dir() or "system library path"
        lines.append("pylolm %s: native libraries OK (%s)" % (__version__, where))
    except Exception as exc:  # show anything that goes wrong instead of crashing the app
        lines.append("pylolm native libraries: FAILED\n%s" % exc)
    return "\n".join(lines)


async def main(page: ft.Page):
    page.title = "AuraIntelligence"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0

    state = {"llm": None, "busy": False, "history": []}

    status = ft.Text("Choose a model (.gguf) to begin.", size=13, color=MUTED)
    progress = ft.ProgressBar(visible=False, color=CYAN)
    chat = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=16)
    box = ft.TextField(
        hint_text="Type a message",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=4,
        border_radius=28,
        filled=True,
        bgcolor=SURFACE,
        border_color=SURFACE,
        focused_border_color=CYAN,
        content_padding=16,
    )

    def add_bubble(text: str, mine: bool, color: str = None):
        label = ft.Text(text, selectable=True, size=16, color=color)
        bubble = ft.Container(
            content=label,
            padding=14,
            border_radius=24,
            bgcolor=USER_BUBBLE if mine else BOT_BUBBLE,
        )
        row = ft.Row(
            controls=[bubble],
            alignment=ft.MainAxisAlignment.END if mine else ft.MainAxisAlignment.START,
        )
        chat.controls.append(row)
        page.update()
        return label

    def set_status(message: str, error: bool = False):
        status.value = message
        status.color = DANGER if error else MUTED
        page.update()

    def set_busy(busy: bool):
        state["busy"] = busy
        send_button.disabled = busy
        stop_button.visible = busy
        progress.visible = busy
        page.update()

    async def load_model(path: str):
        set_status("Loading model...")
        progress.visible = True
        page.update()
        old = state["llm"]
        state["llm"] = None
        if old is not None:
            old.close()
        try:
            from pylolm import Llama

            # Loading blocks for several seconds, so keep it off the UI thread.
            llm = await asyncio.to_thread(Llama, path, n_ctx=2048)
        except Exception as exc:
            progress.visible = False
            set_status("Could not load the model:\n%s" % exc, error=True)
            return
        progress.visible = False
        state["llm"] = llm
        state["history"] = []
        set_status("Ready: %s" % os.path.basename(path))

    async def pick_model(e):
        files = await ft.FilePicker().pick_files(allow_multiple=False)
        if not files:
            return
        path = files[0].path
        if not path:
            set_status("The file picker did not return a file path.", error=True)
            return
        await load_model(path)

    async def send(e):
        llm = state["llm"]
        if llm is None:
            set_status("Choose a model first.", error=True)
            return
        text = (box.value or "").strip()
        if state["busy"] or not text:
            return
        box.value = ""
        history = state["history"]
        history.append({"role": "user", "content": text})
        add_bubble(text, mine=True)
        reply_label = add_bubble("...", mine=False)
        set_busy(True)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        done = object()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-HISTORY_LIMIT:]

        def worker():
            try:
                for chunk in llm.create_chat_completion(
                    messages, stream=True, max_tokens=768, temperature=0.7
                ):
                    piece = chunk["choices"][0]["delta"].get("content")
                    if piece:
                        loop.call_soon_threadsafe(queue.put_nowait, piece)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, done)

        future = loop.run_in_executor(None, worker)
        parts = []
        error = None
        last_refresh = 0.0
        while True:
            item = await queue.get()
            if item is done:
                break
            if isinstance(item, Exception):
                error = item
                continue
            parts.append(item)
            now = time.monotonic()
            if now - last_refresh >= UI_REFRESH_SECONDS:
                reply_label.value = "".join(parts)
                page.update()
                last_refresh = now
        await future

        reply = "".join(parts)
        if error is not None:
            reply_label.value = (reply + "\n\n" if reply else "") + "Error: %s" % error
            reply_label.color = DANGER
            if type(error).__name__ == "ContextOverflowError":
                state["history"] = history[-1:]  # conversation too long: start fresh
        else:
            reply_label.value = reply or "(no reply)"
            history.append({"role": "assistant", "content": reply})
        set_busy(False)

    def stop(e):
        if state["llm"] is not None:
            state["llm"].stop()

    def show_diagnostics(e):
        add_bubble(diagnostics(), mine=False, color=MUTED)

    send_button = ft.IconButton(
        icon=ft.Icons.SEND, icon_color=BG, bgcolor=CYAN, icon_size=26, on_click=send
    )
    stop_button = ft.IconButton(
        icon=ft.Icons.STOP, icon_color=BG, bgcolor=DANGER, icon_size=26, on_click=stop, visible=False
    )

    header = ft.Container(
        padding=16,
        bgcolor=SURFACE,
        border_radius=28,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text("AuraIntelligence", size=22, weight=ft.FontWeight.W_600, color=CYAN),
                status,
                ft.Row(
                    controls=[
                        ft.Button(content="Choose model", icon=ft.Icons.FOLDER_OPEN, on_click=pick_model),
                        ft.Button(content="Diagnostics", icon=ft.Icons.INFO_OUTLINE, on_click=show_diagnostics),
                    ],
                    wrap=True,
                ),
            ],
        ),
    )

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    header,
                    progress,
                    chat,
                    ft.Container(
                        padding=12,
                        content=ft.Row(controls=[box, send_button, stop_button], spacing=8),
                    ),
                ],
            ),
        )
    )

    # Tell the user right away if the native libraries are missing.
    report = diagnostics()
    if "FAILED" in report:
        add_bubble(report, mine=False, color=DANGER)


ft.run(main)
        
