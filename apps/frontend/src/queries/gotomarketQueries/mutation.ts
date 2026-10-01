// src/hooks/useCreatePurchase.tsx
import { gql } from "@apollo/client";

export const CREATE_PURCHASE = gql`
  mutation CreatePurchase($items: [PurchaseLineInput!]!, $sendEmail: Boolean, $sendWhatsapp: Boolean) {
    createPurchase(input: { items: $items, sendEmail: $sendEmail, sendWhatsapp: $sendWhatsapp }) {
      success
      message
      pdfUrl
      purchase {
        id
        purchaseNumber
        subtotal
        vatAmount
        discount
        total
        createdAt
      }
    }
  }
`;
