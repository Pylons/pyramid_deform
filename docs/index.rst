pyramid_deform
==============

``pyramid_deform`` provides bindings for the Pyramid web framework to the
`Deform <http://pylons.readthedocs.org/projects/deform/en/latest/>`_ form
library.

Topics
------

.. toctree::
   :maxdepth: 2

   api.rst
   changes.rst

Installation
------------

Install using ``setuptools`` or ``pip``, e.g. (within a virtualenv)::

  $ easy_install pyramid_deform

or::

  $ pip install pyramid_deform

You can also include ``pyramid_deform`` as a ``setup_requires`` dependency
in your ``setuptools``-compatible project.

Once installed, continue with `Configuration`_ of this package.


Configuration
-------------

Basic configuration
^^^^^^^^^^^^^^^^^^^

``pyramid_deform`` provides an ``includeme`` hook that will configure your
``Pyramid`` environment accordingly.  It will:

* Configure and register translations for Deform and Colander
* Configure template search paths for Deform
* Add a static view for the Deform JavaScript and CSS resources

To use this in your project, add ``pyramid_deform`` to the
``pyramid.includes`` in your PasteDeploy configuration file.  For example::

  [myapp:main]
  ...
  pyramid.includes = pyramid_debugtoolbar pyramid_tm pyramid_deform

You may also use the ``include`` method against a Pyramid configurator
(commonly seen as a `config` object) like so::

    def main(global_config, **settings):
        """ This function returns a Pyramid WSGI application.
        """
        config = Configurator(settings=settings)
        config.include('pyramid_deform')
        ...


Configuring template search paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``pyramid_deform`` allows you to add one or more template search paths in its
configuration.  An example::

  [myapp:main]
  ...
  pyramid_deform.template_search_path = myapp:templates/deform
                                        my.extra:templates/deform/default
                                        ...

Thus, if you put a ``form.pt`` into your application's
``templates/deform`` directory, that will override deform's default
``form.pt``. Similarly, if you put another ``form.pt`` into the 
given directory within the ``my.extra`` package, then it will override
the one in your application and the default from deform.

Configuring the static resource view
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once ``pyramid_deform`` has been included in some fashion in your application,
it will register a add a static view for Deform resources. By default, this
static view is configured via
:meth:`pyramid.config.Configurator.add_static_view` with a ``name`` of
``static-deform``.  You can customise this by setting the option
``pyramid_deform.static_path`` within your Pyramid configuration.

This option is to be a string representing an application-relative local URL
prefix for these static resources. It may alternately be a full URL. 


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
      schema = PageSchema()
      buttons = ('save',)
      form_options = (('formid', 'pyramid-deform'),
                      ('method', 'GET'))

      def save_success(self, appstruct):
          context = self.request.context
          context.title = appstruct['title']
          context.description = appstruct['description']
          context.body = appstruct['body']
          self.request.session.flash(u"Your changes have been saved.")
          return HTTPFound(location=self.request.path_url)

      def save_failure(self, e):
          self.request.session.flash(u"You form input was not correct.")
          return self.failure(e)

      def appstruct(self):
          context = self.request.context
          return {'title': context.title,
                  'description': context.description,
                  'body': context.body}


Form input and validation
^^^^^^^^^^^^^^^^^^^^^^^^^

When a request is received from the above view, the ``FormView`` callable
determines what should happen with the request.  The incoming request is
validated against the given form (and thus the schema), and depending on the
button that the user pressed to submit the form, and whether the form input validates or not a certain instance method will be called.  This given method
will be named either ``buttonID_success`` or ``buttonID_failure``, where
``buttonID`` is the identifier of the button pressed and the suffix is
determined on whether the form validated or not.

Considering the above example:

* If the form validator succeeds, then ``save_success`` will be called with
  the correct ``appstruct`` as the first argument.  In the example above, this
  method is not called when the ``title`` is left blank, as it is a required
  field.
  
  Such a method *must* be specified for any given button on the form, if
  any others were specified as part of ``buttons``.

* If the form validator fails, then ``save_failure`` will be called with the
  resulting ``deform.exception.ValidationFailure`` as the first argument.

  If such a named method was not present on the given ``FormView``-derived
  class, then the default action is to call the ``failure(e)`` method, 
  which re-renders the given form with appropriate error messages.

In either ``*_success`` or ``*_failure`` methods, you may find yourself
wanting to re-render the whole ``FormView`` and return this as a response.  For
instance, you may encounter the situation where a user successfully submits a
form, and you want to immediately re-render the given form (rather than sending
a HTTP redirect, for instance).  Likewise, you may like to customise the
response within the given method before it is sent back to the user (for 
instance, to display custom messages or do anything else).

This would typically just involve calling ``self()`` from within a
``save_success`` (or similar) method and returning the response.  However, this
call method checks for buttons present within the request, so you will end up
with infinite recursion as the call method calls the button handler and so
forth.  You can break this cycle by telling ``FormView``'s default call method
to ignore button handlers like so::

    def save_success(self, appstruct):
        response = self(ignore_buttons=True)
        #Do some fancy processing or add things to response
        response['my_variable'] = 'dummy'
        return response


Appstruct
^^^^^^^^^

We use the ``appstruct`` method to pre-fill the form with values from
the page object that we edit (i.e. ``context``).

Form options
^^^^^^^^^^^^

We also provide a ``form_options`` two-tuple -- this structure can contain
any options to be passed as keyword arguments to the form class' ``__init__``
method.  In the case above, we customise the ID for the form using the
``formid`` and ``method`` options but could change the ``action``
and more.  For more details, see 
http://deform.readthedocs.org/en/latest/api.html#deform.Form.

View registration
^^^^^^^^^^^^^^^^^

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

Templating
^^^^^^^^^^

Your template in ``myapp:templates/form.pt`` will receive ``form`` as
a variable: this is the rendered form.  Your template might look
something like this::

  <html>
    <head>
    <!-- CSS -->
    <tal:block repeat="reqt css_links|[]">
      <link rel="stylesheet" 
            href="${request.static_url('deform:static/%s' % reqt)}" 
            type="text/css" />
    </tal:block>
    <!-- JavaScript -->
    <tal:block repeat="reqt js_links|[]">
      <script type="text/javascript"
              src="${request.static_url('deform:static/%s' % reqt)}"
       ></script>
    </tal:block>
    </head>
    <body>
      <h1>Edit ${context.title}</h1>
      <form tal:replace="structure form" />
    </body>
  </html>


Deferred Colander Schemas
-------------------------

``pyramid_deform.FormView`` will `bind
<http://docs.pylonsproject.org/projects/colander/en/latest/binding.html>`_ the
schema by default to the pyramid request. You may wish to bind additional data
to the schema, which you can do by overriding the get_bind_data method in your
subclass, like this::

    class PageEditView(FormView):
        ...

        def get_bind_data(self):
            # ensure we get any base data defined by FormView
            data = super(PageEditView, self).get_bind_data()
            # add any custom data here
            data.update({
                'bind_this_field': 'to this value',
                'and_this_field': 'to this value'
            })
            return data


CSRF Schema
-----------

This schema can be used as a base class in order to protect forms from
`Cross-Site Request Forgery (CSRF)
<http://en.wikipedia.org/wiki/Cross-site_request_forgery>`_ attacks. In
essence, a CSRF is an attack method in which a third party can instruct a
user's browser to execute commands on a target application or site. This can
happen if a user is logged in on your application in one window or tab, and a
malicious third party site instructs the user's browser to submit a form or
action.  Without protection, as the user is authenticated already (likely via
cookie), the action will succeed.

In order to protect against this, this package provides a Colander base
schema :class:`pyramid_deform.CSRFSchema`.  Use the base schema like so to add a CSRF token field to your given schema::

    >>> class LoginSchema(CSRFSchema):
    >>>     pass
    >>> schema = LoginSchema.get_schema(self.request)

When the schema is rendered as part of a :class:`deform.Form`, a CSRF token
(generated using the current ``Pyramid`` ``request.session.get_csrf_token()``
method) will be included, and this token must be received and verified in the
resulting user form submission for the request to be valid.  Without the token,
the request will fail.  As this token is tied to your current session on your
Pyramid application, and generated per-user session, it is almost certain
(short of packet sniffing or other data theft) that an attacker will not have
this token. Thus CSRF attacks are prevented for forms using this schema.

To prevent CSRF attacks across your application, all public-facing forms
should use schemas incorporating this protection.


SessionFileUploadTempStore
--------------------------

A Deform "FileUploadTempStore" which uses the Pyramid sessioning machinery
and files on disk to store file uploads in the case of a validation failure
exists in this package at :class:`pyramid_deform.SessionFileUploadTempStore`.

Usage::

   from pyramid_deform import SessionFileUploadTempStore
   from colander import Schema
   import deform.widget
   import deform.schema
   import colander

   @colander.deferred
   def upload_widget(node, kw):
       request = kw['request']
       tmpstore = SessionFileUploadTempStore(request)
       return deform.widget.FileUploadWidget(tmpstore)

   class FileSchema(Schema):
       file = colander.SchemaNode(
           deform.schema.FileData(),
           widget = upload_widget,
           )

   def aview(request):
       schema = schema.bind(request=request)
       ...

To use the tempstore you will have to put a ``pyramid_deform.tempdir``
setting in your Pyramid's settings (usually in the ``.ini`` file that you use
to start your application).  This must point to an existing directory.  You
must also configure a Pyramid session factory.

Note that the directory named by ``pyramid_deform.tempdir`` will accrue lots
of garbage.  The tempstore doesn't clean up after itself.  You'll need to set
up a cron job or equivalent to delete files older than a day or so from that
directory.

Wizard
------

This package provides a multi-step (multi-schema) form view in
:class:`pyramid_deform.FormWizardView`. Further docuemntation is coming
shortly.

Reporting Bugs / Development Versions
-------------------------------------

Visit https://github.com/Pylons/pyramid_deform/issues to report bugs.
Visit https://github.com/Pylons/pyramid_deform to download development or
tagged versions.

Indices and tables
------------------

* :ref:`modindex`
* :ref:`search`
