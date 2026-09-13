#!/usr/bin/env python3
"""Run the SurveyZoneList smoke tests outside of the game.

The addon is plain Lua 5.1 against the ESO API. stub.lua stands in for the
parts of that API the addon touches, so the collect / sort / display path can
be exercised without launching the client.

    pip install lupa
    python tools/surveyzonelist-tests/run.py
"""
import os
import sys

try:
    from lupa import LuaRuntime
except ImportError:
    sys.exit("lupa is required: pip install lupa")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ADDON = os.path.join(REPO, "docs", "eso", "addons", "SurveyZoneList")


def main():
    if not os.path.isdir(ADDON):
        sys.exit("addon not found at " + ADDON)

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("ADDON_DIR = '%s'" % ADDON.replace("\\", "/"))

    for name in ("stub.lua", "test.lua"):
        with open(os.path.join(HERE, name), encoding="utf-8") as handle:
            source = handle.read()
        try:
            lua.execute(source)
        except Exception as error:  # noqa: BLE001 - surface the Lua traceback
            print("LUA ERROR in %s: %s" % (name, error))
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
