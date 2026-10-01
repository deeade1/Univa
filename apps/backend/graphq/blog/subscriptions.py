# apps/backend/graphq/blog/subscriptions.py
'''import graphene
from django.utils import timezone
from graphql_relay import from_global_id

from blog.models import Comment, Post, Reply, Tag
from graphq.accounts.types import UserNode
from graphq.blog.types import CommentNode, PostNode, ReplyNode, TagNode
from graphq.subscriptions.subscription import Subscription

# ----------------------------------------------------------------------
# 📝 POST SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPostCreated(Subscription):
    class Arguments:
        author_id = graphene.ID(required=False)

    post = graphene.Field(PostNode)

    @staticmethod
    def subscribe(root, info, author_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if author_id:
            real_id = from_global_id(author_id)[1]
            # Subscribe to specific author's posts
            if str(user.id) == real_id:
                return [f"author_posts_{real_id}"]
            else:
                # Allow subscribing to other authors if posts are published
                return [f"author_published_posts_{real_id}"]
        else:
            # Subscribe to all published posts
            return [f"all_published_posts"]

    @staticmethod
    def publish(payload, info, author_id=None):
        return OnPostCreated(post=payload)

    @classmethod
    def broadcast_to_author(cls, author_id, post):
        cls.broadcast_group(
            group=f"author_posts_{author_id}",
            payload=post,
        )

    @classmethod
    def broadcast_to_followers(cls, author_id, post):
        cls.broadcast_group(
            group=f"author_published_posts_{author_id}",
            payload=post,
        )

    @classmethod
    def broadcast_to_all(cls, post):
        cls.broadcast_group(
            group="all_published_posts",
            payload=post,
        )

class OnPostUpdated(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    post = graphene.Field(PostNode)
    updated_fields = graphene.List(graphene.String)

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Only author and staff can subscribe to post updates
            if post.author == user or user.is_staff:
                return [f"post_updates_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to this post")
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnPostUpdated(
            post=payload["post"],
            updated_fields=payload["updated_fields"]
        )

    @classmethod
    def broadcast(cls, post, updated_fields):
        cls.broadcast_group(
            group=f"post_updates_{post.id}",
            payload={
                "post": post,
                "updated_fields": updated_fields
            },
        )

class OnPostPublished(Subscription):
    class Arguments:
        author_id = graphene.ID(required=False)

    post = graphene.Field(PostNode)
    published_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, author_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        if author_id:
            real_id = from_global_id(author_id)[1]
            # Subscribe to specific author's published posts
            return [f"author_published_{real_id}"]
        else:
            # Subscribe to all published posts
            return [f"all_published"]

    @staticmethod
    def publish(payload, info, author_id=None):
        return OnPostPublished(
            post=payload["post"],
            published_at=payload["published_at"]
        )

    @classmethod
    def broadcast_to_author(cls, author_id, post):
        cls.broadcast_group(
            group=f"author_published_{author_id}",
            payload={
                "post": post,
                "published_at": post.publish_date.isoformat() if post.publish_date else timezone.now().isoformat()
            },
        )

    @classmethod
    def broadcast_to_all(cls, post):
        cls.broadcast_group(
            group="all_published",
            payload={
                "post": post,
                "published_at": post.publish_date.isoformat() if post.publish_date else timezone.now().isoformat()
            },
        )

class OnPostDeleted(Subscription):
    class Arguments:
        author_id = graphene.ID(required=True)

    post_id = graphene.ID()
    deleted_at = graphene.DateTime()
    title = graphene.String()

    @staticmethod
    def subscribe(root, info, author_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(author_id)[1]
        if str(user.id) != real_id and not user.is_staff:
            raise Exception("Not authorized")
        
        return [f"post_deletes_{real_id}"]

    @staticmethod
    def publish(payload, info, author_id):
        return OnPostDeleted(
            post_id=payload["post_id"],
            deleted_at=payload["deleted_at"],
            title=payload["title"]
        )

    @classmethod
    def broadcast(cls, author_id, post_id, title):
        cls.broadcast_group(
            group=f"post_deletes_{author_id}",
            payload={
                "post_id": post_id,
                "deleted_at": timezone.now().isoformat(),
                "title": title
            },
        )

# ----------------------------------------------------------------------
# 💬 COMMENT SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnCommentCreated(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    comment = graphene.Field(CommentNode)

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Anyone can subscribe to comments on published posts
            if post.published or post.author == user or user.is_staff:
                return [f"post_comments_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to comments on this post")
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnCommentCreated(comment=payload)

    @classmethod
    def broadcast(cls, post_id, comment):
        cls.broadcast_group(
            group=f"post_comments_{post_id}",
            payload=comment,
        )

class OnCommentApproved(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    comment = graphene.Field(CommentNode)
    approved_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Post author and comment author can subscribe to approval status
            if post.author == user:
                return [f"comment_approvals_{real_id}"]
            else:
                # Comment author can subscribe to their own comment approvals
                return [f"user_comment_approvals_{user.id}"]
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnCommentApproved(
            comment=payload["comment"],
            approved_at=payload["approved_at"]
        )

    @classmethod
    def broadcast_to_post(cls, post_id, comment):
        cls.broadcast_group(
            group=f"comment_approvals_{post_id}",
            payload={
                "comment": comment,
                "approved_at": timezone.now().isoformat()
            },
        )

    @classmethod
    def broadcast_to_user(cls, user_id, comment):
        cls.broadcast_group(
            group=f"user_comment_approvals_{user_id}",
            payload={
                "comment": comment,
                "approved_at": timezone.now().isoformat()
            },
        )

class OnCommentUpdated(Subscription):
    class Arguments:
        comment_id = graphene.ID(required=True)

    comment = graphene.Field(CommentNode)

    @staticmethod
    def subscribe(root, info, comment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(comment_id)[1]
        try:
            comment = Comment.objects.get(id=real_id)
            # Comment author, post author, and staff can subscribe
            if comment.author == user or comment.post.author == user or user.is_staff:
                return [f"comment_updates_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to this comment")
        except Comment.DoesNotExist:
            raise Exception("Comment not found")

    @staticmethod
    def publish(payload, info, comment_id):
        return OnCommentUpdated(comment=payload)

    @classmethod
    def broadcast(cls, comment):
        cls.broadcast_group(
            group=f"comment_updates_{comment.id}",
            payload=comment,
        )

class OnCommentDeleted(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    comment_id = graphene.ID()
    deleted_at = graphene.DateTime()
    author_name = graphene.String()

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Post author and staff can subscribe to comment deletions
            if post.author == user or user.is_staff:
                return [f"comment_deletes_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnCommentDeleted(
            comment_id=payload["comment_id"],
            deleted_at=payload["deleted_at"],
            author_name=payload["author_name"]
        )

    @classmethod
    def broadcast(cls, post_id, comment_id, author_name):
        cls.broadcast_group(
            group=f"comment_deletes_{post_id}",
            payload={
                "comment_id": comment_id,
                "deleted_at": timezone.now().isoformat(),
                "author_name": author_name
            },
        )

# ----------------------------------------------------------------------
# 🔄 REPLY SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnReplyCreated(Subscription):
    class Arguments:
        comment_id = graphene.ID(required=True)

    reply = graphene.Field(ReplyNode)

    @staticmethod
    def subscribe(root, info, comment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(comment_id)[1]
        try:
            comment = Comment.objects.get(id=real_id)
            # Anyone can subscribe to replies on approved comments
            if comment.is_approved or comment.post.author == user or user.is_staff:
                return [f"comment_replies_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to replies on this comment")
        except Comment.DoesNotExist:
            raise Exception("Comment not found")

    @staticmethod
    def publish(payload, info, comment_id):
        return OnReplyCreated(reply=payload)

    @classmethod
    def broadcast(cls, comment_id, reply):
        cls.broadcast_group(
            group=f"comment_replies_{comment_id}",
            payload=reply,
        )

class OnReplyApproved(Subscription):
    class Arguments:
        comment_id = graphene.ID(required=True)

    reply = graphene.Field(ReplyNode)
    approved_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, comment_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(comment_id)[1]
        try:
            comment = Comment.objects.get(id=real_id)
            # Comment author, reply author, and post author can subscribe
            if comment.author == user or comment.post.author == user:
                return [f"reply_approvals_{real_id}"]
            else:
                # Reply author can subscribe to their own reply approvals
                return [f"user_reply_approvals_{user.id}"]
        except Comment.DoesNotExist:
            raise Exception("Comment not found")

    @staticmethod
    def publish(payload, info, comment_id):
        return OnReplyApproved(
            reply=payload["reply"],
            approved_at=payload["approved_at"]
        )

    @classmethod
    def broadcast_to_comment(cls, comment_id, reply):
        cls.broadcast_group(
            group=f"reply_approvals_{comment_id}",
            payload={
                "reply": reply,
                "approved_at": timezone.now().isoformat()
            },
        )

    @classmethod
    def broadcast_to_user(cls, user_id, reply):
        cls.broadcast_group(
            group=f"user_reply_approvals_{user_id}",
            payload={
                "reply": reply,
                "approved_at": timezone.now().isoformat()
            },
        )

class OnReplyUpdated(Subscription):
    class Arguments:
        reply_id = graphene.ID(required=True)

    reply = graphene.Field(ReplyNode)

    @staticmethod
    def subscribe(root, info, reply_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(reply_id)[1]
        try:
            reply = Reply.objects.get(id=real_id)
            # Reply author, comment author, post author, and staff can subscribe
            if (reply.author == user or reply.comment.author == user or 
                reply.comment.post.author == user or user.is_staff):
                return [f"reply_updates_{real_id}"]
            else:
                raise Exception("Not authorized to subscribe to this reply")
        except Reply.DoesNotExist:
            raise Exception("Reply not found")

    @staticmethod
    def publish(payload, info, reply_id):
        return OnReplyUpdated(reply=payload)

    @classmethod
    def broadcast(cls, reply):
        cls.broadcast_group(
            group=f"reply_updates_{reply.id}",
            payload=reply,
        )

# ----------------------------------------------------------------------
# 🏷️ TAG SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnTagCreated(Subscription):
    class Arguments:
        user_id = graphene.ID(required=True)

    tag = graphene.Field(TagNode)

    @staticmethod
    def subscribe(root, info, user_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(user_id)[1]
        # Only staff users can create tags and subscribe to tag creation
        if user.is_staff and str(user.id) == real_id:
            return [f"tags_created"]
        else:
            raise Exception("Not authorized")

    @staticmethod
    def publish(payload, info, user_id):
        return OnTagCreated(tag=payload)

    @classmethod
    def broadcast(cls, tag):
        cls.broadcast_group(
            group="tags_created",
            payload=tag,
        )

class OnTagUsed(Subscription):
    class Arguments:
        tag_id = graphene.ID(required=True)

    tag = graphene.Field(TagNode)
    post = graphene.Field(PostNode)
    used_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, tag_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(tag_id)[1]
        try:
            tag = Tag.objects.get(id=real_id)
            # Anyone can subscribe to tag usage
            return [f"tag_usage_{real_id}"]
        except Tag.DoesNotExist:
            raise Exception("Tag not found")

    @staticmethod
    def publish(payload, info, tag_id):
        return OnTagUsed(
            tag=payload["tag"],
            post=payload["post"],
            used_at=payload["used_at"]
        )

    @classmethod
    def broadcast(cls, tag, post):
        cls.broadcast_group(
            group=f"tag_usage_{tag.id}",
            payload={
                "tag": tag,
                "post": post,
                "used_at": timezone.now().isoformat()
            },
        )

# ----------------------------------------------------------------------
# 📊 BLOG ANALYTICS SUBSCRIPTIONS
# ----------------------------------------------------------------------

class OnPostViewCountUpdated(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    post = graphene.Field(PostNode)
    view_count = graphene.Int()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Post author and staff can subscribe to view count updates
            if post.author == user or user.is_staff:
                return [f"post_views_{real_id}"]
            else:
                raise Exception("Not authorized")
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnPostViewCountUpdated(
            post=payload["post"],
            view_count=payload["view_count"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast(cls, post, view_count):
        cls.broadcast_group(
            group=f"post_views_{post.id}",
            payload={
                "post": post,
                "view_count": view_count,
                "updated_at": timezone.now().isoformat()
            },
        )

class OnCommentCountUpdated(Subscription):
    class Arguments:
        post_id = graphene.ID(required=True)

    post = graphene.Field(PostNode)
    comment_count = graphene.Int()
    approved_count = graphene.Int()
    updated_at = graphene.DateTime()

    @staticmethod
    def subscribe(root, info, post_id):
        user = info.context.user
        if not user.is_authenticated:
            raise Exception("Authentication required")
        
        real_id = from_global_id(post_id)[1]
        try:
            post = Post.objects.get(id=real_id)
            # Post author and staff can subscribe to comment count updates
            if post.author == user or user.is_staff:
                return [f"post_comments_count_{real_id}"]
            else:
                # Regular users can see approved comment counts
                return [f"post_approved_comments_count_{real_id}"]
        except Post.DoesNotExist:
            raise Exception("Post not found")

    @staticmethod
    def publish(payload, info, post_id):
        return OnCommentCountUpdated(
            post=payload["post"],
            comment_count=payload["comment_count"],
            approved_count=payload["approved_count"],
            updated_at=payload["updated_at"]
        )

    @classmethod
    def broadcast_full_stats(cls, post_id, post, comment_count, approved_count):
        cls.broadcast_group(
            group=f"post_comments_count_{post_id}",
            payload={
                "post": post,
                "comment_count": comment_count,
                "approved_count": approved_count,
                "updated_at": timezone.now().isoformat()
            },
        )

    @classmethod
    def broadcast_public_stats(cls, post_id, post, approved_count):
        cls.broadcast_group(
            group=f"post_approved_comments_count_{post_id}",
            payload={
                "post": post,
                "comment_count": approved_count,
                "approved_count": approved_count,
                "updated_at": timezone.now().isoformat()
            },
        )

# ----------------------------------------------------------------------
# Root BlogSubscription
# ----------------------------------------------------------------------

class BlogSubscription(graphene.ObjectType):
    # Posts
    on_post_created = OnPostCreated.Field()
    on_post_updated = OnPostUpdated.Field()
    on_post_published = OnPostPublished.Field()
    on_post_deleted = OnPostDeleted.Field()
    
    # Comments
    on_comment_created = OnCommentCreated.Field()
    on_comment_approved = OnCommentApproved.Field()
    on_comment_updated = OnCommentUpdated.Field()
    on_comment_deleted = OnCommentDeleted.Field()
    
    # Replies
    on_reply_created = OnReplyCreated.Field()
    on_reply_approved = OnReplyApproved.Field()
    on_reply_updated = OnReplyUpdated.Field()
    
    # Tags
    on_tag_created = OnTagCreated.Field()
    on_tag_used = OnTagUsed.Field()
    
    # Analytics
    on_post_view_count_updated = OnPostViewCountUpdated.Field()
    on_comment_count_updated = OnCommentCountUpdated.Field()'''