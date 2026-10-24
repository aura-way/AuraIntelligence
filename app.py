import asyncio
import os
import queue
import requests
from dataclasses import field
import flet as ft
from pylolm import Llama

MODEL_URL = (
    "https://huggingface.co/tensorblock/SmolLM2-135M-Instruct-GGUF/"
    "resolve/main/SmolLM2-135M-Instruct-Q3_K_M.gguf?download=true"
)
MODEL_PATH = "auraintelligence.gguf"
llm = None
SYSTEM_MESSAGE = "You are AuraIntelligence, a helpful assistant."
history = []


def reset_history():
    global history
    history = [{"role": "system", "content": SYSTEM_MESSAGE}]


def load_model(path=MODEL_PATH):
    """Load the local GGUF model and store it in this module's shared state."""
    global llm
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        raise FileNotFoundError("The model file is missing or empty.")
    llm = Llama(path, n_ctx=2048)
    reset_history()
    return llm


async def copy(text):
    try:
        await ft.Clipboard().set(text)
    except Exception as exc:
        print(f"Clipboard error: {exc}")


async def share(text):
    try:
        await ft.Share().share_text(text)
    except Exception as exc:
        print(f"Share error: {exc}")


@ft.control
class Query(ft.Container):
    body: str = ""
    border_radius: ft.BorderRadius = field(
        default_factory=lambda: ft.BorderRadius.all(30)
    )
    align: ft.Alignment = field(
        default_factory=lambda: ft.Alignment.TOP_RIGHT
    )
    vertical_alignment: ft.CrossAxisAlignment = ft.CrossAxisAlignment.CENTER
    bgcolor: ft.Colors = ft.Colors.PRIMARY_CONTAINER
    padding: ft.PaddingValue = 15
    spacing: int = 0
    width: int = 220
    expand: bool = True
    expand_loose: bool = True

    async def copy_query(self, e):
        await copy(self.body)

    async def share_query(self, e):
        await share(self.body)

    def init(self):
        self.content = ft.Column(
            controls=[
                ft.Text(self.body, size=18, selectable=True),
                ft.Row(
                    controls=[
                        ft.IconButton(ft.Icons.COPY, on_click=self.copy_query),
                        ft.IconButton(ft.Icons.SHARE, on_click=self.share_query),
                    ],
                    tight=True,
                    spacing=0,
                ),
            ]
        )


@ft.control
class Ans(ft.Container):
    body: str = ""
    padding: ft.PaddingValue = 10

    async def copy_ans(self, e):
        await copy(self.body)

    async def share_ans(self, e):
        await share(self.body)

    def change_text(self, tx):
        self.body = tx
        self.content = ft.Column(
            controls=[
                ft.Markdown(
                    tx,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
                ft.Divider(),
                ft.Row(
                    controls=[
                        ft.IconButton(ft.Icons.COPY, on_click=self.copy_ans),
                        ft.IconButton(ft.Icons.SHARE, on_click=self.share_ans),
                    ],
                    tight=True,
                    spacing=0,
                ),
            ]
        )

    def init(self):
        self.change_text(self.body)


def change_page(e, cur, go, bottom_cont, page, chat_page):
    cur.visible = False
    go.visible = True
    bottom_cont.visible = go == chat_page
    page.appbar.visible = True
    page.update()


def _download_and_load(progress_queue):
    """Blocking download/load worker. Progress is sent back through a queue."""
    temp_path = MODEL_PATH + ".part"
    try:
        with requests.get(MODEL_URL, stream=True, timeout=(20, 60)) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            downloaded = 0
            with open(temp_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    file.write(chunk)
                    downloaded += len(chunk)
                    progress_queue.put(("progress", downloaded, total))

        if downloaded <= 0:
            raise RuntimeError("The server returned an empty model file.")
        if total and downloaded != total:
            raise RuntimeError(
                f"Incomplete download: received {downloaded} of {total} bytes."
            )

        os.replace(temp_path, MODEL_PATH)
        progress_queue.put(("status", "Download complete. Loading model…"))
        load_model(MODEL_PATH)
        progress_queue.put(("done", downloaded, total))
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        raise


async def download_model(
    download_prog, download_text, status_text, download_button,
    download_page, chat_page, bottom_cont, page
):
    """Download, verify, and load the model without blocking Flet's UI loop."""
    download_button.disabled = True
    download_prog.value = 0
    download_text.value = "Starting download…"
    status_text.value = "Keep the app open while the model downloads."
    page.update()

    progress_queue = queue.Queue()
    worker = asyncio.create_task(asyncio.to_thread(_download_and_load, progress_queue))
    try:
        while not worker.done() or not progress_queue.empty():
            try:
                item = progress_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

            kind = item[0]
            if kind == "progress":
                _, downloaded, total = item
                downloaded_mb = downloaded / (1024 * 1024)
                if total:
                    total_mb = total / (1024 * 1024)
                    download_text.value = f"{downloaded_mb:.1f} / {total_mb:.1f} MB"
                    download_prog.value = min(downloaded / total, 1.0)
                else:
                    download_text.value = f"{downloaded_mb:.1f} MB downloaded"
                    download_prog.value = None
            elif kind == "status":
                status_text.value = item[1]
            elif kind == "done":
                _, downloaded, total = item
                download_prog.value = 1.0
                size_mb = downloaded / (1024 * 1024)
                download_text.value = f"Complete — {size_mb:.1f} MB"
            page.update()

        await worker
        download_page.visible = False
        chat_page.visible = True
        bottom_cont.visible = True
        page.appbar.visible = True
        status_text.value = "Model ready."
        page.update()
    except Exception as exc:
        print(f"Model download/load error: {exc}")
        status_text.value = f"Could not download or load the model: {exc}"
        download_button.disabled = False
        download_prog.value = 0
        page.update()


def new_chat(e, chats, intro):
    chats.controls.clear()
    chats.controls.append(intro)
    intro.visible = True
    reset_history()
    if getattr(intro, "page", None):
        intro.page.update()


def send(e, page, inp, intro, chats):
    global llm, history

    # If generation is running, stop it.
    if getattr(llm, "_generating", False):
        llm.stop()
        return

    user_text = (inp.value or "").strip()
    if not user_text:
        return

    if llm is None:
        page.open(ft.SnackBar(ft.Text("The AI model is not loaded yet.")))
        page.update()
        return

    # Mark generation as active.
    llm._generating = True

    send_button = e.control
    send_button.icon = ft.Icons.STOP

    inp.value = ""
    intro.visible = False

    query = Query(body=user_text)
    answer = Ans(body="Thinking…")

    chats.controls.extend([query, answer])
    history.append({"role": "user", "content": user_text})
    page.update()

    try:
        answer.body = ""

        for chunk in llm.create_chat_completion(
            messages=history,
            max_tokens=512,
            stream=True,
        ):
            if not llm._generating:
                break

            token = (
                chunk.get("choices", [{}])[0]
                .get("delta", {})
                .get("content")
            )

            if token:
                answer.body += str(token)
                answer.change_text(answer.body)
                page.update()

        if answer.body:
            history.append({
                "role": "assistant",
                "content": answer.body,
            })
        else:
            answer.change_text("Generation stopped.")
            page.update()

    except Exception as exc:
        print(f"Generation error: {exc}")
        answer.change_text(
            "Sorry, an error occurred while generating the response."
        )
        page.update()

    finally:
        llm._generating = False
        send_button.icon = ft.Icons.SEND
        page.update()
