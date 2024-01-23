import json
from pathlib import Path
import pickle
from typing import Any


def load_datalogger_file(path: str | Path,
                         printing: bool = False,
                         ) -> tuple[str,
                                    dict[str, list[float]],
                                    dict[str, Any]]:
    if isinstance(path, str):
        path = Path(path)
    full_path = path
    extensions = [".json", ".pkl"]
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
    else:
        raise ValueError(f"Invalid file name suffix '{suffix}'.")
    metas = more[0] if more else {}
    if printing:
        print(full_path.name, data.keys())
    return header, data, metas
