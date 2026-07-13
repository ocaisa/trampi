# MPI ABI Trampoline

`mpi-abi-trampoline` generates a trampoline implementation of the MPI ABI from an `mpi.h` header file and an `mpistubs.c` file (which are expected to come from the [`mpi-abi-stubs` reference for the MPI standard ABI](https://github.com/mpi-forum/mpi-abi-stubs)). The generated `mpi_proxy.c` forwards all supported MPI and PMPI entry points to a backend MPI library that is selected at runtime. The library also relies on `mpi-abi-stubs` to provide a build system.

## Installation

Create and activate a Python virtual environment, then install the generator:

```bash
pip install -e .
```

This installs the `mpi-abi-trampoline` command-line tool.

## Generating the trampoline

Run the generator against the MPI ABI header and stub. For example:

```bash
mpi-abi-trampoline --header mpi-abi-stubs/mpi.h --stubs mpi-abi-stubs/mpistubs.c
```

The generator will:

* Parse and verify all MPI and PMPI declarations.
* Generate `mpi_proxy.c`.
* Verify that every parsed function has a corresponding wrapper.

A successful run reports the number of verified wrappers and writes `mpi_proxy.c` into the current directory.

## Building the trampoline library

The generated source can be built using the existing `mpi-abi-stubs` build system (which supports a `Makefile`, `CMake`, and `Meson`).

First, build the reference library if desired to ensure compilation succeeds in general:

```bash
cd mpi-abi-stubs
make
make clean
```

Then build the trampoline implementation by overriding the source file:

```bash
ln -s ../mpi_proxy.c  # Make a symlink to our generated code
make SOURCE_C=mpi_proxy.c
```

A similar source override mechanism is supported by the CMake (`-DSOURCE_C=mpi_proxy.c`) and Meson (`-Dsource_c=mpi_proxy.c`) build systems.

## Output

The resulting shared library exports the same MPI/PMPI interface as the reference `mpi-abi-stubs` implementation while dispatching calls to a backend MPI library at runtime.

## Selecting the backend MPI library

The generated trampoline loads the backend MPI library at runtime using `dlopen()`.

The library to load is chosen as follows:

1. If the environment variable `MPI_ABI_LIBRARY` is set, its value is used.
2. Otherwise, if `DEFAULT_MPI_ABI_LIBRARY` was defined when `mpi_proxy.c` was compiled, that library is used.
3. If neither is available, initialisation fails with an error.

For example:

```bash
export MPI_ABI_LIBRARY=/path/to/libmpi.so
./my_mpi_application
```

To embed a default backend library at compile time requires some awkward but necessary quoting since we don't control the build system. For the `Makefile`

```bash
export CPPFLAGS='-DDEFAULT_MPI_ABI_LIBRARY=\"/path/to/libmpi_abi.so\"'
make SOURCE_C=mpi_proxy.c
```

or for CMake:

```bash
cmake -B build --install-prefix=$PWD -DSOURCE_C=mpi_proxy.c -DCMAKE_C_FLAGS='"-DDEFAULT_MPI_ABI_LIBRARY=\"/path/to/libmpi_abi.so\""'
```

or for Meson:

```bash
meson setup build -Dsource_c=mpi_proxy.c -Dc_args='-DDEFAULT_MPI_ABI_LIBRARY=\"/path/to/libmpi_abi.so\"'
```

This allows the trampoline to use a fixed backend by default while still permitting it to be overridden at runtime via `MPI_ABI_LIBRARY`.
