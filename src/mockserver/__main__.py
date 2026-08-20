"""
WHAT      Entry point so the mock server starts with `python -m mockserver`.
WHY       An MCP stdio server is spawned by its client as a command line. Having
          a module entry point means that command is `python -m mockserver`,
          which works from any directory once the package is installed, rather
          than a path to a script file that only works from the repo root.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  `python -m` depends on the package being installed in the environment
          the client spawns. That is why external_mcp.py passes sys.executable
          rather than the string "python" - the client must use the same
          interpreter, or the import fails in a subprocess whose stderr you are
          not reading.
ALTERNATIVE  A console script in [project.scripts]. Cleaner to invoke, and it
          hides which interpreter is running, which is the one thing you most
          want visible while debugging a transport.
"""
from .server import main

main()
