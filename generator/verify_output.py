"""
verify_output.py

Verify a generated mpi_proxy.c.

This does NOT parse arbitrary C.

It only understands the very regular code emitted by emit.py.
"""

import re

##############################################################################
# Patterns
##############################################################################

TYPEDEF_RE = re.compile(r"^typedef\b.*\(\*fn_(\w+)_t\)\(")

BACKEND_RE = re.compile(r"^static\s+fn_(\w+)_t\s+backend_(\w+)\s*=")

DLSYM_RE = re.compile(r'dlsym\(.*?"(\w+)"')

WRAPPER_RE = re.compile(r"^(?:int|void|double|MPI_\w+)\s+((?:P?MPI_\w+))\(")

CALL_RE = re.compile(r"backend_(\w+)\((.*?)\)")


##############################################################################
# Index
##############################################################################


class OutputIndex:

    def __init__(self):

        self.typedefs = {}

        self.backends = {}

        self.dlsyms = {}

        self.wrappers = {}

        self.calls = {}


##############################################################################
# Scanner
##############################################################################


def scan(filename):

    index = OutputIndex()

    current_wrapper = None

    with open(filename, encoding="utf8") as f:

        for line in f:

            line = line.strip()

            #
            # typedef
            #
            m = TYPEDEF_RE.match(line)

            if m:

                index.typedefs[m.group(1)] = True

                continue

            #
            # backend variable
            #
            m = BACKEND_RE.match(line)

            if m:

                if m.group(1) != m.group(2):

                    raise RuntimeError("Backend typedef mismatch")

                index.backends[m.group(1)] = True

                continue

            #
            # dlsym
            #
            m = DLSYM_RE.search(line)

            if m:

                index.dlsyms[m.group(1)] = True

                continue

            #
            # wrapper
            #
            m = WRAPPER_RE.match(line)

            if m:

                current_wrapper = m.group(1)

                index.wrappers[current_wrapper] = True

                continue

            #
            # backend call
            #
            if current_wrapper:

                m = CALL_RE.search(line)

                if m:

                    index.calls[current_wrapper] = (m.group(1), m.group(2))

    return index


##############################################################################
# Verification
##############################################################################


def verify(functions, filename):

    index = scan(filename)

    errors = 0

    print()

    print("Output verification")
    print("-------------------")

    for function in functions:

        #
        # Skip MPI_Pcontrol if you intentionally stub it.
        #
        if function.name in ("MPI_Pcontrol", "PMPI_Pcontrol"):

            continue

        name = function.name

        if name not in index.typedefs:

            print("Missing typedef:", name)

            errors += 1

        if name not in index.backends:

            print("Missing backend:", name)

            errors += 1

        if name not in index.dlsyms:

            print("Missing dlsym:", name)

            errors += 1

        if name not in index.wrappers:

            print("Missing wrapper:", name)

            errors += 1

        if name not in index.calls:

            print("Missing backend call:", name)

            errors += 1

            continue

        backend_name, call = index.calls[name]

        if backend_name != name:

            print(f"Wrong backend: " f"{name} -> {backend_name}")

            errors += 1

        expected = [p.name for p in function.parameters if p.name]

        actual = [x.strip() for x in call.split(",") if x.strip()]

        if expected != actual:

            print()

            print(name)

            print(" expected:", expected)

            print(" actual:  ", actual)

            errors += 1

    print()

    if errors:

        raise RuntimeError(f"{errors} verification errors")

    print(f"Verified {len(functions)} wrappers.")

    return True
