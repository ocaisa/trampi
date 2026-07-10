from pathlib import Path
from .verify import SKIP_FUNCTIONS


def emit_header(out):

    out.write("""\
/*
 * Auto-generated.
 * DO NOT EDIT.
 */

#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <stdarg.h>
#include <string.h>

#include <mpi.h>

/* Fallback definition if DEFAULT_MPI_ABI_LIBRARY is not provided at compile time */
#ifndef DEFAULT_MPI_ABI_LIBRARY
#define DEFAULT_MPI_ABI_LIBRARY NULL
#endif

""")


def emit_typedefs(out, functions):

    out.write("/* Function pointer typedefs */\n\n")

    for fn in functions:

        args = ", ".join(p.declaration for p in fn.parameters)

        if not args:
            args = "void"

        out.write(f"typedef {fn.return_type} " f"(*fn_{fn.name}_t)" f"({args});\n")

    out.write("\n")


def emit_backend_storage(out, functions):

    out.write("/* Backend storage */\n\n")

    for fn in functions:

        out.write(f"static fn_{fn.name}_t " f"backend_{fn.name} = NULL;\n")

    out.write("\n")


def emit_constructor(out, functions):

    out.write("""\
static void __attribute__((constructor))
init_proxy(void)
{
    void *handle;
    void *symbol;

    const char *lib =
        getenv("MPI_ABI_LIBRARY");

    if (!lib)
        lib = DEFAULT_MPI_ABI_LIBRARY;
              
    if (!lib) {
        fprintf(stderr,
                "No MPI backend library specified, set environment variable MPI_ABI_LIBRARY to an ABI standard library.\\n");
        exit(EXIT_FAILURE);
    }

    handle = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);

    if (!handle) {

        fprintf(stderr,
                "Unable to load %s\\n",
                lib);

        abort();
    }

""")

    for fn in functions:

        out.write(f'    symbol = dlsym(handle, "{fn.name}");\n')

        out.write(f"    memcpy(&backend_{fn.name}," f" &symbol, sizeof(symbol));\n")

    out.write("}\n\n")


def emit_wrappers(out, functions):

    out.write("/* Wrappers */\n\n")

    for fn in functions:

        # Handle the special case for variadic arguments
        if fn.name in SKIP_FUNCTIONS:
            out.write(f"""{fn.return_type} {fn.name}(const int level, ...)
{{
    fprintf(stderr,
            "{fn.name}: cannot automatically forward variadic arguments\\n");
    return MPI_SUCCESS;
}}

""")
            continue

        args = ", ".join(p.declaration for p in fn.parameters)

        if not args:
            args = "void"

        call = ", ".join(p.name for p in fn.parameters if p.name)

        out.write(f"{fn.return_type} " f"{fn.name}" f"({args})\n{{\n")

        if fn.return_type == "void":

            out.write(f"    backend_{fn.name}" f"({call});\n")

        else:

            out.write(f"    return " f"backend_{fn.name}" f"({call});\n")

        out.write("}\n\n")


def emit(functions, output_file):
    """
    Emit mpi_proxy.c from a list of Function objects.

    Parameters
    ----------
    functions : list[Function]
        Parsed and verified MPI functions.

    output_file : str or Path
        Output C filename.
    """

    with open(output_file, "w") as out:

        emit_header(out)

        emit_typedefs(out, functions)

        emit_backend_storage(out, functions)

        emit_constructor(out, functions)

        emit_wrappers(out, functions)
