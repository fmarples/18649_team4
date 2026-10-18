"""Check a built measurement image's TEST_BTN mapping against the board's B1.

Run with the Zephyr Python environment and python-devicetree on PYTHONPATH:
    python tests/check_lab3_button.py BUILD/zephyr/edt.pickle [...]
"""
import argparse
import pickle
from pathlib import Path


# Check the generated hardware configuration rather than overlay text formatting.
def check_button(path):
    with path.open('rb') as stream:
        edt = pickle.load(stream)  # Trusted, locally generated Zephyr build artifact.
    actual = edt.get_node('/zephyr,user').props['test-button-gpios'].val[0]
    expected = edt.get_node('sw0').props['gpios'].val[0]
    actual_input = (actual.controller.path, actual.data['pin'], actual.data['flags'] & 1)
    expected_input = (expected.controller.path, expected.data['pin'], expected.data['flags'] & 1)
    assert actual_input == expected_input, f'{path}: TEST_BTN {actual_input} != B1 {expected_input}'
    print(f'{path}: TEST_BTN matches built-in B1, active polarity included')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('builds', nargs='+', type=Path)
    for path in parser.parse_args().builds:
        check_button(path)
