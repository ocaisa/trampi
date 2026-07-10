"""
verify.py

Sanity checks for parsed MPI prototypes.

The emitter assumes every Function that reaches it
has already passed these checks.
"""

import re

##############################################################################
# Unsupported constructs
##############################################################################

UNSUPPORTED_PATTERNS = [
    (re.compile(r"\.\.\."), "variadic arguments"),
    (re.compile(r"\(\s*\*"), "function pointer parameter"),
    (re.compile(r"__attribute__"), "GCC attributes"),
    (re.compile(r"\btypeof\b"), "typeof"),
]

SKIP_FUNCTIONS = {
    "MPI_Pcontrol",
    "PMPI_Pcontrol",
}

##############################################################################
# Helpers
##############################################################################


def fail(function, message):

    raise RuntimeError(
        f"\n" f"Unsupported declaration in {function.name}\n\n" f"{function.prototype}\n\n" f"Reason: {message}\n"
    )


##############################################################################
# Individual checks
##############################################################################


def check_name(function):

    if not function.name.startswith(("MPI_", "PMPI_")):

        fail(function, "not an MPI symbol")


def check_return_type(function):

    if not function.return_type.strip():

        fail(function, "missing return type")


def check_parameters(function):

    for parameter in function.parameters:

        text = parameter.declaration

        #
        # Parameter without identifier.
        #
        if parameter.name is None:

            fail(function, f"unable to determine identifier:\n{text}")

        #
        # Unsupported syntax.
        #
        for regex, reason in UNSUPPORTED_PATTERNS:

            if regex.search(text):

                fail(function, reason)


def check_duplicates(functions):

    names = set()

    for function in functions:

        if function.name in names:

            raise RuntimeError(f"Duplicate declaration:\n" f"{function.name}")

        names.add(function.name)


##############################################################################
# Statistics
##############################################################################


def print_summary(functions):

    print()

    print("Verification summary")
    print("--------------------")

    print(f"Functions : {len(functions)}")

    mpi = sum(1 for f in functions if f.name.startswith("MPI_"))

    pmpi = len(functions) - mpi

    print(f"MPI  : {mpi}")
    print(f"PMPI : {pmpi}")

    print()


##############################################################################
# Public API
##############################################################################


def verify(functions):

    check_duplicates(functions)

    for function in functions:
        if function.name in SKIP_FUNCTIONS:
            continue

        check_name(function)

        check_return_type(function)

        check_parameters(function)

    print_summary(functions)

    print("Verification successful.")

    return True
