import { Title, Meta, Link } from "react-head";

export default function SEO({ data }) {
  return (
    <>
      <Title>{data.metaTitle}</Title>
      <Meta name="description" content={data.metaDescription} />
      <Link rel="canonical" href={data.canonicalUrl} />

      {/* OpenGraph */}
      <Meta property="og:title" content={data.title} />
      <Meta property="og:description" content={data.summary} />
      <Meta property="og:type" content="article" />

      {/* Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(data.structuredData) }}
      />
    </>
  );
}

<>
  <Title>{product?.name} | Royal Foam</Title>
  <Meta name="description" content={product?.description?.substring(0, 160)} />
  <Meta property="og:title" content={product?.name} />
  <Meta property="og:description" content={product?.description?.substring(0, 160)} />
  <Meta property="og:type" content="product" />
  {product?.media?.edges?.[0]?.node.image && (
    <Meta property="og:image" content={`http://localhost:8080/media/${product.media.edges[0].node.image}`} />
  )}
  <Meta property="product:brand" content="Royal Foam" />
  <Meta property="product:price:amount" content="0" />
  <Meta property="product:price:currency" content="NGN" />
</>
