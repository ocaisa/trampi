"""
verify_output.py

Verify a generated mpi_proxy.c.

This does NOT parse arbitrary C.

It only understands the very regular code emitted by emitter.py.
"""

import re
from .verify import SKIP_FUNCTIONS

NAME_RE = re.compile(r"^\s*.*?\b((?:MPI|PMPI)_\w+)\s*\(")
CALL_RE = re.compile(r"\bbackend_(\w+)\((.*?)\)")


def make_wrapper_pattern(functions):

    names = sorted(
        (re.escape(fn.name) for fn in functions),
        key=len,
        reverse=True,
    )

    return re.compile(r"\b(" + "|".join(names) + r")\s*\(")


def make_backend_pattern(functions):

    names = sorted(
        (re.escape(fn.name) for fn in functions),
        key=len,
        reverse=True,
    )

    return re.compile(
        r"\bbackend_(" + "|".join(names) + r")\s*\((.*?)\)",
        re.DOTALL,
    )


def scan_wrappers(filename, functions):

    wrappers = {}

    current = None
    depth = 0

    wrapper_re = make_wrapper_pattern(functions)
    backend_re = make_backend_pattern(functions)

    with open(filename, encoding="utf8") as f:

        for line in f:

            #
            # Outside a function.
            #
            if current is None:

                m = wrapper_re.search(line)

                if not m:
                    continue

                current = m.group(1)

                wrappers[current] = {
                    "call": None,
                    "args": [],
                }

                #
                # Backend call on the same line?
                #
                m = backend_re.search(line)

                if m:

                    wrappers[current]["call"] = m.group(1)

                    wrappers[current]["args"] = [x.strip() for x in m.group(2).split(",") if x.strip()]

                depth += line.count("{")
                depth -= line.count("}")

                if depth == 0:
                    current = None

                continue

            #
            # Inside a function.
            #
            depth += line.count("{")
            depth -= line.count("}")

            m = backend_re.search(line)

            if m:

                wrappers[current]["call"] = m.group(1)

                wrappers[current]["args"] = [x.strip() for x in m.group(2).split(",") if x.strip()]

            if depth == 0:
                current = None

    return wrappers


def verify_output(*, functions, mpi_stubs, mpi_proxy):

    reference = scan_wrappers(mpi_stubs, functions)
    generated = scan_wrappers(mpi_proxy, functions)

    errors = 0

    print()
    print("Output verification")
    print("-------------------")

    #
    # Compare wrapper sets.
    #
    missing = sorted(set(reference) - set(generated))

    for name in missing:
        print("Missing wrapper:", name)
        errors += 1

    extra = sorted(set(generated) - set(reference))

    for name in extra:
        print("Unexpected wrapper:", name)
        errors += 1

    #
    # Compare generated wrappers against the parsed MPI API.
    #
    for fn in functions:

        if fn.name in SKIP_FUNCTIONS:
            continue

        if fn.name not in generated:
            continue

        wrapper = generated[fn.name]

        #
        # Backend call.
        #
        if wrapper["call"] != fn.name:

            print(f"Wrong backend: " f"{fn.name} -> {wrapper['call']}")

            errors += 1

        #
        # Arguments.
        #
        expected = [p.name for p in fn.parameters if p.name]

        if wrapper["args"] != expected:

            print()
            print(fn.name)
            print(" expected:", expected)
            print(" actual:  ", wrapper["args"])

            errors += 1

    print()

    if errors:
        print(f"Reference wrappers : {len(reference)}")
        print(f"Generated wrappers : {len(generated)}")
        print()
        raise RuntimeError(f"{errors} verification errors")

    print(f"Verified {len(reference)} wrappers ({len(SKIP_FUNCTIONS)} of these checks were skipped though).")

    return True
