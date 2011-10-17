import colander
from deform import widget

from pyramid.i18n import TranslationString

@colander.deferred
def deferred_csrf(node, kw):
    return kw['csrf']

@colander.deferred
def deferred_validate(node, kw):
    val = lambda x: x == kw['csrf']
    return colander.Function(val, message=TranslationString('Invalid'))


class CSRFSchema(colander.Schema):
    """
    Generates and Validates a CSRF Token
    """
    @classmethod
    def get_schema(cls, request):
        instance = cls()
        return instance.bind(csrf=request.session.get_csrf_token())


    csrf_token = colander.SchemaNode(colander.String(),
            widget=widget.HiddenWidget(),
            default=deferred_csrf,
            validator=deferred_validate)

