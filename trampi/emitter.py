import re
from .verify import VARIADIC_FUNCTIONS


def read_mpi_stubs(source):
    """
    Return mpistubs.c as a list of lines.

    The file is read verbatim.
    """

    with open(source, encoding="utf8") as f:
        return f.readlines()


def inject_runtime_support(out, base_functions, extension_functions):
    all_functions = base_functions + extension_functions
    out.write("""
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>

#ifndef DEFAULT_MPI_ABI_LIBRARY
#define DEFAULT_MPI_ABI_LIBRARY NULL
#endif

""")

    #
    # Typedefs
    #
    for fn in all_functions:
        params = ", ".join(p.declaration for p in fn.parameters) or "void"
        out.write(f"typedef {fn.return_type} " f"(*fn_{fn.name}_t)({params});\n")

    out.write("\n")

    #
    # Backend pointers
    #
    for fn in all_functions:
        out.write(f"static fn_{fn.name}_t backend_{fn.name} = NULL;\n")

    out.write(r"""

static void __attribute__((constructor))
init_mpi_proxy(void)
{
    const char *lib;
    const char *verbose;
    void *handle;
    void *sym;
    int missing_symbols = 0;
    int missing_ext_symbols = 0;

    verbose = getenv("MPI_ABI_LIBRARY_VERBOSE");
    lib = getenv("MPI_ABI_LIBRARY");

    if (!lib)
        lib = DEFAULT_MPI_ABI_LIBRARY;


    if (!lib) {
        fprintf(stderr,
            "No MPI backend configured. Please set the environment variable MPI_ABI_LIBRARY to an MPI ABI-compliant library\n");
        abort();
    }

    handle = dlopen(lib, RTLD_NOW | RTLD_GLOBAL);

    if (!handle) {
        fprintf(stderr,
            "%s\n",
            dlerror());
        abort();
    }
    
    if (verbose) {
        fprintf(stderr, "Opened backend MPI ABI library %s\n", lib);
    }

""")

    for fn in base_functions:
        out.write(f'    sym = dlsym(handle, "{fn.name}");\n')
        out.write("    if (!sym) {\n")
        out.write("        if (verbose)\n")
        out.write(f'            fprintf(stderr, "Unable to resolve {fn.name}\\n");\n')
        out.write("        ++missing_symbols;\n")
        out.write("    }\n")
        out.write(f"    *(void **)(&backend_{fn.name}) = sym;\n")
    out.write("\n")
    for fn in extension_functions:
        out.write(f'    sym = dlsym(handle, "{fn.name}");\n')
        out.write("    if (!sym) {\n")
        out.write("        if (verbose)\n")
        out.write(
            f"            fprintf(stderr, " f'"Optional MPI ABI extension not available in runtime: {fn.name}\\n");\n'
        )
        out.write("        ++missing_ext_symbols;\n")
        out.write("    }\n")
        out.write(f"    *(void **)(&backend_{fn.name}) = sym;\n")

    out.write("""
    if (missing_symbols && verbose) {
    fprintf(stderr,
            "Warning: %d required MPI ABI symbols could not be resolved. "
            "Calls to these functions will fail.\\n",
            missing_symbols);
    }

    if (missing_ext_symbols && verbose) {
        fprintf(stderr,
                "Warning: %d optional MPI ABI extension symbols could not be resolved. "
                "This runtime is not patched for these (optional) MPI ABI extensions. "
                "Calls to these functions will fail.\\n",
                missing_ext_symbols);
    }
}

""")


def wrapper_body(fn):

    if fn.name in VARIADIC_FUNCTIONS:

        return (
            f'fprintf(stderr, "{fn.name}: '
            'cannot automatically forward variadic arguments\\n"); '
            "return MPI_SUCCESS; "
        )

    call = ", ".join(p.name for p in fn.parameters if p.name)

    if fn.return_type == "void":
        return f"backend_{fn.name}({call}); "

    return f"return backend_{fn.name}({call}); "


def emit_wrapper(out, fn):

    params = ", ".join(p.declaration for p in fn.parameters) or "void"

    out.write(f"{fn.return_type} {fn.name}({params}) ")
    out.write("{ ")

    out.write(wrapper_body(fn))

    out.write("}\n")


def rewrite_mpi_stubs(lines, functions):
    """
    Rewrite the bodies of MPI/PMPI functions while preserving the rest
    of mpistubs.c unchanged.
    """

    lookup = {fn.name: fn for fn in functions}

    pattern = re.compile(r"\b(" + "|".join(re.escape(fn.name) for fn in functions) + r")\s*\(")

    out = []

    i = 0

    while i < len(lines):

        line = lines[i]

        m = pattern.search(line)

        #
        # Not an MPI function.
        #
        if m is None:
            out.append(line)
            i += 1
            continue

        fn = lookup[m.group(1)]

        #
        # Copy the signature up to and including the opening brace.
        #
        while True:

            line = lines[i]

            if "{" in line:

                brace = line.index("{")

                #
                # Preserve everything through the opening brace.
                #
                out.append(line[: brace + 1] + " ")

                #
                # One-line function?
                #
                if "}" in line[brace + 1 :]:
                    i += 1
                    break

                i += 1

                #
                # Skip the original body.
                #
                depth = 1

                while i < len(lines) and depth:

                    depth += lines[i].count("{")
                    depth -= lines[i].count("}")

                    i += 1

                break

            out.append(line)
            i += 1

        #
        # Emit replacement body.
        #
        out.append(wrapper_body(fn))

        #
        # Close the function.
        #
        out.append("}\n")

    return out


def emit_proxy(
    *,
    functions,
    extension_functions,
    mpi_stubs,
    output,
):

    lines = read_mpi_stubs(mpi_stubs)

    rewritten = rewrite_mpi_stubs(lines, functions)

    insert_after = -1

    for i, line in enumerate(rewritten):
        if line.lstrip().startswith("#include"):
            insert_after = i

    if insert_after == -1:
        raise RuntimeError("No #include directives found.")

    with open(output, "w", encoding="utf8") as out:

        for i, line in enumerate(rewritten):

            out.write(line)

            if i == insert_after:
                out.write("\n")
                inject_runtime_support(out, functions, extension_functions)
                out.write("\n")

        #
        # Emit wrappers that are not yet present in mpistubs.c.
        #
        if extension_functions:

            out.write("""

/*
 * Additional wrappers from mpi.h.patch.
 */

""")

            for fn in extension_functions:
                emit_wrapper(out, fn)
                out.write("\n")
