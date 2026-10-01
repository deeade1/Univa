import React from "react";
import { Card } from "react-bootstrap";

export interface BlogPost {
  id: number;
  image: string;
  date: string;
  title: string;
  author: string;
  description: string;
}

interface BlogWidgetProps {
  blog: BlogPost;
}

const BlogWidget: React.FC<BlogWidgetProps> = ({ blog }) => {
  return (
    <Card className="h-100 shadow-sm">
      <Card.Img
        variant="top"
        src={blog.image}
        alt={blog.title}
        style={{ objectFit: "cover", height: "200px" }}
      />
      <Card.Body>
        <small className="text-muted d-block mb-2">
          {blog.date} • {blog.author}
        </small>
        <Card.Title>{blog.title}</Card.Title>
        <Card.Text>{blog.description}</Card.Text>
      </Card.Body>
    </Card>
  );
};

export default BlogWidget;
