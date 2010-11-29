import deform
import deform.form
import deform.exception
from deform.form import Button

from pyramid.httpexceptions import HTTPFound

class FormView(object):
    form_class = deform.form.Form
    buttons = ()
    schema = None

    def __init__(self, request):
        self.request = request

    def __call__(self):
        use_ajax = getattr(self, 'use_ajax', False)
        ajax_options = getattr(self, 'ajax_options', '')
        schema = self.schema.bind(request=self.request)
        form = self.form_class(schema, buttons=self.buttons, use_ajax=use_ajax,
                               ajax_options=ajax_options)
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

class FormWizardView(object):

    form_view_class = FormView

    def __init__(self, wizard):
        self.wizard = wizard

    def __call__(self, request):
        self.request = request
        step = self.get_step_num()
        if step > len(self.wizard.schemas)-1:
            states = self.get_step_states()
            result = self.wizard.done(request, states)
            self.clear_wizard_data()
            return result
        form_view = self.form_view_class(request)
        schema = self.wizard.schemas[step]
        form_view.schema = schema
        buttons = []
        if step > 0: # pragma: no cover
            buttons.append(Button(name='previous', title='Previous'))
        if step < len(self.wizard.schemas)-1: # pragma: no cover
            buttons.append(Button(name='next', title='Next'))
        else:
            buttons.append(Button(name='next', title='Done'))
        form_view.buttons = buttons
        form_view.next_success = self.next_success
        form_view.previous_success = self.previous_success
        form_view.previous_failure = self.previous_failure
        form_view.show = self.show
        result = form_view()
        return result

    def show(self, form):
        state = self.get_step_state()
        return {
            'form':form.render(appstruct=state)
            }

    def next_success(self, validated):
        step = self.get_step_num()
        self.set_step_state(step, validated)
        self.set_step_num(step+1)
        return HTTPFound(location = self.request.url)

    def previous_success(self, validated):
        step = self.get_step_num()
        self.set_step_state(step, validated)
        if step > 0:
            self.set_step_num(step-1)
        return HTTPFound(location = self.request.url)

    def previous_failure(self, e):
        step = self.get_step_num()
        if step > 0:
            self.set_step_num(step-1)
        return HTTPFound(location = self.request.url)

    def _get_wizard_data(self):
        wizdatas = self.request.session.setdefault('pyramid_deform.wizards', {})
        wizdata = wizdatas.get(self.wizard.name, None)
        if wizdata is None:
            wizdata = {}
            wizdatas[self.wizard.name] = wizdata
            self.request.session.changed()
        return wizdata

    def clear_wizard_data(self):
        wizdata = self._get_wizard_data()
        wizdata.clear()
        self.request.session.changed()

    def get_step_num(self):
        step = self.request.GET.get('step')
        if step is None:
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

    def get_step_state(self):
        states = self.get_step_states()
        step = self.get_step_num()
        return states.get(step, {})

    def set_step_state(self, num, state):
        states = self.get_step_states()
        states[num] = state
        self.request.session.changed()

class FormWizard(object):
    form_wizard_view_class = FormWizardView # for testing
    
    def __init__(self, name, done, *schemas):
        self.name = name
        self.schemas = schemas
        self._done = done

    def __call__(self, request):
        view = self.form_wizard_view_class(self)
        result = view(request)
        return result

    def done(self, request, validated):
        wizdata = request.session.setdefault('pyramid_deform.wizards', {})
        if self.name in wizdata:
            del wizdata[self.name]
            request.session.changed()
        return self._done(request, validated)
    
    
        
    
