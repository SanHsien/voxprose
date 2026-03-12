import subprocess
import pyperclip
import time


class TextInjector:
    """
    Injects text into the currently focused input field
    by writing to clipboard and simulating Cmd+V.
    """

    def inject(self, text: str) -> None:
        if not text:
            return
            
        # v2.8.27_V50: Revert to pyperclip + Ctrl+V/Cmd+V for ALL platforms.
        # This prevents IME (Input Method Editor) conflicts on Windows and 
        # preserves the user's ability to re-paste the generated text manually.
        pyperclip.copy(text)
        time.sleep(0.05)
        self._paste()

    def select_back(self, char_count: int) -> None:
        """往回選取 char_count 個字元（用於背景 LLM 替換）"""
        if char_count <= 0:
            return
            
        import platform
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            
            # v2.8.27_V38: Use SendInput for reliable back-selection in LLM mode.
            INPUT_KEYBOARD = 1
            VK_SHIFT = 0x10
            VK_LEFT = 0x25
            KEYEVENTF_KEYUP = 0x0002
            
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]
            
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]
                
            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [
                    ("uMsg", wintypes.DWORD),
                    ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD),
                ]

            class INPUT(ctypes.Structure):
                class _INPUT(ctypes.Union):
                    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]
                _anonymous_ = ("_input",)
                _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

            # Press shift
            in_shift_pre = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_SHIFT, 0, 0, 0, None)))
            ctypes.windll.user32.SendInput(1, ctypes.byref(in_shift_pre), ctypes.sizeof(in_shift_pre))

            for _ in range(char_count):
                # Press Left
                in_left_pre = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_LEFT, 0, 0, 0, None)))
                ctypes.windll.user32.SendInput(1, ctypes.byref(in_left_pre), ctypes.sizeof(in_left_pre))
                # Release Left
                in_left_post = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_LEFT, 0, KEYEVENTF_KEYUP, 0, None)))
                ctypes.windll.user32.SendInput(1, ctypes.byref(in_left_post), ctypes.sizeof(in_left_post))

            # Release shift
            in_shift_post = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0, None)))
            ctypes.windll.user32.SendInput(1, ctypes.byref(in_shift_post), ctypes.sizeof(in_shift_post))
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

    def _paste(self) -> None:
        import platform
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            
            # v2.8.27_V53: Use SendInput for maximum reliability on Windows.
            # keybd_event is legacy and might be ignored by some apps.
            
            INPUT_KEYBOARD = 1
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]
            
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]
                
            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [
                    ("uMsg", wintypes.DWORD),
                    ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD),
                ]

            class INPUT(ctypes.Structure):
                class _INPUT(ctypes.Union):
                    _fields_ = [
                        ("ki", KEYBDINPUT),
                        ("mi", MOUSEINPUT),
                        ("hi", HARDWAREINPUT)
                    ]
                _anonymous_ = ("_input",)
                _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

            # 1. Press CTRL
            in_ctrl_down = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, None)))
            # 2. Press V
            in_v_down = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_V, 0, 0, 0, None)))
            # 3. Release V
            in_v_up = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, None)))
            # 4. Release CTRL
            in_ctrl_up = INPUT(type=INPUT_KEYBOARD, _input=INPUT._INPUT(ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None)))

            inputs = (INPUT * 4)(in_ctrl_down, in_v_down, in_v_up, in_ctrl_up)
            ctypes.windll.user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        else:
            # macOS: Use AppleScript
            script = """
            tell application "System Events"
                keystroke "v" using command down
            end tell
            """
            subprocess.run(["osascript", "-e", script], check=True)
