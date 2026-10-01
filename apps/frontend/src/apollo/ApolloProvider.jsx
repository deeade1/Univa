import { ApolloProvider as Provider } from "@apollo/client";
import client from "@/apollo/client";

export default function ApolloWrapper({ children }) {
  return <Provider client={client}>{children}</Provider>;
}
