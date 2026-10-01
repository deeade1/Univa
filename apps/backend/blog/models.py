from django.conf import settings
from django.contrib.postgres.indexes import BTreeIndex
from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            BTreeIndex(fields=['name'], name='tag_name_idx'),
        ]

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=255, unique=True)
    subtitle = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    body = models.TextField()
    meta_description = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(blank=True, null=True, db_index=True)
    published = models.BooleanField(default=False, db_index=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        db_index=True
    )
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        ordering = ["-publish_date", "-created_at", "title"]
        indexes = [
            
            # For common query patterns
            BTreeIndex(fields=['published', 'publish_date'], name='post_published_date_idx'),
            BTreeIndex(fields=['author', 'published'], name='post_author_published_idx'),
            
            # For admin/site management
            BTreeIndex(fields=['created_at'], name='post_created_at_idx'),
            BTreeIndex(fields=['updated_at'], name='post_updated_at_idx'),
        ]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name="comments",
        db_index=True
    )
    name = models.CharField(max_length=100, null=True, blank=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        db_index=True
    )
    is_approved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at", "post", "name"]
        indexes = [
            # For comment moderation
            BTreeIndex(fields=['is_approved', 'created_at'], name='comment_approved_date_idx'),
            
            
            # For user-specific queries
            BTreeIndex(fields=['author', 'is_approved'], name='comment_author_approved_idx'),
            
            # For post-specific comment queries
            BTreeIndex(fields=['post', 'is_approved', 'created_at'], name='comment_post_approved_date_idx'),
        ]

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"


class Reply(models.Model):
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        related_name="replies",
        db_index=True
    )
    name = models.CharField(max_length=200, null=True, blank=False)
    is_approved = models.BooleanField(default=False, db_index=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        db_index=True
    )

    class Meta:
        ordering = ["-created_at", "comment", "name"]
        indexes = [
            # For reply moderation
            BTreeIndex(fields=['is_approved', 'created_at'], name='reply_approved_date_idx'),

            
            # For comment thread navigation
            BTreeIndex(fields=['comment', 'created_at'], name='reply_comment_date_idx'),
            
            # For user-specific reply queries
            BTreeIndex(fields=['author', 'is_approved'], name='reply_author_approved_idx'),
        ]

    def __str__(self):
        return f"Reply by {self.name} to {self.comment.post.title}"