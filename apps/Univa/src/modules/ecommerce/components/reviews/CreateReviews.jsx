import { useMutation } from '@apollo/client/react';
import { CREATE_PRODUCT_REVIEW } from '@/graphql/mutations/productReview';

const [createReview, { loading, error }] = useMutation(CREATE_PRODUCT_REVIEW);

const submitReview = async (productId, rating, comment) => {
  try {
    const { data } = await createReview({
      variables: {
        input: { productId, rating, comment },
      },
    });
    console.log('Created review:', data.createProductReview.review);
  } catch (err) {
    console.error(err);
  }
};
