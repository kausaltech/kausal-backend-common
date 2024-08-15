from wagtail.documents.models import AbstractDocument

def get_document_model_string() -> str:
    """
    Get the dotted ``app.Model`` name for the document model as a string.
    Useful for developers making Wagtail plugins that need to refer to the
    document model, such as in foreign keys, but the model itself is not required.
    """

def get_document_model() -> type[AbstractDocument]:
    """
    Get the document model from the ``WAGTAILDOCS_DOCUMENT_MODEL`` setting.
    Defaults to the standard :class:`~wagtail.documents.models.Document` model
    if no custom model is defined.
    """
