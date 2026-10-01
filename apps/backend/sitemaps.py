from django.contrib.sitemaps import GenericSitemap, Sitemap
from django.urls import reverse

from blog.models import Post

from .models import ServiceRequest  # Only if you have public pages


# For React static routes (e.g., '/about', '/contact')
class ReactStaticSitemap(Sitemap):
    priority = 0.5
    changefreq = "weekly"

    def items(self):
        return ["home", "about", "contact"]  # Names matching Django URL patterns
    
    def location(self, item):
        return reverse(item)

# For database-driven routes (e.g., blog posts)
blog_sitemap = GenericSitemap(
    {"queryset": Post.objects.published(), "date_field": "publish_date"},
    priority=0.7,
)

sitemaps = {
    "static": ReactStaticSitemap(),
    "blog": blog_sitemap,
} 


class PublicServiceSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ServiceRequest.objects.filter(
            is_public=True  # Add this field to your model
        ).exclude(status='cancelled')

    def lastmod(self, obj):
        return obj.updated_at

sitemaps = {
    'static': StaticPagesSitemap,  # From previous example
    'services': PublicServiceSitemap,
}