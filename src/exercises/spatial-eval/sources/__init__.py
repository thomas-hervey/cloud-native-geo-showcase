"""GT source adapters — importing this package registers all GT sources.

To add a new GT source:
  1. Create sources/my_source.py
  2. Decorate the class with @register_gt("my_source")
  3. Add `from . import my_source` below
"""
from . import click_that_hood
from . import osm
from . import osm_overpass
from . import sf_planning
from . import zillow
from . import wikidata
