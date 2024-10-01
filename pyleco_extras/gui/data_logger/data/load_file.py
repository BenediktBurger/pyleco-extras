import json
from pathlib import Path
import pickle
from typing import Any

import numpy as np


def load_datalogger_file(path: str | Path,
                         printing: bool = False,
                         ) -> tuple[str,
                                    dict[str, list[float]],
                                    dict[str, Any]]:
    """Load a file saved with the data logger.

    Can load files pickled, numpy text file, or JSON formatted.

    :return: Header string, data dict, parameters dict
    """
    if isinstance(path, str):
        path = Path(path)
    full_path = path
    extensions = [".json", ".pkl", ".txt"]
    while not full_path.is_file():
        try:
            full_path = Path(f"{path}{extensions.pop()}")
        except IndexError:
            raise FileNotFoundError
    suffix = full_path.suffix
    if suffix.lower() == ".json":
        header, data, *more = json.load(full_path.open("r"))
    elif suffix.lower() == ".pkl":
        header, data, *more = pickle.load(full_path.open("rb"))
    elif suffix.lower() == ".txt":
        with full_path.open("r") as file:
            lines = []
            while True:
                line = file.readline()
                if line.startswith("# "):
                    lines.append(line[2:])
                else:
                    break
            header = "\n".join(lines)
            variables = lines[-1].split() if lines else []
        data_table = np.loadtxt(full_path)
        data = {}
        for i, var in enumerate(variables):
            data[var] = list(data_table[:, i])
        more = None
    else:
        raise ValueError(f"Invalid file name suffix '{suffix}'.")
    metas = more[0] if more else {}
    if printing:
        print(full_path.name, data.keys())
    return header, data, metas
