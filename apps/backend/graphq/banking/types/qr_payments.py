# ============================================================================
# QR PAYMENTS TYPES
# ============================================================================
import base64
import graphene
from graphene import  String, relay
from graphene_django import DjangoObjectType



from banking.models.qr_payments import QRCode, QRTransaction

class QRCodeNode(DjangoObjectType):
    """QR code node type."""
    qr_type_display = graphene.String()
    formatted_fixed_amount = graphene.String()
    formatted_max_amount_per_use = graphene.String()
    is_valid = graphene.Boolean()
    is_active_display = graphene.String()
    qr_image_base64 = graphene.String()

    class Meta:
        model = QRCode
        interfaces = (relay.Node,)
        filter_fields = {
            'creator': ['exact'],
            'merchant': ['exact'],
            'qr_type': ['exact'],
            'is_active': ['exact'],
            'qr_id': ['exact'],
            'reference': ['exact'],
        }

    def resolve_qr_type_display(self, info):
        return dict(self.QR_TYPES).get(self.qr_type, self.qr_type)

    def resolve_formatted_fixed_amount(self, info):
        if self.fixed_amount:
            return f"₦{self.fixed_amount:,.2f}"
        return "Variable"

    def resolve_formatted_max_amount_per_use(self, info):
        return f"₦{self.max_amount_per_use:,.2f}"

    def resolve_is_valid(self, info):
        return self.is_valid()

    def resolve_is_active_display(self, info):
        return "Active" if self.is_active else "Inactive"

    def resolve_qr_image_base64(self, info):
        if self.qr_image and hasattr(self.qr_image, 'read'):
            import base64
            with self.qr_image.open('rb') as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        return None


class QRTransactionNode(DjangoObjectType):
    """QR transaction node type."""
    formatted_amount = graphene.String()
    status_display = graphene.String()

    class Meta:
        model = QRTransaction
        interfaces = (relay.Node,)
        filter_fields = {
            'qr_code': ['exact'],
            'payer': ['exact'],
            'payee': ['exact'],
            'status': ['exact'],
            'reference': ['exact'],
        }

    def resolve_formatted_amount(self, info):
        return f"₦{self.amount:,.2f}"

    def resolve_status_display(self, info):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

