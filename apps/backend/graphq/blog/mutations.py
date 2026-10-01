import graphene
from graphene import relay

from blog.models import Tag
from graphq.blog.types import CommentNode, PostNode, ReplyNode, TagNode


# TagCreate Mutation
class TagCreate(relay.ClientIDMutation):
    class Input:
        name = graphene.String(required=True, description="Name of the tag.")

    tag = graphene.Field(TagNode, description="The created tag.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        name = input.get("name")
        # Create the tag
        tag = Tag.objects.create(name=name)
        return TagCreate(tag=tag)


# TagDelete Mutation
class TagDelete(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True, description="ID of the tag to delete.")

    success = graphene.Boolean(description="Whether the tag was successfully deleted.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        tag_id = input.get("id")
        try:
            # Retrieve and delete the tag
            _, tag_pk = relay.Node.from_global_id(tag_id)
            tag = Tag.objects.get(pk=tag_pk)
            tag.delete()
            return TagDelete(success=True)
        except Tag.DoesNotExist:
            return TagDelete(success=False)


class PostCreate(relay.ClientIDMutation):

    class Input:
        title = graphene.String(required=True, description="Title of the post.")
        subtitle = graphene.String(description="Subtitle of the post.")
        slug = graphene.String(required=True, description="Unique slug for the post.")
        body = graphene.String(required=True, description="Content of the post.")
        meta_description = graphene.String(description="Meta description of the post.")
        publish_date = graphene.DateTime(description="Date the post will be published.")
        published = graphene.Boolean(description="Publish status of the post.")
        author_id = graphene.ID(required=True, description="ID of the post's author.")
        tag_ids = graphene.List(
            graphene.ID, description="List of tag IDs associated with the post."
        )

    post = graphene.Field(PostNode, description="The created post.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        title = input.get("title")
        subtitle = input.get("subtitle", "")
        slug = input.get("slug")
        body = input.get("body")
        meta_description = input.get("meta_description", "")
        publish_date = input.get("publish_date")
        published = input.get("published", False)
        author_id = input.get("author_id")
        tag_ids = input.get("tag_ids", [])

        # Decode the author ID and fetch the author
        _, author_pk = relay.Node.from_global_id(author_id)
        author = settings.AUTH_USER_MODEL.objects.get(pk=author_pk)

        # Create the post
        post = Post.objects.create(
            title=title,
            subtitle=subtitle,
            slug=slug,
            body=body,
            meta_description=meta_description,
            publish_date=publish_date,
            published=published,
            author=author,
        )

        # Associate tags with the post
        if tag_ids:
            tags = []
            for tag_id in tag_ids:
                _, tag_pk = relay.Node.from_global_id(tag_id)
                tag = Tag.objects.get(pk=tag_pk)
                tags.append(tag)
            post.tags.set(tags)

        return PostCreate(post=post)


# PostDelete Mutation
class PostDelete(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True, description="ID of the post to delete.")

    success = graphene.Boolean(description="Whether the post was successfully deleted.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        post_id = input.get("id")
        try:
            # Decode the post ID and retrieve the post
            _, post_pk = relay.Node.from_global_id(post_id)
            post = Post.objects.get(pk=post_pk)
            post.delete()
            return PostDelete(success=True)
        except Post.DoesNotExist:
            return PostDelete(success=False)


class PostUpdate(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True, description="ID of the post to update.")
        title = graphene.String(description="Updated title of the post.")
        subtitle = graphene.String(description="Updated subtitle of the post.")
        slug = graphene.String(description="Updated unique slug for the post.")
        body = graphene.String(description="Updated content of the post.")
        meta_description = graphene.String(
            description="Updated meta description of the post."
        )
        publish_date = graphene.DateTime(
            description="Updated date the post will be published."
        )
        published = graphene.Boolean(description="Updated publish status of the post.")
        author_id = graphene.ID(description="Updated ID of the post's author.")
        tag_ids = graphene.List(
            graphene.ID, description="List of tag IDs to associate with the post."
        )

    post = graphene.Field(PostNode, description="The updated post.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        post_id = input.get("id")

        # Decode the post ID and retrieve the existing post
        _, post_pk = relay.Node.from_global_id(post_id)
        try:
            post = Post.objects.get(pk=post_pk)
        except Post.DoesNotExist:
            raise Exception("Post not found.")

        # Update the post fields if provided
        title = input.get("title")
        if title is not None:
            post.title = title

        subtitle = input.get("subtitle")
        if subtitle is not None:
            post.subtitle = subtitle

        slug = input.get("slug")
        if slug is not None:
            post.slug = slug

        body = input.get("body")
        if body is not None:
            post.body = body

        meta_description = input.get("meta_description")
        if meta_description is not None:
            post.meta_description = meta_description

        publish_date = input.get("publish_date")
        if publish_date is not None:
            post.publish_date = publish_date

        published = input.get("published")
        if published is not None:
            post.published = published

        author_id = input.get("author_id")
        if author_id is not None:
            _, author_pk = relay.Node.from_global_id(author_id)
            post.author_id = author_pk

        # Update tags if provided
        tag_ids = input.get("tag_ids")
        if tag_ids is not None:
            tags = []
            for tag_id in tag_ids:
                _, tag_pk = relay.Node.from_global_id(tag_id)
                tag = Tag.objects.get(pk=tag_pk)
                tags.append(tag)
            post.tags.set(tags)

        # Save the updated post
        post.save()

        return PostUpdate(post=post)


class CommentUpdate(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True, description="ID of the comment to update.")
        name = graphene.String(description="Updated name of the comment's author.")
        body = graphene.String(description="Updated content of the comment.")
        post_id = graphene.ID(
            description="ID of the post this comment is associated with."
        )

    comment = graphene.Field(lambda: CommentNode, description="The updated comment.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        comment_id = input.get("id")

        # Decode the comment ID and retrieve the existing comment
        _, comment_pk = relay.Node.from_global_id(comment_id)
        try:
            comment = Comment.objects.get(pk=comment_pk)
        except Comment.DoesNotExist:
            raise Exception("Comment not found.")

        # Update fields if provided
        name = input.get("name")
        if name is not None:
            comment.name = name

        body = input.get("body")
        if body is not None:
            comment.body = body

        post_id = input.get("post_id")
        if post_id is not None:
            _, post_pk = relay.Node.from_global_id(post_id)
            try:
                post = Post.objects.get(pk=post_pk)
                comment.post = post
            except Post.DoesNotExist:
                raise Exception("Post not found.")

        # Save the updated comment
        comment.save()

        return CommentUpdate(comment=comment)


class CommentCreate(relay.ClientIDMutation):
    class Input:
        post_id = graphene.ID(
            required=True, description="ID of the post to comment on."
        )
        name = graphene.String(
            required=True, description="Name of the comment's author."
        )
        body = graphene.String(required=True, description="Content of the comment.")

    comment = graphene.Field(
        lambda: CommentNode, description="The newly created comment."
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        post_id = input.get("post_id")
        name = input.get("name")
        body = input.get("body")

        # Decode the post ID and retrieve the post
        _, post_pk = relay.Node.from_global_id(post_id)
        try:
            post = Post.objects.get(pk=post_pk)
        except Post.DoesNotExist:
            raise Exception("Post not found.")

        # Create a new comment
        comment = Comment.objects.create(
            post=post,
            name=name,
            body=body,
        )

        return CommentCreate(comment=comment)


class CommentDelete(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True, description="ID of the comment to delete.")

    success = graphene.Boolean(
        description="True if the comment was deleted successfully."
    )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        comment_id = input.get("id")

        # Decode the comment ID and retrieve the comment
        _, comment_pk = relay.Node.from_global_id(comment_id)
        try:
            comment = Comment.objects.get(pk=comment_pk)
            comment.delete()
            return CommentDelete(success=True)
        except Comment.DoesNotExist:
            raise Exception("Comment not found.")

        return CommentDelete(success=False)


class ReplyCreate(graphene.relay.ClientIDMutation):
    reply = graphene.Field(ReplyNode)

    class Input:
        comment_id = graphene.ID(required=True, description="ID of the comment.")
        name = graphene.String(required=False, description="Name of the replier.")
        body = graphene.String(required=True, description="Body of the reply.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, comment_id, **input):
        # Decode the global ID for comment
        _, comment_db_id = from_global_id(comment_id)

        comment = Comment.objects.get(pk=comment_db_id)

        # Create the Reply
        reply = Reply.objects.create(
            comment=comment, name=input.get("name"), body=input["body"]
        )
        return ReplyCreate(reply=reply)


class ReplyUpdate(graphene.relay.ClientIDMutation):
    reply = graphene.Field(ReplyNode)

    class Input:
        id = graphene.ID(required=True, description="ID of the reply to update.")
        name = graphene.String(
            required=False, description="Updated name of the replier."
        )
        body = graphene.String(required=False, description="Updated body of the reply.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input):
        # Decode the global ID for reply
        _, reply_db_id = from_global_id(id)

        try:
            # Retrieve the existing reply
            reply = Reply.objects.get(pk=reply_db_id)

            # Update fields if new values are provided
            if "name" in input:
                reply.name = input["name"]
            if "body" in input:
                reply.body = input["body"]

            # Save the updated reply
            reply.save()

            return ReplyUpdate(reply=reply)

        except Reply.DoesNotExist:
            raise Exception("Reply not found")


class ReplyDelete(graphene.relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True, description="ID of the reply to delete.")

    @classmethod
    def mutate_and_get_payload(cls, root, info, id, **input):
        # Decode the global ID for reply
        _, reply_db_id = from_global_id(id)

        try:
            reply = Reply.objects.get(pk=reply_db_id)
            reply.delete()
            success = True
        except Reply.DoesNotExist:
            success = False

        return ReplyDelete(success=success)


# Add mutations to Mutation class
class BlogMutations(graphene.ObjectType):
    create_tag = TagCreate.Field(description="Create a new tag.")
    delete_tag = TagDelete.Field(description="Delete a tag by ID.")
    create_post = PostCreate.Field(description="Create a new post.")
    update_post = PostUpdate.Field(description="Update an existing post.")
    delete_post = PostDelete.Field(description="Delete a post by ID.")
    create_comment = CommentCreate.Field(description="Create a new comment.")
    update_comment = CommentUpdate.Field(description="Update an existing comment.")
    delete_comment = CommentDelete.Field(description="Delete a comment by ID.")
