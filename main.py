# main.py
# Entry point.
#
# HOW TO RUN:
#   cd C:\outer_reasoning      (the folder containing this file)
#   python main.py
#
# WHY THIS WORKS WITHOUT CONFIGURATION:
#   Python adds the directory of the script being run to sys.path[0].
#   All imports in this project use flat module names (e.g. "from state import ...")
#   because all files are siblings in the same directory.
#   No packages. No __init__.py. No PYTHONPATH. No IDE required.

from state          import CognitiveStateEngine
from decay          import DecayEngine
from logger         import SessionLogger
from inference_stub import InferenceStub
from terminal       import Terminal


def main() -> None:

    engine = CognitiveStateEngine()
    log    = SessionLogger()
    stub   = InferenceStub()
    log.begin()

    # Start passive decay daemon
    # [DECAY ENGINE: background thread begins here]
    decay = DecayEngine(engine=engine)
    decay.start()

    def on_command(command: str, argument: str) -> dict:
        # [STATE UPDATE via engine.on_command()]
        snap = engine.on_command(command)
        log.log_command(command, argument, snap)
        # [NEURAL MODEL INTEGRATION POINT — uncomment when model ready]
        # stub.infer(engine.get_feature_vector())
        return snap

    def on_quit() -> None:
        log.end(engine.command_count)
        decay.stop()

    terminal = Terminal(engine=engine, on_command=on_command, on_quit=on_quit)
    terminal.boot()

    try:
        terminal.run()
    except Exception as exc:
        print(f"\n  [SYSTEM ERROR] {exc}")
    finally:
        try:
            on_quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
