pyramid_deform
==============

``pyramid_deform`` provides bindings for the Pyramid web framework to the
`Deform <http://docs.repoze.org/deform>`_ form library.

Installation
------------

Install using setuptools, e.g. (within a virtualenv)::

  $ easy_install pyramid_deform

Usage
-----
XXX

CSRF Schema
-----------
::
    >>> class LoginSchema(CSRFSchema):
    >>>     pass
    >>> schema = LoginSchema.get_schema(self.request)


Reporting Bugs / Development Versions
-------------------------------------

Visit https://github.com/Pylons/pyramid_deform/issues to report bugs.
Visit https://github.com/Pylons/pyramid_deform to download development or
tagged versions.

Indices and tables
------------------

* :ref:`modindex`
* :ref:`search`
