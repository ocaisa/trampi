# MPI ABI Trampoline

`mpi-abi-trampoline` generates a trampoline implementation of the MPI ABI from an `mpi.h` header. The generated `mpi_proxy.c` forwards all supported MPI and PMPI entry points to a backend MPI library that is selected at runtime.

## Installation

Create and activate a Python virtual environment, then install the generator:

```bash
pip install -e .
```

This installs the `mpi-abi-trampoline` command-line tool together with its Python dependencies.

## Generating the trampoline

Run the generator against the MPI ABI header:

```bash
mpi-abi-trampoline ./mpi-abi-stubs/mpi.h
```

The generator will:

* Parse and verify all MPI and PMPI declarations.
* Generate `mpi_proxy.c`.
* Verify that every parsed function has a corresponding wrapper.

A successful run reports the number of verified wrappers and writes `mpi_proxy.c` into the current directory.

## Building the trampoline library

The generated source can be built using the existing `mpi-abi-stubs` build system.

First, build the reference library if desired:

```bash
cd mpi-abi-stubs
make
make clean
```

Then build the trampoline implementation by overriding the source file:

```bash
make MPI_SOURCE=$PWD/../mpi_proxy.c
```

If the generated source includes the local `mpi.h`, ensure the compiler can find it by adding the project include directory as appropriate for your build system (for example, via `CPPFLAGS=-I$PWD` if required).

The same source override mechanism is supported by the CMake and Meson build systems.

## Output

The resulting shared library exports the same MPI/PMPI interface as the reference `mpi-abi-stubs` implementation while dispatching calls to a backend MPI library at runtime.

## Selecting the backend MPI library

The generated trampoline loads the backend MPI library at runtime using `dlopen()`.

The library to load is chosen as follows:

1. If the environment variable `MPI_ABI_LIBRARY` is set, its value is used.
2. Otherwise, if `DEFAULT_MPI_ABI_LIBRARY` was defined when `mpi_proxy.c` was compiled, that library is used.
3. If neither is available, initialization fails with an error.

For example:

```bash
export MPI_ABI_LIBRARY=/path/to/libmpi.so
./my_mpi_application
```

To embed a default backend library at compile time:

```bash
make \
    MPI_SOURCE=$PWD/../mpi_proxy.c \
    CPPFLAGS='-DDEFAULT_MPI_ABI_LIBRARY=\"/path/to/libmpi.so\"'
```

This allows the trampoline to use a fixed backend by default while still permitting it to be overridden at runtime via `MPI_ABI_LIBRARY`.


