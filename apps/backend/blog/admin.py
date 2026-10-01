from django.contrib import admin

from blog.models import Comment, Post, Reply, Tag

# ===================================
# BLOG ADMIN REGISTRATIONS
# ===================================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'subtitle', 'slug', 'publish_date', 'published')
    list_filter = ('published', 'publish_date')
    list_editable = ('title', 'subtitle', 'slug', 'publish_date', 'published')
    search_fields = ('title', 'subtitle', 'slug', 'body')
    prepopulated_fields = {'slug': ('title', 'subtitle')}
    date_hierarchy = 'publish_date'
    save_on_top = True
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-publish_date',)

# blog/admin.py

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author__first_name', 'post__title', 'body')
    readonly_fields = ('created_at', 'updated_at')
    
@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('author', 'comment', 'created_at', 'is_approved')  # Changed author_name to author
    list_filter = ('is_approved', 'created_at')
    search_fields = ('author__first_name', 'comment__post__title', 'body')
    readonly_fields = ('created_at',)  # Removed updated_at if it doesn't exist