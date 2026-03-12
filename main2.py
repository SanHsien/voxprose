import multiprocessing
import os
import sys

print(f"Current process name: {multiprocessing.current_process().name}")

is_main_process = (
    getattr(multiprocessing.current_process(), 'name', '') == 'MainProcess' and
    os.environ.get("VOICETYPE_STT_WORKER") != "1" and
    "--multiprocessing-fork" not in sys.argv
)

print(f"is_main_process: {is_main_process}")

from paths import initialize_paths
initialize_paths()
print("Paths initialized OK")

from ui.app import VoiceTypeApp
print("VoiceTypeApp imported OK")
