import importlib
import os


def render_ts_accessor(*args, **kwargs):
    """Get template from env var TSGEN_TEMPLATE_MODULE

    Falls back to tsgen.output_templates.fetch if no env var is set
    """
    template_module_name = os.environ.get("TSGEN_TEMPLATE_MODULE")
    if template_module_name:
        mod = importlib.import_module(template_module_name)
    else:
        import tsgen.output_templates.fetch as mod

    return mod.render_ts_accessor(*args, **kwargs)
