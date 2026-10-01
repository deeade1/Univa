# community/signals.py
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from social.models import (VideoComment, VideoContent, VideoLike, VideoShare,
                           VideoView)
from social.tasks import update_video_engagement


@receiver(post_save, sender=VideoLike)
def handle_like_created(sender, instance, created, **kwargs):
    if created:
        VideoContent.objects.filter(id=instance.video_id).update(likes_count=F('likes_count') + 1)
        update_video_engagement.delay(str(instance.video_id))


@receiver(post_delete, sender=VideoLike)
def handle_like_deleted(sender, instance, **kwargs):
    VideoContent.objects.filter(id=instance.video_id).update(likes_count=F('likes_count') - 1)
    update_video_engagement.delay(str(instance.video_id))


@receiver(post_save, sender=VideoComment)
def handle_comment_created(sender, instance, created, **kwargs):
    if created:
        VideoContent.objects.filter(id=instance.video_id).update(comments_count=F('comments_count') + 1)
        update_video_engagement.delay(str(instance.video_id))


@receiver(post_delete, sender=VideoComment)
def handle_comment_deleted(sender, instance, **kwargs):
    VideoContent.objects.filter(id=instance.video_id).update(comments_count=F('comments_count') - 1)
    update_video_engagement.delay(str(instance.video_id))


@receiver(post_save, sender=VideoView)
def handle_view_created(sender, instance, created, **kwargs):
    if created:
        VideoContent.objects.filter(id=instance.video_id).update(views_count=F('views_count') + 1)
        update_video_engagement.delay(str(instance.video_id))


@receiver(post_save, sender=VideoShare)
def handle_share_created(sender, instance, created, **kwargs):
    if created:
        VideoContent.objects.filter(id=instance.video_id).update(shares_count=F('shares_count') + 1)
        update_video_engagement.delay(str(instance.video_id))


@receiver(post_save, sender=VideoLike)
def increment_likes(sender, instance, created, **kwargs):
    if created:
        instance.video.adjust_like_count(1)

@receiver(post_delete, sender=VideoLike)
def decrement_likes(sender, instance, **kwargs):
    instance.video.adjust_like_count(-1)


