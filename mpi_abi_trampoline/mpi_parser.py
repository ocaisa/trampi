"""
mpi_parser.py

Read mpi.h and build a list of MPI functions.
"""

from dataclasses import dataclass
import subprocess
import re

from .tokenizer import parse_prototype, extract_identifier

##############################################################################
# Model
##############################################################################


@dataclass
class Parameter:

    declaration: str
    name: str


@dataclass
class Function:

    return_type: str
    name: str
    parameters: list

    @property
    def prototype(self):

        if self.parameters:

            args = ", ".join(p.declaration for p in self.parameters)

        else:

            args = "void"

        return f"{self.return_type} " f"{self.name}" f"({args})"


##############################################################################
# Formatting
##############################################################################


def clang_format(text):

    try:

        p = subprocess.run(["clang-format"], input=text, capture_output=True, text=True, check=True)

        return p.stdout.strip()

    except Exception:

        #
        # Continue without formatting.
        #
        return text.strip()


##############################################################################
# Reading mpi.h
##############################################################################


def read_prototypes(filename):
    """
    Collect complete MPI/PMPI prototypes.

    Multi-line declarations become one string.
    """

    prototypes = []

    collecting = False

    current = []

    with open(filename, encoding="utf8", errors="ignore") as f:

        for line in f:

            stripped = line.strip()

            # Skip blank lines.
            if not stripped:
                continue

            # Skip comments.
            if stripped.startswith("/*"):
                continue

            # Skip preprocessor directives.
            if stripped.startswith("#"):
                continue

            if not collecting:

                # Only start collecting if this line contains the
                # beginning of an MPI/PMPI function declaration.
                if not re.search(r"\b(?:MPI_|PMPI_)\w+\s*\(", line):
                    continue
                collecting = True
                current = [stripped]

                if ";" in line:

                    prototypes.append(" ".join(current))

                    collecting = False

            else:

                current.append(stripped)

                if ";" in line:

                    prototypes.append(" ".join(current))

                    collecting = False

    return prototypes


##############################################################################
# Parsing
##############################################################################


def parse_header(filename):

    functions = []

    for prototype in read_prototypes(filename):

        prototype = clang_format(prototype)

        try:

            return_type, name, params = parse_prototype(prototype)

        except Exception as e:

            print()
            print("Unable to parse prototype:")
            print(prototype)
            raise

        parameter_objects = []

        for p in params:

            parameter_objects.append(Parameter(declaration=p, name=extract_identifier(p)))

        functions.append(Function(return_type=return_type, name=name, parameters=parameter_objects))

    return functions
