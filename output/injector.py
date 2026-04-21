import subprocess
import pyperclip
import time
import logging

_log = logging.getLogger("voicetype.injector")


class TextInjector:
    """
    Injects text into the currently focused input field
    by writing to clipboard and simulating Cmd+V.
    """

    def inject(self, text: str, target_bundle_id: str = "", target_pid: int = 0) -> None:
        if not text:
            return
        pyperclip.copy(text)
        time.sleep(0.05)  # small delay to ensure clipboard is ready
        self._paste(target_bundle_id, target_pid)

    def select_back(self, char_count: int) -> None:
        """往回選取 char_count 個字元（用於背景 LLM 替換）"""
        if char_count <= 0:
            return
            
        import platform
        if platform.system() == "Windows":
            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.shift):
                for _ in range(char_count):
                    kb.press(Key.left)
                    kb.release(Key.left)
        else:
            # macOS: Use AppleScript
            script = f"""
            tell application "System Events"
                repeat {char_count} times
                    key code 123 using shift down
                end repeat
            end tell
            """
            subprocess.run(["osascript", "-e", script], check=True)

    def _paste(self, target_bundle_id: str = "", target_pid: int = 0) -> None:
        import platform
        if platform.system() == "Windows":
            from pynput.keyboard import Controller, Key
            kb = Controller()
            with kb.pressed(Key.ctrl):
                kb.press('v')
                kb.release('v')
        else:
            # macOS: v2.9.10 — CGEventPostToPid + 診斷日誌
            # 流程：
            # 1. 取得目前 frontmost app，記錄診斷日誌
            # 2. 若 focus 已跑掉，先 AppleScript activate 目標 App
            # 3. 優先用 CGEventPostToPid 直接投遞 Cmd+V 給目標 PID（繞過 System Events）
            # 4. Fallback: AppleScript keystroke

            # 1. 取得目前 frontmost
            current_bundle = ""
            try:
                from AppKit import NSWorkspace
                current = NSWorkspace.sharedWorkspace().activeApplication()
                current_bundle = current.get("NSApplicationBundleIdentifier", "")
            except Exception as e:
                _log.warning(f"[paste] NSWorkspace error: {e}")

            focus_changed = bool(target_bundle_id and current_bundle != target_bundle_id)
            clipboard_len = 0
            try:
                clipboard_len = len(pyperclip.paste())
            except Exception:
                pass
            _log.info(
                f"[paste] target=({target_bundle_id}, pid={target_pid}) "
                f"current=({current_bundle}) focus_changed={focus_changed} "
                f"clipboard_len={clipboard_len}"
            )

            # 2. focus 跑掉時先 activate
            if focus_changed and target_bundle_id:
                _log.info(f"[paste] Activating target app: {target_bundle_id}")
                subprocess.run(
                    ["osascript", "-e",
                     f'tell application id "{target_bundle_id}" to activate'],
                    capture_output=True
                )
                time.sleep(0.3)

            # 3. CGEventPostToPid（若有 PID）
            if target_pid > 0:
                try:
                    import Quartz
                    V_KEYCODE = 9  # kVK_ANSI_V
                    CMD_MASK = Quartz.kCGEventFlagMaskCommand
                    for is_down in [True, False]:
                        ev = Quartz.CGEventCreateKeyboardEvent(None, V_KEYCODE, is_down)
                        Quartz.CGEventSetFlags(ev, CMD_MASK)
                        Quartz.CGEventPostToPid(target_pid, ev)
                        time.sleep(0.01)
                    _log.info(f"[paste] CGEventPostToPid({target_pid}) Cmd+V sent OK")
                    return
                except Exception as e:
                    _log.warning(f"[paste] CGEventPostToPid failed: {e}, falling back to AppleScript")

            # 4. Fallback: AppleScript keystroke
            script = """tell application "System Events"
    keystroke "v" using command down
end tell"""
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                _log.error(f"[paste] AppleScript fallback error: {result.stderr.strip()}")
            else:
                _log.info("[paste] AppleScript fallback OK")
