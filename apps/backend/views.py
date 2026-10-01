# views.py
from django_react.render import render_react


def seo_friendly_view(request, slug):
    return render_react(
        request,
        title="Dynamic SEO Title",
        description="Custom meta description",
        props={'serviceData': your_serialized_data}
    )