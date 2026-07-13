#!/usr/bin/env python3

"""
Generate mpi_proxy.c from an MPI header.
"""

import argparse
import sys

from .mpi_parser import parse_header
from .verify import verify
from .emitter import emit_proxy
from .verify_output import verify_output


def main():

    parser = argparse.ArgumentParser(description="Generate an MPI ABI trampoline.")

    parser.add_argument(
        "--header",
        required=True,
        help="Path to mpi.h",
    )

    parser.add_argument(
        "--stubs",
        required=True,
        help="Path to mpistubs.c",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="mpi_proxy.c",
        help="Output C file",
    )

    parser.add_argument(
        "--no-verify-output",
        action="store_true",
        help="Skip verification of generated output",
    )

    args = parser.parse_args()

    print(f"Reading {args.header}")
    print(f"Reading {args.stubs}")

    functions = parse_header(args.header)

    verify(functions)

    emit_proxy(
        functions=functions,
        mpi_stubs=args.stubs,
        output=args.output,
    )

    print(f"Wrote {args.output}")

    if not args.no_verify_output:
        verify_output(functions=functions, mpi_stubs=args.stubs, mpi_proxy=args.output)

    print("Done.")


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        sys.exit(1)

    except Exception as e:

        print()

        print("ERROR")

        print(e)

        sys.exit(1)
