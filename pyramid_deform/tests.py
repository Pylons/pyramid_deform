# get_step_num
# get_step_states
# clear
# get_step_state
# set_state
# decrement_step
# increment_step

import unittest
from pyramid import testing

class TestFormView(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_deform import FormView
        return FormView
        
    def _makeOne(self, request):
        klass = self._getTargetClass()
        inst = klass(request)
        return inst

    def test___call__show(self):
        schema = DummySchema()
        request = DummyRequest()
        inst = self._makeOne(request)
        inst.schema = schema
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result,
                         {'css_links': (), 'js_links': (), 'form': 'rendered'})

    def test___call__show_result_response(self):
        from webob import Response
        schema = DummySchema()
        request = DummyRequest()
        inst = self._makeOne(request)
        inst.schema = schema
        inst.form_class = DummyForm
        response = Response()
        inst.show = lambda *arg: response
        result = inst()
        self.assertEqual(result, response)

    def test___call__button_in_request(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        inst.submit_success = lambda *x: 'success'
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result, 'success')
        
    def test___call__button_in_request_fail(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        import deform.exception
        def raiseit(*arg):
            raise deform.exception.ValidationFailure(None, None, None)
        inst.submit_success = raiseit
        inst.form_class = DummyForm
        inst.submit_failure = lambda *arg: 'failure'
        result = inst()
        self.assertEqual(result, 'failure')

    def test___call__button_in_request_fail_no_failure_handler(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        import deform.exception
        def raiseit(*arg):
            exc = deform.exception.ValidationFailure(None, None, None)
            exc.render = lambda *arg: 'failure'
            raise exc
        inst.submit_success = raiseit
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result,
                         {'css_links': (), 'js_links': (), 'form': 'failure'})

class TestFormWizardView(unittest.TestCase):
    def _makeOne(self, wizard):
        from pyramid_deform import FormWizardView
        return FormWizardView(wizard)

    def test___call__step_zero_no_schemas(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'done')

    def test___call__step_zero_one_schema(self):
        schema = DummySchema()
        wizard = DummyFormWizard(schema)
        inst = self._makeOne(wizard)
        inst.form_view_class = DummyFormView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'viewed')

    def test___call__prev_not_ok(self):
        schema = DummySchema()
        schema.prev_ok = lambda *arg: False
        wizard = DummyFormWizard(schema)
        inst = self._makeOne(wizard)
        inst.form_view_class = DummyFormView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'viewed')

    def test___call__next_not_ok(self):
        schema = DummySchema()
        schema.next_ok = lambda *arg: False
        wizard = DummyFormWizard(schema)
        inst = self._makeOne(wizard)
        inst.form_view_class = DummyFormView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'viewed')

    def test_show(self):
        from pyramid_deform import WizardState
        form = DummyForm(None)
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        result = inst.show(form)
        self.assertEqual(result, {'form': 'rendered'})
        self.assertEqual(form.appstruct, {})

    def test_show_with_appstruct(self):
        from pyramid_deform import WizardState
        form = DummyForm(None)
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        class DummySchemaWithAppstruct(object):
            appstruct = {'1':'2'}
        inst.schema = DummySchemaWithAppstruct()
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        result = inst.show(form)
        self.assertEqual(result, {'form': 'rendered'})
        self.assertEqual(form.appstruct, {'1':'2'})

    def test_show_with_deserialize(self):
        from pyramid_deform import WizardState
        form = DummyForm(None)
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda *arg: DummySerializer('state2')
        inst.wizard_state = WizardState(request, 'name')
        result = inst.show(form)
        self.assertEqual(result, {'form': 'rendered'})
        self.assertEqual(form.appstruct, 'state2')

    def test_next_success(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        inst.schema = DummySchema()
        result = inst.next_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['step'], 1)
        self.assertEqual(state['states'][0], {'one':'one'})
        self.assertEqual(state['states']['schema'], {'one':'one'})

    def test_next_success_with_serializer(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda *arg: DummySerializer('state2')
        result = inst.next_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['step'], 1)
        self.assertEqual(state['states'][0], 'state2')
        self.assertEqual(state['states']['schema'], 'state2')

    def test_previous_success_at_step_zero(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        inst.schema = DummySchema()
        result = inst.previous_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['states'][0], {'one':'one'})
        self.assertEqual(state['states']['schema'], {'one':'one'})
        self.failIf('step' in state)

    def test_previous_success_at_step_one(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        inst.schema = DummySchema()
        states = inst.request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':1}
        result = inst.previous_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['states'][1], {'one':'one'})
        self.assertEqual(state['states']['schema'], {'one':'one'})
        self.assertEqual(state['step'], 0)

    def test_previous_success_with_serializer(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.wizard_state = WizardState(request, 'name')
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda *arg:DummySerializer('state2')
        result = inst.previous_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['states'][0], 'state2')
        self.assertEqual(state['states']['schema'], 'state2')

    def test_previous_failure_at_step_zero(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.schema = DummySchema()
        inst.wizard_state = WizardState(request, 'name')
        result = inst.previous_failure(None)
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.failIf('step' in state)

    def test_previous_failure_at_step_one(self):
        from pyramid_deform import WizardState
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.schema = DummySchema()
        inst.wizard_state = WizardState(request, 'name')
        states = inst.request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':1}
        result = inst.previous_failure(None)
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['step'], 0)

    def test_get_schema_serializer_no_serializer(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        inst.schema = DummySchema()
        self.assertEqual(inst.get_schema_serializer(), None)

    def test_get_schema_serializer(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda schema: '123'
        self.assertEqual(inst.get_schema_serializer(), '123')

    def test_deserialize(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda *arg: DummySerializer('state2')
        self.assertEqual(inst.deserialize('state'), 'state2')
        
    def test_serialize(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        inst.schema = DummySchema()
        inst.schema.wizard_serializer = lambda *arg: DummySerializer('state2')
        self.assertEqual(inst.serialize('state'), 'state2')
        
class TestWizardState(unittest.TestCase):
    def _makeOne(self, request):
        from pyramid_deform import WizardState
        return WizardState(request, 'name')

    def test__get_wizard_data_no_existing_data(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        data = inst._get_wizard_data()
        self.assertEqual(data, {})
        self.failUnless('name' in request.session['pyramid_deform.wizards'])
        self.failUnless(request.session._changed)

    def test__get_wizard_data_with_existing_data(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        state = {'abc':'123'}
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = state
        inst.request = request
        data = inst._get_wizard_data()
        self.assertEqual(data, state)
        self.failIf(request.session._changed)

    def test_clear(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        state = {'abc':'123'}
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = state
        inst.request = request
        inst.clear()
        self.assertEqual(request.session['pyramid_deform.wizards']['name'], {})

    def test_clear_get_step_num_from_params(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        request.GET['step'] = '1'
        inst.request = request
        self.assertEqual(inst.get_step_num(), 1)

    def test_clear_get_step_num_from_session(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':'1'}
        inst.request = request
        self.assertEqual(inst.get_step_num(), 1)

    def test_set_step_num(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        inst.request = request
        inst.set_step_num(5)
        self.assertEqual(inst.get_step_num(), 5)

    def test_get_step_states(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':'states', 'step':0}
        inst.request = request
        self.assertEqual(inst.get_step_states(), 'states')

    def test_get_step_state(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':{0:'state'}, 'step':0}
        inst.request = request
        self.assertEqual(inst.get_step_state(), 'state')

    def test_get_step_state_nondefault(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        request.session['pyramid_deform.wizards'] = {}
        inst.request = request
        self.assertEqual(inst.get_step_state('123'), '123')

    def test_set_step_state(self):
        request = DummyRequest()
        inst = self._makeOne(request)
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':{0:'state'}, 'step':0}
        inst.request = request
        inst.set_step_state(0, 'schema', 'state2')
        self.assertEqual(states['name']['states'][0], 'state2')
        self.assertEqual(states['name']['states']['schema'], 'state2')

class TestFormWizard(unittest.TestCase):
    def _makeOne(self, name, done, *schemas):
        from pyramid_deform import FormWizard
        return FormWizard(name, done, *schemas)
    
    def test___call__(self):
        inst = self._makeOne('name', None, 'schema1', 'schema2')
        inst.form_wizard_view_class = DummyFormWizardView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result.wizard, inst)

    def test_get_summary(self):
        schema1 = DummySchema()
        schema2 = DummySchema()
        inst = self._makeOne('name', None, schema1, schema2)
        request = DummyRequest()
        summary = inst.get_summary(request)
        self.assertEqual(
            summary,
            [{'current': True,
              'num': 0,
              'last': False,
              'name': 'schema',
              'title': 'title',
              'url': 'http://example.com?step=0',
              'first': True,
              'class': 'first hilight',
              'desc': 'desc'},
             {'current': False,
              'num': 1,
              'last': True,
              'name': 'schema',
              'title': 'title',
              'url': 'http://example.com?step=1',
              'first': False,
              'class': 'last',
              'desc': 'desc'}
             ])

class TestCRSFSchema(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_deform import CSRFSchema
        return CSRFSchema

    def _makeOne(self):
        return self._getTargetClass()()

    def test_validate_failure(self):
        from colander import Invalid
        inst = self._makeOne()
        request = DummyRequest()
        inst2 = inst.bind(request=request)
        self.assertRaises(Invalid, inst2.deserialize, {'csrf_token':''})

    def test_validate_missing(self):
        from colander import Invalid
        inst = self._makeOne()
        request = DummyRequest()
        inst2 = inst.bind(request=request)
        self.assertRaises(Invalid, inst2.deserialize, {})

    def test_validate_success(self):
        inst = self._makeOne()
        request = DummyRequest()
        inst2 = inst.bind(request=request)
        self.assertEqual(inst2.deserialize({'csrf_token':'csrf_token'}),
                         {'csrf_token': 'csrf_token'})
        
class DummyForm(object):
    def __init__(self, schema, buttons=None, use_ajax=False, ajax_options=''):
        self.schema = schema
        self.buttons = buttons
        self.use_ajax = use_ajax
        self.ajax_options = ajax_options

    def get_widget_resources(self):
        return {'js':(), 'css':()}

    def render(self, appstruct=None):
        self.appstruct = appstruct
        return 'rendered'

    def validate(self, controls):
        return 'validated'

class DummySchema(object):
    name = 'schema'
    description = 'desc'
    title = 'title'
    
    def bind(self, **kw):
        self.kw = kw
        return self
    
class DummyButton(object):
    def __init__(self, name):
        self.name = name
        
class DummyFormWizardView(object):
    def __init__(self, wizard):
        self.wizard = wizard

    def __call__(self, request):
        return self
    
class DummyFormWizard(object):
    name = 'name'
    def __init__(self, *schemas):
        self.schemas = schemas

    def done(self, request, states):
        return 'done'

class DummySession(dict):
    _changed = False
    def changed(self):
        self._changed = True

    def get_csrf_token(self):
        return 'csrf_token'

class DummyRequest(testing.DummyRequest):
    def __init__(self, *arg, **kw):
        testing.DummyRequest.__init__(self, *arg, **kw)
        self.session = DummySession()
    
class DummyFormView(object):
    def __init__(self, request):
        self.request = request

    def __call__(self):
        return 'viewed'
        

class DummySerializer(object):
    def __init__(self, result):
        self.result = result

    def deserialize(self, state):
        return self.result

    def serialize(self, state):
        return self.result
