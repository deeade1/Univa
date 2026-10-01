import numpy as np
from celery import shared_task
from django.db import transaction
from django.db.models import F

from .models import UserProfile, VideoContent, VideoLike, VideoView
from .utils.embeddings import embed_texts, normalize


@shared_task
def update_video_engagement(video_id):
    """Recalculate engagement rate asynchronously"""
    try:
        video = VideoContent.objects.get(pk=video_id)
        video.recalc_engagement()
    except VideoContent.DoesNotExist:
        return


@shared_task
def recompute_video_vectors(batch_size=200):
    qs = VideoContent.objects.filter(content_vector__isnull=True, published_at__isnull=False)[:batch_size]
    videos = list(qs)
    if not videos:
        return 0

    texts = []
    for v in videos:
        text = " ".join(filter(None, [v.title or "", v.description or "", " ".join(v.hashtags or [])]))
        texts.append(text)

    vecs = embed_texts(texts)  # implement this externally
    with transaction.atomic():
        for v, vec in zip(videos, vecs):
            v.set_content_vector(vec)
            v.save(update_fields=['content_vector'])
    return len(videos)

@shared_task
def recompute_user_vector(user_id, top_n=200):
    user = UserProfile.objects.get(pk=user_id)
    # weight liked videos more, fully watched videos also included
    liked_ids = VideoLike.objects.filter(user=user).select_related('video').values_list('video__id', flat=True)
    recent_views = VideoView.objects.filter(user=user).select_related('video').order_by('-created_at')[:top_n]

    vectors = []
    # liked
    for video_id in liked_ids:
        v = VideoContent.objects.filter(pk=video_id).first()
        if v and v.content_vector:
            vectors.append(np.array(v.content_vector) * 2.0)  # liked weight

    for view in recent_views:
        v = view.video
        if v and v.content_vector:
            # weight by watch_time proportionally (simple heuristic)
            weight = min(3.0, (view.watch_time / max(1.0, getattr(v, 'duration', 1.0))) * 3.0)
            vectors.append(np.array(v.content_vector) * weight)

    if not vectors:
        return None

    avg = np.mean(vectors, axis=0)
    norm = np.linalg.norm(avg) or 1.0
    user.interest_vector = (avg / norm).tolist()
    user.save(update_fields=['interest_vector'])
    return True

@shared_task
def update_video_viral_scores(batch_size=1000):
    from django.utils import timezone
    now = timezone.now()
    videos = VideoContent.objects.filter(published_at__isnull=False).order_by('-created_at')[:batch_size]
    for v in videos:
        # simplified formula
        age_hours = max(1.0, (now - (v.published_at or v.created_at)).total_seconds() / 3600.0)
        # assume engagement_rate is already computed periodically elsewhere
        v.viral_score = ( (v.engagement_rate or 0.0) * (v.likes_count + v.comments_count*2 + v.shares_count*3 + 1) ) / (age_hours ** 0.7)
        v.save(update_fields=['viral_score'])
    return len(videos)

@shared_task
def recompute_all_user_vectors(batch_size=100):
    from .models import UserProfile
    user_ids = list(UserProfile.objects.values_list('id', flat=True)[:batch_size])
    for uid in user_ids:
        recompute_user_vector.delay(uid)
    return len(user_ids)


@shared_task
def recompute_trending_feed(top_n=200):
    """
    Combine viral_score and engagement_rate to build a trending feed cache.
    """
    from accounts.models import UserProfile

    from .models import TrendingFeed, VideoContent

    TrendingFeed.objects.all().delete()  # reset feed (or prune old entries)

    videos = (
        VideoContent.objects.filter(published_at__isnull=False)
        .exclude(viral_score__isnull=True)
        .order_by('-viral_score')[:top_n]
    )

    entries = [
        TrendingFeed(video=v, rank_score=v.viral_score + (v.engagement_rate * 0.3))
        for v in videos
    ]
    TrendingFeed.objects.bulk_create(entries, ignore_conflicts=True)
    return len(entries)

