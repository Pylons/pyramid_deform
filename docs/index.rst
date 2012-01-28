pyramid_deform
==============

``pyramid_deform`` provides bindings for the Pyramid web framework to the
`Deform <http://docs.repoze.org/deform>`_ form library.

Installation
------------

Install using setuptools, e.g. (within a virtualenv)::

  $ easy_install pyramid_deform

FormView Usage
--------------

Consider this `colander
<http://docs.pylonsproject.org/projects/colander/en/latest/>`_ schema:

.. code-block:: python

  from colander import Schema, SchemaNode, String
  from deform.widget import RichTextWidget, TextAreaWidget

  class PageSchema(Schema):
      title = SchemaNode(String())
      description = SchemaNode(
          String(),
          widget=TextAreaWidget(cols=40, rows=5),
          missing=u"",
          )
      body = SchemaNode(
          String(),
          widget=RichTextWidget(),
          missing=u"",
          )

You can then write a ``PageEditView`` using
``pyramid_deform.FormView`` like this:

.. code-block:: python

  from pyramid_deform import FormView

  class PageEditView(FormView):
      schema = PageSchema
      buttons = ('save',)

      def save_success(self, appstruct):
          context = self.context.request
          context.title = appstruct['title']
          context.description = appstruct['description']
          context.body = appstruct['body']
          self.request.session.flash(u"Your changes have been saved.")
          return HTTPFound(location=self.request.path_url)

Note that ``save_success`` is only called when the form input
validates.  E.g. it's not called when the ``title`` is left blank, as
it's a required field.

The ``PageEditView`` is registered like any other Pyramid view.  Maybe
like this:

.. code-block:: python

  from myapp.resources import Page

  config.add_view(
      PageEditView,
      context=Page,
      name='edit',
      permission='edit',
      renderer='myapp:templates/form.pt',
      )

Your template in ``myapp:templates/form.pt`` will receive ``form`` as
a variable: this is the rendered form.  Your template might look
something like this:

.. code-block:: html

  <html>
    <body>
      <h1>Edit ${context.title}</h1>
      <form tal:replace="structure form" />
    </div>
  </html>

Wizard
------

XXX

CSRF Schema
-----------

XXX

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
