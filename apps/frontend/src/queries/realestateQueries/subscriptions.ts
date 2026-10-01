import { gql, useSubscription } from '@apollo/client';

const CREATE_LISTING_SUBSCRIPTION = gql`
  subscription OnCreateListing {
    createListing {
      id
      title
      description
      price
      # Add other fields as needed
    }
  }
`;

const NewListingNotification = () => {
  const { data, loading, error } = useSubscription(CREATE_LISTING_SUBSCRIPTION);

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div>
      <h2>New Listing Created</h2>
      {data && (
        <div>
          <p>ID: {data.createListing.id}</p>
          <p>Title: {data.createListing.title}</p>
          <p>Description: {data.createListing.description}</p>
          <p>Price: {data.createListing.price}</p>
          {/* Render additional fields as needed */}
        </div>
      )}
    </div>
  );
};

export default NewListingNotification;
