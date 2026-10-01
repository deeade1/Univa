// GraphQL mutations
import { gql } from '@apollo/client';

// Tag Mutations
export const CREATE_TAG_MUTATION = gql`
  mutation CreateTag($input: TagCreateInput!) {
    tagCreate(input: $input) {
      tag {
        id
        name
        slug
      }
    }
  }
`;

export const DELETE_TAG_MUTATION = gql`
  mutation DeleteTag($input: TagDeleteInput!) {
    tagDelete(input: $input) {
      success
    }
  }
`;

// Post Mutations
export const CREATE_POST_MUTATION = gql`
  mutation CreatePost($input: PostCreateInput!) {
    postCreate(input: $input) {
      post {
        id
        title
        subtitle
        slug
        body
        metaDescription
        publishDate
        published
        author {
          id
          firstName
          lastName
        }
        tags {
          id
          name
        }
      }
    }
  }
`;

export const UPDATE_POST_MUTATION = gql`
  mutation UpdatePost($input: PostUpdateInput!) {
    postUpdate(input: $input) {
      post {
        id
        title
        subtitle
        slug
        body
        metaDescription
        publishDate
        published
        author {
          id
          firstName
          lastName
        }
        tags {
          id
          name
        }
      }
    }
  }
`;

export const DELETE_POST_MUTATION = gql`
  mutation DeletePost($input: PostDeleteInput!) {
    postDelete(input: $input) {
      success
    }
  }
`;

// Comment Mutations
export const CREATE_COMMENT_MUTATION = gql`
  mutation CreateComment($input: CommentCreateInput!) {
    commentCreate(input: $input) {
      comment {
        id
        name
        body
        isApproved
        createdAt
        post {
          id
          title
        }
        author {
          id
          firstName
        }
      }
    }
  }
`;

export const UPDATE_COMMENT_MUTATION = gql`
  mutation UpdateComment($input: CommentUpdateInput!) {
    commentUpdate(input: $input) {
      comment {
        id
        name
        body
        isApproved
        post {
          id
          title
        }
      }
    }
  }
`;

export const DELETE_COMMENT_MUTATION = gql`
  mutation DeleteComment($input: CommentDeleteInput!) {
    commentDelete(input: $input) {
      success
    }
  }
`;

// Reply Mutations
export const CREATE_REPLY_MUTATION = gql`
  mutation CreateReply($input: ReplyCreateInput!) {
    replyCreate(input: $input) {
      reply {
        id
        name
        body
        isApproved
        createdAt
        comment {
          id
        }
        author {
          id
          firstName
        }
      }
    }
  }
`;

export const UPDATE_REPLY_MUTATION = gql`
  mutation UpdateReply($input: ReplyUpdateInput!) {
    replyUpdate(input: $input) {
      reply {
        id
        name
        body
        isApproved
      }
    }
  }
`;

export const DELETE_REPLY_MUTATION = gql`
  mutation DeleteReply($input: ReplyDeleteInput!) {
    replyDelete(input: $input) {
      success
    }
  }
`;

// Input types
export const TAG_CREATE_INPUT = gql`
  input TagCreateInput {
    name: String!
  }
`;

export const TAG_DELETE_INPUT = gql`
  input TagDeleteInput {
    id: ID!
  }
`;

export const POST_CREATE_INPUT = gql`
  input PostCreateInput {
    title: String!
    subtitle: String
    slug: String!
    body: String!
    metaDescription: String
    publishDate: DateTime
    published: Boolean
    authorId: ID!
    tagIds: [ID]
  }
`;

export const POST_UPDATE_INPUT = gql`
  input PostUpdateInput {
    id: ID!
    title: String
    subtitle: String
    slug: String
    body: String
    metaDescription: String
    publishDate: DateTime
    published: Boolean
    authorId: ID
    tagIds: [ID]
  }
`;

export const POST_DELETE_INPUT = gql`
  input PostDeleteInput {
    id: ID!
  }
`;

export const COMMENT_CREATE_INPUT = gql`
  input CommentCreateInput {
    postId: ID!
    name: String!
    body: String!
  }
`;

export const COMMENT_UPDATE_INPUT = gql`
  input CommentUpdateInput {
    id: ID!
    name: String
    body: String
    postId: ID
  }
`;

export const COMMENT_DELETE_INPUT = gql`
  input CommentDeleteInput {
    id: ID!
  }
`;

export const REPLY_CREATE_INPUT = gql`
  input ReplyCreateInput {
    commentId: ID!
    name: String
    body: String!
  }
`;

export const REPLY_UPDATE_INPUT = gql`
  input ReplyUpdateInput {
    id: ID!
    name: String
    body: String
  }
`;

export const REPLY_DELETE_INPUT = gql`
  input ReplyDeleteInput {
    id: ID!
  }
`;