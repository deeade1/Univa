import { gql } from "@apollo/client";

export const GET_ALL_POSTS = gql`
  query GetAllPosts($first: Int, $after: String) {
    allPosts(first: $first, after: $after) {
      edges {
        node {
          id
          title
          subtitle
          slug
          metaDescription
          publishDate
          published
          author {
            id
            firstName
            lastName
          }
          tags {
            edges {
              node {
                id
                name
                slug
              }
            }
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_AUTHOR_BY_FIRST_NAME = gql`
  query GetAuthorByFirstName($first_name: String!) {
    authorByFirstName(firstName: $first_name) {
      id
      firstName
      lastName
      email
      posts {
        edges {
          node {
            id
            title
            slug
          }
        }
      }
    }
  }
`;

export const GET_POST_BY_SLUG = gql`
  query GetPostBySlug($slug: String!) {
    postBySlug(slug: $slug) {
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
        edges {
          node {
            id
            name
            slug
          }
        }
      }
      comments {
        edges {
          node {
            id
            body
            createdAt
            author {
              id
              firstName
            }
          }
        }
      }
    }
  }
`;

export const GET_POSTS_BY_AUTHOR = gql`
  query GetPostsByAuthor($first_name: String!) {
    postsByAuthor(firstName: $first_name) {
      edges {
        node {
          id
          title
          slug
          publishDate
          tags {
            edges {
              node {
                id
                name
              }
            }
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_POSTS_BY_TAG = gql`
  query GetPostsByTag($tag: String!) {
    postsByTag(tag: $tag) {
      edges {
        node {
          id
          title
          slug
          publishDate
          author {
            id
            firstName
            lastName
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_REPLY = gql`
  query GetReply($id: ID!) {
    reply(id: $id) {
      id
      body
      createdAt
      isApproved
      author {
        id
        firstName
      }
      comment {
        id
        post {
          id
          title
        }
      }
    }
  }
`;

export const GET_ALL_REPLIES = gql`
  query GetAllReplies($first: Int, $after: String) {
    allReplies(first: $first, after: $after) {
      edges {
        node {
          id
          body
          createdAt
          isApproved
          author {
            id
            firstName
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_COMMENT = gql`
  query GetComment($id: ID!) {
    comment(id: $id) {
      id
      body
      createdAt
      isApproved
      author {
        id
        firstName
      }
      post {
        id
        title
      }
      replies {
        edges {
          node {
            id
            body
            createdAt
          }
        }
      }
    }
  }
`;

export const GET_ALL_COMMENTS = gql`
  query GetAllComments($first: Int, $after: String) {
    allComments(first: $first, after: $after) {
      edges {
        node {
          id
          body
          createdAt
          isApproved
          author {
            id
            firstName
          }
          post {
            id
            title
          }
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
`;

export const GET_POST_WITH_COMMENTS = gql`
  query GetPostWithComments($slug: String!) {
    postBySlug(slug: $slug) {
      id
      title
      comments {
        edges {
          node {
            id
            body
            createdAt
            isApproved
            author {
              id
              firstName
            }
            replies {
              edges {
                node {
                  id
                  body
                  createdAt
                  author {
                    id
                    firstName
                  }
                }
              }
            }
          }
        }
      }
    }
  }
`;