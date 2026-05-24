# check.py
# Run this first if anything fails: python check.py
# Every line must print OK.

def test(label: str, fn):
    try:
        fn()
        print(f"  OK   {label}")
    except Exception as e:
        print(f"  FAIL {label}: {e}")

print("\nDIAGNOSTIC — INSTRUMENT FOR OUTER REASONING")
print("─" * 48)
test("config",         lambda: __import__("config"))
test("state",          lambda: __import__("state"))
test("decay",          lambda: __import__("decay"))
test("commands",       lambda: __import__("commands"))
test("terminal",       lambda: __import__("terminal"))
test("logger",         lambda: __import__("logger"))
test("inference_stub", lambda: __import__("inference_stub"))
print("─" * 48)

try:
    from state    import CognitiveStateEngine
    from decay    import DecayEngine
    from commands import CommandParser, PERMITTED_COMMANDS
    from terminal import Terminal
    from logger   import SessionLogger
    print(f"  OK   All classes resolved")
    print(f"  OK   Permitted: {sorted(PERMITTED_COMMANDS)}")
except Exception as e:
    print(f"  FAIL {e}")

print("─" * 48)
print("All OK? Run: python main.py\n")
