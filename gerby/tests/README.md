Tests
=====

The script `find_tex_errors.py` runs a headless browser through all tags
corresponding to sections and looks for MathJax errors. When TeX errors are
found, they are reported in console by a print statement. The tag at which this
error is found is given, together with the offending LaTeX code.

To run this script:

  1. Install `selenium`, via `pip install selenium`. See the
  [docs](https://selenium-python.readthedocs.io/) for more detail.
  2. Install `geckodriver` to run the Firefox webdriver. Obtain the binary
  [here](https://github.com/mozilla/geckodriver/releases), and put it somewhere
  where your `PATH` variable can find.
  3. Change the parameters `database` and `url` in `find_tex_errors.py` as
  needed.
  4. Run your Flask app.
  5. Run `python find_tex_errors.py`.

