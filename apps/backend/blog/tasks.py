# tasks.py - Celery Tasks for Banking App

import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from blog.models import Comment, Post, Reply, Tag
from graphq.blog.mutations import (CommentCreate, CommentDelete, CommentUpdate,
                                   PostCreate, PostDelete, PostUpdate,
                                   ReplyCreate, ReplyDelete, ReplyUpdate,
                                   TagCreate, TagDelete)

logger = logging.getLogger(__name__)
User = get_user_model()

# Email notification tasks
@shared_task(bind=True, max_retries=3)
def send_notification_email(self, subject, message, recipient_list):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise self.retry(exc=e, countdown=60)

# Tag related tasks
@shared_task
def create_tag_task(name):
    try:
        with transaction.atomic():
            tag = Tag.objects.create(name=name)
            logger.info(f"Tag created: {tag.name}")
            return str(tag.id)
    except Exception as e:
        logger.error(f"Failed to create tag: {e}")
        raise

@shared_task
def delete_tag_task(tag_id):
    try:
        with transaction.atomic():
            tag = Tag.objects.get(pk=tag_id)
            tag.delete()
            logger.info(f"Tag deleted: {tag_id}")
            return True
    except Tag.DoesNotExist:
        logger.warning(f"Tag not found: {tag_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete tag: {e}")
        raise

# Post related tasks
@shared_task
def create_post_task(post_data, author_id, tag_ids=None):
    try:
        with transaction.atomic():
            author = User.objects.get(pk=author_id)
            post = Post.objects.create(author=author, **post_data)

            if tag_ids:
                tags = Tag.objects.filter(id__in=tag_ids)
                post.tags.set(tags)

            logger.info(f"Post created: {post.title}")

            send_notification_email.delay(
                subject="New Post Created",
                message=f"Your post '{post.title}' has been created successfully.",
                recipient_list=[author.email]
            )

            return str(post.id)
    except Exception as e:
        logger.error(f"Failed to create post: {e}")
        raise

@shared_task
def update_post_task(post_id, update_data, tag_ids=None):
    try:
        with transaction.atomic():
            post = Post.objects.get(pk=post_id)

            for field, value in update_data.items():
                setattr(post, field, value)

            if tag_ids is not None:
                tags = Tag.objects.filter(id__in=tag_ids)
                post.tags.set(tags)

            post.save()
            logger.info(f"Post updated: {post.title}")
            return True
    except Post.DoesNotExist:
        logger.warning(f"Post not found: {post_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to update post: {e}")
        raise

@shared_task
def delete_post_task(post_id):
    try:
        with transaction.atomic():
            post = Post.objects.get(pk=post_id)
            title = post.title
            author_email = post.author.email
            post.delete()

            logger.info(f"Post deleted: {post_id}")

            send_notification_email.delay(
                subject="Post Deleted",
                message=f"Your post '{title}' has been deleted.",
                recipient_list=[author_email]
            )

            return True
    except Post.DoesNotExist:
        logger.warning(f"Post not found: {post_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete post: {e}")
        raise

# Comment related tasks
@shared_task
def create_comment_task(post_id, comment_data, author_id=None):
    try:
        with transaction.atomic():
            post = Post.objects.get(pk=post_id)

            if author_id:
                author = User.objects.get(pk=author_id)
                comment_data['author'] = author

            comment = Comment.objects.create(post=post, **comment_data)

            logger.info(f"Comment created on post: {post.title}")

            if post.author.email:
                send_notification_email.delay(
                    subject="New Comment on Your Post",
                    message=f"A new comment was added to your post '{post.title}'.",
                    recipient_list=[post.author.email]
                )

            return str(comment.id)
    except Exception as e:
        logger.error(f"Failed to create comment: {e}")
        raise

@shared_task
def update_comment_task(comment_id, update_data):
    try:
        with transaction.atomic():
            comment = Comment.objects.get(pk=comment_id)

            for field, value in update_data.items():
                setattr(comment, field, value)

            comment.save()
            logger.info(f"Comment updated: {comment_id}")
            return True
    except Comment.DoesNotExist:
        logger.warning(f"Comment not found: {comment_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to update comment: {e}")
        raise

@shared_task
def delete_comment_task(comment_id):
    try:
        with transaction.atomic():
            comment = Comment.objects.get(pk=comment_id)
            post_title = comment.post.title
            comment.delete()

            logger.info(f"Comment deleted: {comment_id}")
            return True
    except Comment.DoesNotExist:
        logger.warning(f"Comment not found: {comment_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete comment: {e}")
        raise

# Reply related tasks
@shared_task
def create_reply_task(comment_id, reply_data, author_id=None):
    try:
        with transaction.atomic():
            comment = Comment.objects.get(pk=comment_id)

            if author_id:
                author = User.objects.get(pk=author_id)
                reply_data['author'] = author

            reply = Reply.objects.create(comment=comment, **reply_data)

            logger.info(f"Reply created on comment: {comment_id}")

            if comment.author.email:
                send_notification_email.delay(
                    subject="New Reply to Your Comment",
                    message=f"A new reply was added to your comment on '{comment.post.title}'.",
                    recipient_list=[comment.author.email]
                )

            return str(reply.id)
    except Exception as e:
        logger.error(f"Failed to create reply: {e}")
        raise

@shared_task
def update_reply_task(reply_id, update_data):
    try:
        with transaction.atomic():
            reply = Reply.objects.get(pk=reply_id)

            for field, value in update_data.items():
                setattr(reply, field, value)

            reply.save()
            logger.info(f"Reply updated: {reply_id}")
            return True
    except Reply.DoesNotExist:
        logger.warning(f"Reply not found: {reply_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to update reply: {e}")
        raise

@shared_task
def delete_reply_task(reply_id):
    try:
        with transaction.atomic():
            reply = Reply.objects.get(pk=reply_id)
            reply.delete()

            logger.info(f"Reply deleted: {reply_id}")
            return True
    except Reply.DoesNotExist:
        logger.warning(f"Reply not found: {reply_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete reply: {e}")
        raise

# GraphQL mutation wrappers
@shared_task
def execute_tag_create_mutation(name):
    return TagCreate.mutate_and_get_payload(None, None, name=name)

@shared_task
def execute_tag_delete_mutation(tag_id):
    return TagDelete.mutate_and_get_payload(None, None, id=tag_id)

@shared_task
def execute_post_create_mutation(post_data):
    return PostCreate.mutate_and_get_payload(None, None, **post_data)

@shared_task
def execute_post_update_mutation(post_id, update_data):
    return PostUpdate.mutate_and_get_payload(None, None, id=post_id, **update_data)

@shared_task
def execute_post_delete_mutation(post_id):
    return PostDelete.mutate_and_get_payload(None, None, id=post_id)

@shared_task
def execute_comment_create_mutation(comment_data):
    return CommentCreate.mutate_and_get_payload(None, None, **comment_data)

@shared_task
def execute_comment_update_mutation(comment_id, update_data):
    return CommentUpdate.mutate_and_get_payload(None, None, id=comment_id, **update_data)

@shared_task
def execute_comment_delete_mutation(comment_id):
    return CommentDelete.mutate_and_get_payload(None, None, id=comment_id)

@shared_task
def execute_reply_create_mutation(reply_data):
    return ReplyCreate.mutate_and_get_payload(None, None, **reply_data)

@shared_task
def execute_reply_update_mutation(reply_id, update_data):
    return ReplyUpdate.mutate_and_get_payload(None, None, id=reply_id, **update_data)

@shared_task
def execute_reply_delete_mutation(reply_id):
    return ReplyDelete.mutate_and_get_payload(None, None, id=reply_id)

# Scheduled tasks
@shared_task
def publish_scheduled_posts():
    try:
        from django.utils import timezone
        now = timezone.now()

        posts_to_publish = Post.objects.filter(
            publish_date__lte=now,
            published=False
        )

        count = posts_to_publish.update(published=True)

        logger.info(f"Published {count} scheduled posts")
        return count
    except Exception as e:
        logger.error(f"Failed to publish scheduled posts: {e}")
        raise

@shared_task
def cleanup_unapproved_comments(days_old=30):
    try:
        from django.db.models import Q
        from django.utils import timezone

        cutoff_date = timezone.now() - timezone.timedelta(days=days_old)

        comments_to_delete = Comment.objects.filter(
            Q(is_approved=False) &
            Q(created_at__lte=cutoff_date)
        )

        count, _ = comments_to_delete.delete()

        logger.info(f"Deleted {count} old unapproved comments")
        return count
    except Exception as e:
        logger.error(f"Failed to cleanup unapproved comments: {e}")
        raise
