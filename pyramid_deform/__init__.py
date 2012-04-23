import os
import binascii

from pkg_resources import resource_filename

import colander
import deform
import deform.form
import deform.exception
import deform.widget
from deform.form import Button

from pyramid.exceptions import ConfigurationError
from pyramid.httpexceptions import HTTPFound
from pyramid.i18n import get_localizer
from pyramid.i18n import TranslationStringFactory
from pyramid.threadlocal import get_current_request

_ = TranslationStringFactory('pyramid_deform')

class FormView(object):
    form_class = deform.form.Form
    buttons = ()
    schema = None

    def __init__(self, request):
        self.request = request

    def __call__(self):
        use_ajax = getattr(self, 'use_ajax', False)
        ajax_options = getattr(self, 'ajax_options', '{}')
        self.schema = self.schema.bind(request=self.request)
        form = self.form_class(self.schema, buttons=self.buttons,
                               use_ajax=use_ajax, ajax_options=ajax_options)
        self.before(form)
        reqts = form.get_widget_resources()
        result = None

        for button in form.buttons:
            if button.name in self.request.POST:
                success_method = getattr(self, '%s_success' % button.name)
                try:
                    controls = self.request.POST.items()
                    validated = form.validate(controls)
                    result = success_method(validated)
                except deform.exception.ValidationFailure, e:
                    fail = getattr(self, '%s_failure' % button.name, None)
                    if fail is None:
                        fail = self.failure
                    result = fail(e)
                break

        if result is None:
            result = self.show(form)

        if isinstance(result, dict):
            result['js_links'] = reqts['js']
            result['css_links'] = reqts['css']

        return result

    def before(self, form):
        pass

    def failure(self, e):
        return {
            'form':e.render(),
            }

    def show(self, form):
        return {
            'form':form.render(),
            }

class WizardState(object):
    def __init__(self, request, wizard_name):
        self.wizard_name = wizard_name
        self.request = request

    def _get_wizard_data(self):
        session = self.request.session
        wizdatas = session.setdefault('pyramid_deform.wizards', {})
        wizdata = wizdatas.get(self.wizard_name, None)
        if wizdata is None:
            wizdata = {}
            wizdatas[self.wizard_name] = wizdata
            session.changed()
        return wizdata

    def clear(self):
        wizdata = self._get_wizard_data()
        wizdata.clear()
        self.request.session.changed()

    def get_step_num(self):
        step = self.request.GET.get('step')
        if step is not None:
            step = int(step)
            self.set_step_num(step)
        else:
            wizdata = self._get_wizard_data()
            step = wizdata.get('step', 0)
        return int(step)

    def set_step_num(self, num):
        wizdata = self._get_wizard_data()
        wizdata['step'] = num
        self.request.session.changed()

    def get_step_states(self):
        wizdata = self._get_wizard_data()
        states = wizdata.setdefault('states', {})
        return states

    def get_step_state(self, default=None):
        if default is None:
            default = {}
        states = self.get_step_states()
        step = self.get_step_num()
        return states.get(step, default)

    def set_step_state(self, num, name, state):
        states = self.get_step_states()
        states[num] = state
        states[name] = state
        self.request.session.changed()

    def decrement_step(self):
        step = self.get_step_num()
        if step > 0:
            self.set_step_num(step-1)

    def increment_step(self):
        step = self.get_step_num()
        self.set_step_num(step+1)

    def set_state(self, name, state):
        step = self.get_step_num()
        self.set_step_state(step, name, state)

class FormWizardView(object):

    form_view_class = FormView
    wizard_state_class = WizardState
    schema = None

    def __init__(self, wizard):
        self.wizard = wizard

    def __call__(self, request):
        self.request = request
        self.wizard_state = self.wizard_state_class(request, self.wizard.name)
        step = self.wizard_state.get_step_num()
        
        if step > len(self.wizard.schemas)-1:
            states = self.wizard_state.get_step_states()
            result = self.wizard.done(request, states)
            self.wizard_state.clear()
            return result
        form_view = self.form_view_class(request)
        schema = self.wizard.schemas[step]
        self.schema = schema.bind(request=request)
        form_view.schema = self.schema
        buttons = []

        prev_disabled = False
        next_disabled = False

        if hasattr(schema, 'prev_ok'):
            prev_disabled = not schema.prev_ok(request)

        if hasattr(schema, 'next_ok'):
            next_disabled = not schema.next_ok(request)

        prev_button = Button(name='previous', title='Previous',
                             disabled=prev_disabled)
        next_button = Button(name='next', title='Next',
                             disabled=next_disabled)
        done_button = Button(name='next', title='Done',
                             disabled=next_disabled)

        if step > 0:
            buttons.append(prev_button)

        if step < len(self.wizard.schemas)-1:
            buttons.append(next_button)
        else:
            buttons.append(done_button)

        form_view.buttons = buttons
        form_view.next_success = self.next_success
        form_view.previous_success = self.previous_success
        form_view.previous_failure = self.previous_failure
        form_view.show = self.show
        form_view.appstruct = getattr(schema, 'appstruct', None)
        result = form_view()
        return result

    def get_schema_serializer(self):
        serializer = getattr(self.schema, 'wizard_serializer', None)
        if serializer is not None:
            return serializer(self.schema)
        return None

    def deserialize(self, state):
        serializer = self.get_schema_serializer()
        if serializer is not None:
            state = serializer.deserialize(state)
        return state 

    def serialize(self, state):
        serializer = self.get_schema_serializer()
        if serializer is not None:
            state = serializer.serialize(state)
        return state

    def show(self, form):
        appstruct = getattr(self.schema, 'appstruct', None)
        state = self.wizard_state.get_step_state(appstruct)
        state = self.deserialize(state)
        result = dict(form=form.render(appstruct=state))
        return result

    def next_success(self, validated):
        validated = self.serialize(validated)
        self.wizard_state.set_state(self.schema.name, validated)
        self.wizard_state.increment_step()
        return HTTPFound(location = self.request.path_url)

    def previous_success(self, validated):
        validated = self.serialize(validated)
        self.wizard_state.set_state(self.schema.name, validated)
        self.wizard_state.decrement_step()
        return HTTPFound(location = self.request.path_url)

    def previous_failure(self, e):
        self.wizard_state.decrement_step()
        return HTTPFound(location = self.request.path_url)

class FormWizard(object):
    form_wizard_view_class = FormWizardView # for testing
    wizard_state_class = WizardState
    
    def __init__(self, name, done, *schemas):
        self.name = name
        self.done = done
        self.schemas = schemas

    def __call__(self, request):
        view = self.form_wizard_view_class(self)
        result = view(request)
        return result

    def get_summary(self, request):
        result = []
        state = WizardState(request, self.name)
        step = state.get_step_num()
        last = len(self.schemas) - 1
        for num, schema in enumerate(self.schemas):
            classes = []
            is_first = num == 0
            is_last = num == last
            is_current = num == step
            if is_first:
                classes.append('first')
            if is_last:
                classes.append('last')
            if is_current:
                classes.append('hilight')
            result.append({
                'num':num,
                'name':schema.name,
                'title':schema.title,
                'desc':schema.description,
                'current':step == num,
                'url':request.path_url + '?step=%s' % num,
                'first':is_first,
                'last':is_last,
                'class':' '.join(classes),
                })
        return result

@colander.deferred
def deferred_csrf_value(node, kw):
    return kw['request'].session.get_csrf_token()

@colander.deferred
def deferred_csrf_validator(node, kw):
    def csrf_validate(node, value):
        if value != kw['request'].session.get_csrf_token():
            raise colander.Invalid(node,
                                   _('Invalid cross-site scripting token'))
    return csrf_validate

class CSRFSchema(colander.Schema):
    """
    Schema base class which generates and validates a CSRF token
    automatically.  You must use it like so:

    .. code-block:: python

      from pyramid_deform import CSRFSchema
      import colander

      class MySchema(CRSFSchema):
          my_value = colander.SchemaNode(colander.String())

      And in your application code, *bind* the schema, passing the request
      as a keyword argument:

      .. code-block:: python

        def aview(request):
            schema = MySchema().bind(request=request)

      In order for the CRSFSchema to work, you must configure a *session
      factory* in your Pyramid application.
    """
    csrf_token = colander.SchemaNode(
        colander.String(),
        widget=deform.widget.HiddenWidget(),
        default=deferred_csrf_value,
        validator=deferred_csrf_validator,
        )

def translator(term):
    request = get_current_request()
    if request is not None:
        return get_localizer(request).translate(term)
    else:
        return term.interpolate() if hasattr(term, 'interpolate') else term

def configure_zpt_renderer(search_path=()):
    default_paths = deform.form.Form.default_renderer.loader.search_path
    paths = []
    for path in search_path:
        pkg, resource_name = path.split(':')
        paths.append(resource_filename(pkg, resource_name))
    deform.form.Form.default_renderer = deform.ZPTRendererFactory(
        tuple(paths) + default_paths, translator=translator)

_marker = object()

class SessionFileUploadTempStore(object):
    def __init__(self, request):
        try:
            self.tempdir = request.registry.settings['pyramid_deform.tempdir']
        except KeyError:
            raise ConfigurationError(
                'To use SessionFileUploadTempStore, you must set a  '
                '"pyramid_deform.tempdir" key in your Pyramid settings. It '
                'points to a directory which will temporarily '
                'hold uploaded files when form validation fails.')
        self.request = request
        self.session = request.session
        self.tempstore = self.session.setdefault('pyramid_deform.tempstore', {})
        
    def preview_url(self, uid):
        return None

    def __contains__(self, name):
        return name in self.tempstore

    def __setitem__(self, name, data):
        stream = data.get('fp', None)

        if stream is not None:
            while True:
                randid = binascii.hexlify(os.urandom(20))
                fn = os.path.join(self.tempdir, randid)
                if not os.path.exists(fn):
                    # XXX race condition
                    fp = open(fn, 'w+b')
                    break
            for chunk in chunks(stream):
                fp.write(chunk)
            data['fp'] = fn

        self.tempstore[name] = data
        self.session.changed()

    def get(self, name, default=None):
        data = self.tempstore.get(name)

        if data is None:
            return default

        data = data.copy()
            
        fp = data.get('fp', None)

        if isinstance(fp, basestring):
            try:
                fp = open(fp, 'rb')
            except IOError: # pragma: no cover
                fp = None
            data['fp'] = fp

        return data

    def __getitem__(self, name):
        data = self.get(name, _marker)
        if data is _marker:
            raise KeyError(name)
        return data

def chunks(stream, chunk_size=10000):
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        yield chunk


def includeme(config):
    settings = config.registry.settings
    search_path = settings.get(
        'pyramid_deform.template_search_path', '').strip()

    config.add_translation_dirs('colander:locale', 'deform:locale')
    config.add_static_view('static-deform', 'deform:static')

    configure_zpt_renderer(search_path.split())
